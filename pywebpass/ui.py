from flask import Blueprint, make_response, render_template

ui_page = Blueprint('ui_page', __name__)


@ui_page.route('/')
def get_ui_page():
    """Renders and returns the UI page."""
    return make_response(render_template('index.html'))
