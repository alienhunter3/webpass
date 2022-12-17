from flask import Blueprint, abort, g, current_app, request
import json
from pykeepass import PyKeePass

api_group = Blueprint('api_group', __name__)
api_prefix = '/group'


@api_group.before_request
def before_request_func():
    pw = request.args.get('password')
    g.db = PyKeePass(current_app.config['DATABASE'], password=pw)


@api_group.route(api_prefix + '/')
def all_groups(page):
    pass
