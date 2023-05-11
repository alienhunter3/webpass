from flask import Blueprint, g, current_app, request, make_response, send_file
from traceback import format_exc
from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError

api_datafile = Blueprint('api_datafile', __name__)
api_prefix = '/file'


@api_datafile.before_request
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


@api_datafile.route(api_prefix, methods=['GET'])
def get_file():
    return send_file(g.db.filename)


@api_datafile.route(api_prefix, methods=['POST'])
def update_file():
    pass
