from flask import Blueprint, current_app, make_response, render_template

ui_page = Blueprint('ui_page', __name__)

DEFAULT_UI_IDLE_TIMEOUT = 15 * 60
DEFAULT_UI_ABSOLUTE_TIMEOUT = 8 * 60 * 60


def _ui_timeout_seconds(key, default):
    raw = current_app.config.get(key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    if value < 1:
        return default
    return value


@ui_page.route('/')
def get_ui_page():
    """Renders and returns the UI page."""
    response = make_response(render_template(
        'index.html',
        idle_timeout=_ui_timeout_seconds('UI_IDLE_TIMEOUT', DEFAULT_UI_IDLE_TIMEOUT),
        absolute_timeout=_ui_timeout_seconds(
            'UI_ABSOLUTE_TIMEOUT', DEFAULT_UI_ABSOLUTE_TIMEOUT
        ),
    ))
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response
