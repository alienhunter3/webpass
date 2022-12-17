import os
import logging
from flask import Flask
from systemdlogging.toolbox import init_systemd_logging
from .util import parse_bool


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, 'passwords.kdbx'),
    )

    app.config['LOG_LEVEL'] = logging.WARNING
    app.config['LOG_TO_SYSTEMD'] = True

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
    print(app.config)
    app.logger.setLevel(app.config['LOG_LEVEL'])

    if "WEBPASS_SYSTEMD" in os.environ:
        app.config['LOG_TO_SYSTEMD'] = parse_bool(os.environ.get("WEBPASS_SYSTEMD"))

    if app.config['LOG_TO_SYSTEMD']:
        if 'INVOCATION_ID' not in os.environ:
            os.environ['INVOCATION_ID'] = 'dummy'
        init_systemd_logging(logger=app.logger, syslog_id=__name__)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        app.logger.info("got a request" + __name__)
        return 'Hello, World!'

    return app
