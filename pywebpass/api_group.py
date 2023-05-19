from flask import Blueprint, g, current_app, request, make_response
from traceback import format_exc
from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError
from uuid import UUID

api_group = Blueprint('api_group', __name__)
api_prefix = '/group'


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
    data = [{'uuid': str(x.uuid), 'name': x.name} for x in g.db.groups]
    return make_response({'msg': 'ok', 'data': data}, 200)


@api_group.route(api_prefix + '/<string:uuid>')
def group_details(uuid: str):
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
