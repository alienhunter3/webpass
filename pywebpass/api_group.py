"""Group REST endpoints under ``/api/group``.

All routes require HTTP Basic authentication. The password is the KeePass
master password; the username is ignored.
"""

from flask import Blueprint, g, current_app, request, make_response
from traceback import format_exc
from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError
from uuid import UUID

from .request_guard import install_secret_guards

api_group = Blueprint('api_group', __name__)
api_prefix = '/group'
install_secret_guards(api_group)


@api_group.before_request
def before_request_func():
    if request.authorization is None:
        return make_response({'msg': 'login with http basic auth'}, 401)
    pw = request.authorization.password
    try:
        g.db = PyKeePass(current_app.config['DATABASE'], password=pw)
    except CredentialsError as e:
        return make_response({'msg': 'login invalid'}, 401)
    except Exception as e:
        current_app.logger.error(f"Unexpected error:\n{format_exc()}")
        return make_response({'msg': 'unexpected server error'}, 500)


@api_group.route(api_prefix)
def all_groups():
    """``GET /api/group`` — list all groups.

    Response:
        ``200`` with ``{"msg": "ok", "data": [{"uuid", "name"}, ...]}``.
    """
    data = [{'uuid': str(x.uuid), 'name': x.name} for x in g.db.groups]
    return make_response({'msg': 'ok', 'data': data}, 200)


def _group_node(group):
    parent = group.parentgroup
    path = group.path or []
    return {
        'uuid': str(group.uuid),
        'name': group.name,
        'path': '/' + '/'.join('' if part is None else str(part) for part in path),
        'parent': None if parent is None else str(parent.uuid),
    }


def _entry_node(entry):
    group = entry.group
    return {
        'uuid': str(entry.uuid),
        'title': entry.title,
        'username': entry.username,
        'group': None if group is None else str(group.uuid),
    }


@api_group.route(api_prefix + '/tree')
def group_tree():
    """``GET /api/group/tree`` — groups and entry summaries, without secret values.

    One database open returns the navigation tree. Groups include ``uuid``,
    ``name``, ``path``, and ``parent``. Entries include ``uuid``, ``title``,
    ``username``, and ``group``. Passwords, notes, URLs, and custom properties
    are omitted; ``GET /api/secret/<uuid>`` reads those for a single entry.

    Response:
        ``200`` with ``{"msg": "ok", "data": {"groups": [...], "entries": [...]}}``.
    """
    def _group_sort_key(group):
        path = tuple('' if part is None else str(part) for part in (group.path or []))
        return (path, group.name or '')

    groups = sorted(g.db.groups, key=_group_sort_key)
    entries = sorted(g.db.entries, key=lambda entry: ((entry.title or ''), str(entry.uuid)))
    data = {
        'groups': [_group_node(group) for group in groups],
        'entries': [_entry_node(entry) for entry in entries],
    }
    return make_response({'msg': 'ok', 'data': data}, 200)


@api_group.route(api_prefix + '/<string:uuid>')
def group_details(uuid: str):
    """``GET /api/group/<uuid>`` — details for one group.

    Response:
        ``200`` with name, path, uuid, notes, and ``num_entries``.
        ``400`` / ``404`` for bad or missing UUID.
    """
    try:
        uuid_obj = UUID(uuid)
    except ValueError as e:
        return make_response({'msg': 'incorrectly formatted uuid value'}, 400)
    group = g.db.find_groups_by_uuid(uuid_obj, first=True)
    if group is None:
        return make_response({'msg': 'group not found'}, 404)
    data = {'name': group.name, 'path': '/'+'/'.join(group.path), 'uuid': group.uuid, 'notes': group.notes,
            'num_entries': len(group.entries)}
    return make_response({'msg': 'ok', 'data': data}, 200)


@api_group.route(api_prefix + '/<string:uuid>/secrets')
def group_secrets(uuid: str):
    """``GET /api/group/<uuid>/secrets`` — secrets in a group.

    Query params:
        fetch_all: If truthy, return full entry details including passwords.

    Response:
        ``200`` with ``{"msg": "ok", "data": [...]}``.
        ``400`` / ``404`` for bad or missing group UUID.
    """
    try:
        uuid_obj = UUID(uuid)
    except ValueError as e:
        return make_response({'msg': 'incorrectly formatted uuid value'}, 400)
    group = g.db.find_groups_by_uuid(uuid_obj, first=True)
    if group is None:
        return make_response({'msg': 'group not found'}, 404)
    fetch_all_details = False
    if 'fetch_all' in request.args:
        if request.args['fetch_all'].strip().lower() in ['y', 'yes', 'true', '1']:
            fetch_all_details = True
    if fetch_all_details:
        return_data = []
        for secret in group.entries:
            attachments = []
            for a in secret.attachments:
                attachments.append({'id': a.id, 'file_name': a.filename})
            data = {'name': secret.title, 'path': f"/{'/'.join(secret.path)}", 'uuid': secret.uuid,
                    'notes': secret.notes,
                    'attachments': attachments, 'username': secret.username, 'password': secret.password,
                    'url': secret.url}
            for key in secret.custom_properties.keys():
                var = key
                val = secret.custom_properties[var]
                if var in data:
                    var = 'custom_' + var
                data[var] = val
            return_data.append(data)
    else:
        return_data = [{'uuid': x.uuid, 'title': x.title, 'username': x.username} for x in group.entries]
    return make_response({'msg': 'ok', 'data': return_data}, 200)
