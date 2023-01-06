from flask import Blueprint, g, current_app, request, make_response, send_file
from io import BytesIO
from traceback import format_exc
from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError
from uuid import UUID
from werkzeug.exceptions import BadRequest

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


@api_secret.route(api_prefix)
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
    group = ''
    username = ''
    password = ''
    url = ''
    notes = ''
    if request.content_type in ['application/json']:
        try:
            json_data = request.get_json()
            if type(json_data) is not dict:
                return make_response({'msg': 'invalid JSON structure'}, 400)
        except BadRequest as e:
            return make_response({'msg': 'cannot parse JSON payload'}, 400)

        if 'title' not in request.json:
            return make_response({'msg': 'new secret must have a title'}, 400)

    else:
        pass

    entry = g.db.add_entry(group, title, username, password, url=url, notes=notes)


@api_secret.route(api_prefix + '/<string:uuid>')
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
            'attachments': attachments, 'password': secret.password}
    return make_response({'msg': 'ok', 'data': data}, 200)


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
