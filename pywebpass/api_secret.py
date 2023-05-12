import logging

from flask import Blueprint, g, current_app, request, make_response, send_file
from io import BytesIO
from traceback import format_exc
from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError
from uuid import UUID
from werkzeug.exceptions import BadRequest
from .keepass import find_group

api_secret = Blueprint('api_secret', __name__)
api_prefix = '/secret'


@api_secret.before_request
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


@api_secret.route(api_prefix, methods=['GET'])
def root_secrets():
    all_secrets = g.db.entries
    if 'search' in request.args:
        term = request.args.get('search').strip().lower()
        if term == '':
            data = [{'uuid': x.uuid, 'title': x.title, 'username': x.username} for x in all_secrets]
            return make_response({'msg': 'ok', 'data': data}, 200)
        secrets = []
        for s in all_secrets:
            if type(s.title) is str and term in s.title.lower():
                secrets.append(s)
                continue
            if type(s.username) is str and term in s.username.lower():
                secrets.append(s)
                continue
            if type(s.notes) is str and term in s.notes.lower():
                secrets.append(s)
                continue
            for a in s.attachments:
                if term in a.filename.lower():
                    secrets.append(s)
                    break
        data = [{'uuid': x.uuid, 'title': x.title, 'username': x.username} for x in secrets]
        return make_response({'msg': 'ok', 'data': data}, 200)

    else:
        data = [{'uuid': x.uuid, 'title': x.title, 'username': x.username} for x in all_secrets]
        return make_response({'msg': 'ok', 'data': data}, 200)


@api_secret.route(api_prefix, methods=['POST'])
def post_secret():
    json_data = {}
    if str(request.content_type).find('json') != -1:
        try:
            json_data = request.get_json()
            if type(json_data) is not dict:
                current_app.logger.error("Invalid JSON structure.")
                return make_response({'msg': 'invalid JSON structure'}, 400)
        except BadRequest as e:
            current_app.logger.error("Cannot parse json payload.")
            return make_response({'msg': 'cannot parse JSON payload'}, 400)

    else:
        logging.error(f"Msg not application/json, received '{request.content_type}'")
        return make_response({'msg': 'currently only "application/json" supported'}, 400)

    group = find_group(g.db, json_data.get('group', ''))
    title = json_data.get('title', '')
    username = json_data.get('username', '')
    password = json_data.get('password', '')
    url = json_data.get('url', '')
    notes = json_data.get('notes', '')
    if len(g.db.find_entries_by_title(title, group=group)) > 0:
        logging.error(f'Group already contains entry with title "{title}"')
        return make_response({'msg': f'Group already contains entry with title "{title}"'}, 400)
    try:
        entry = g.db.add_entry(group, title, username, password, url=url, notes=notes)
    except:
        return make_response({'msg': "Couldn't create new secret due to an unknown error."}, 500)

    if 'extra' in json_data:
        props = json_data['extra']
        if type(props) is dict:
            for key in props.keys():
                key = key.strip()
                if key.lower() in ['title', 'url', 'notes', 'password', 'username', 'group']:
                    continue
                val = props[key]
                entry.set_custom_property(key, str(val))

    try:
        g.db.save()
        return make_response({'msg': 'ok', 'secret': f'{str(entry.uuid)}'}, 201)
    except:
        return make_response({'msg': "Couldn't save changes to database due to unknown error."}, 500)


@api_secret.route(api_prefix + '/<string:uuid>', methods=['GET'])
def secret_details(uuid: str):
    try:
        uuid_obj = UUID(uuid)
    except ValueError as e:
        return make_response({'msg': 'incorrectly formatted uuid value'}, 400)
    secret = g.db.find_entries_by_uuid(uuid_obj, first=True)
    if secret is None:
        return make_response({'msg': 'secret not found'}, 404)
    attachments = []
    for a in secret.attachments:
        attachments.append({'id': a.id, 'file_name': a.filename})
    data = {'name': secret.title, 'path': f"/{'/'.join(secret.path)}", 'uuid': secret.uuid, 'notes': secret.notes,
            'attachments': attachments, 'username': secret.username, 'password': secret.password, 'url': secret.url}
    for key in secret.custom_properties.keys():
        var = key
        val = secret.custom_properties[var]
        if var in data:
            var = 'custom_'+var
        data[var] = val
    return make_response({'msg': 'ok', 'data': data}, 200)


@api_secret.route(api_prefix + '/<string:uuid>', methods=['PUT'])
def secret_update(uuid: str):
    try:
        uuid_obj = UUID(uuid)
    except ValueError as e:
        return make_response({'msg': 'incorrectly formatted uuid value'}, 400)
    secret = g.db.find_entries_by_uuid(uuid_obj, first=True)
    if secret is None:
        return make_response({'msg': 'secret not found'}, 404)

    json_data = {}
    if str(request.content_type).find('json') != -1:
        try:
            json_data = request.get_json()
            if type(json_data) is not dict:
                return make_response({'msg': 'invalid JSON structure'}, 400)
        except BadRequest as e:
            return make_response({'msg': 'cannot parse JSON payload'}, 400)
    else:
        return make_response({'msg': 'currently only "application/json" supported'}, 400)

    if 'title' in json_data:
        title = json_data['title'].strip()
        if title != secret.title:
            group = secret.group
            if len(g.db.find_entries_by_title(title, group=group)) > 0:
                return make_response({'msg': f'Group already contains entry with title "{title}"'}, 400)
            secret.title = title
    for prop in ('username', 'password', 'url', 'notes'):
        if prop in json_data:
            new_val = json_data[prop].strip()
            if new_val != secret.__getattribute__(prop):
                secret.__setattr__(prop, new_val)
    try:
        g.db.save()
        return make_response({'msg': 'ok', 'secret': f'{str(secret.uuid)}'}, 200)
    except:
        return make_response({'msg': "Couldn't save changes to database due to unknown error."}, 500)


@api_secret.route(api_prefix + '/<string:uuid>/attachment/<int:attachment_id>')
def secret_attachments(uuid: str, attachment_id: int):
    try:
        uuid_obj = UUID(uuid)
    except ValueError as e:
        return make_response({'msg': 'incorrectly formatted uuid value'}, 400)
    secret = g.db.find_entries_by_uuid(uuid_obj, first=True)
    if secret is None:
        return make_response({'msg': 'secret not found'}, 404)

    for a in secret.attachments:
        if a.id == attachment_id:
            return send_file(path_or_file=BytesIO(a.binary), download_name=a.filename, as_attachment=True)
    return make_response({'msg': 'attachment not found'}, 404)
