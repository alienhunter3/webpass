import os
import logging
from flask import Flask
from systemdlogging.toolbox import init_systemd_logging
from .util import parse_bool
from .api_group import api_group
from .api_secret import api_secret
from .api_datafile import api_datafile
from .ui import ui_page


def _ensure_database_readable(app):
    """Refuse to serve until the configured KeePass file can be opened for reading."""
    db_path = app.config.get('DATABASE')
    if isinstance(db_path, os.PathLike):
        db_path = os.fspath(db_path)
    if not isinstance(db_path, str) or db_path == '':
        raise RuntimeError(
            'DATABASE is not configured. Set it to the KeePass .kdbx path '
            '(default is <instance_path>/passwords.kdbx).'
        )
    try:
        with open(db_path, 'rb'):
            pass
    except FileNotFoundError:
        raise FileNotFoundError(
            f'KeePass database not found: {db_path}. '
            'pywebpass will not start until this file exists and is readable. '
            f'Place passwords.kdbx in the instance folder ({app.instance_path}). '
            'When rebuilding a virtualenv, copy the instance folder '
            '(passwords.kdbx and config.py) into the new environment.'
        ) from None
    except PermissionError:
        raise PermissionError(
            f'KeePass database is not readable: {db_path}.'
        ) from None
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise OSError(
            f'KeePass database cannot be read: {db_path} ({detail}).'
        ) from exc


def create_app(test_config=None, *, instance_path=None, require_database=None):
    """Create the Flask application.

    With no ``test_config``, startup fails if the configured ``DATABASE`` file
    is missing or not readable. Passing ``test_config`` skips that check unless
    ``require_database`` is true.
    """
    # create and configure the app
    flask_kwargs = {'instance_relative_config': True}
    if instance_path is not None:
        flask_kwargs['instance_path'] = instance_path
    app = Flask(__name__, **flask_kwargs)

    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, 'passwords.kdbx'),
        # Web UI only. Seconds. The browser tab clears the master password
        # after either limit. Override in instance config.py.
        UI_IDLE_TIMEOUT=15 * 60,
        UI_ABSOLUTE_TIMEOUT=8 * 60 * 60,
    )

    app.config['LOG_LEVEL'] = logging.WARNING
    app.config['LOG_TO_SYSTEMD'] = True

    config_loaded = False
    if test_config is None:
        # load the instance config, if it exists, when not testing
        config_loaded = app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    if require_database is None:
        require_database = test_config is None

    app.logger.setLevel(app.config['LOG_LEVEL'])

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    if require_database:
        _ensure_database_readable(app)

    if "WEBPASS_SYSTEMD" in os.environ:
        app.config['LOG_TO_SYSTEMD'] = parse_bool(os.environ.get("WEBPASS_SYSTEMD"))

    if app.config['LOG_TO_SYSTEMD']:
        if 'INVOCATION_ID' not in os.environ:
            os.environ['INVOCATION_ID'] = 'dummy'
        init_systemd_logging(logger=app.logger, syslog_id=__name__)

    if test_config is None and not config_loaded:
        config_path = os.path.join(app.instance_path, 'config.py')
        app.logger.warning(
            'Instance config not found at %s; using built-in defaults. '
            'Local development can omit config.py. Production should keep '
            'config.py in the instance folder and copy it when rebuilding the virtualenv.',
            config_path,
        )

    log_level = app.config.get('LOG_LEVEL')
    if isinstance(log_level, int):
        log_level = logging.getLevelName(log_level)
    app.logger.info(
        'pywebpass ready (instance_path=%s database=%s log_level=%s log_to_systemd=%s)',
        app.instance_path,
        app.config.get('DATABASE'),
        log_level,
        app.config.get('LOG_TO_SYSTEMD'),
    )
    if 'APP_PATH' in os.environ:
        app_prefix = os.environ.get('APP_PATH')
    else:
        app_prefix = ''
    app.register_blueprint(api_group, url_prefix=app_prefix + "/api")
    app.register_blueprint(api_secret, url_prefix=app_prefix + "/api")
    app.register_blueprint(api_datafile, url_prefix=app_prefix + "/api")
    app.register_blueprint(ui_page, url_prefix=app_prefix)

    # a simple page that says hello
    @app.route('/test')
    def hello():
        app.logger.info("got a request" + __name__)
        return 'Hello, World!'

    return app
