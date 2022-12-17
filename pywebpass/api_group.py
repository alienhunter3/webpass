from flask import Blueprint, render_template, abort
from jinja2 import TemplateNotFound
import json
from .config import configuration
from pykeepass import

api_group = Blueprint('api_group', __name__)
api_prefix = '/api/group'


db = PyKeePass()


@api_group.before_request
def before_request_func():



@api_group.route(api_prefix + '/')
def all_groups(page):
    pass
