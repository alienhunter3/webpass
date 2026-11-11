# PLACE THIS IN THE INSTANCE FOLDER, NEXT TO passwords.kdbx
# Development checkout: <repo>/instance/config.py
# Virtualenv install: <venv>/var/pywebpass-instance/config.py
# Optional for local runs (built-in logging defaults apply). Keep this file
# with passwords.kdbx when rebuilding a virtualenv; pip does not preserve it.
# DATABASE defaults to <instance_path>/passwords.kdbx and can be set here.

import logging

LOG_TO_SYSTEMD = True
# INFO or WARNING in production. DEBUG is noisy, and the Flask debugger
# (flask run --debug) can show the master password from request locals.
LOG_LEVEL = logging.INFO

# Web UI session limits, in seconds. Omit both to keep the defaults
# (15 minutes idle, 8 hours absolute). The master password is held only
# in the browser tab and is cleared when either limit is reached.
# UI_IDLE_TIMEOUT = 15 * 60
# UI_ABSOLUTE_TIMEOUT = 8 * 60 * 60

# Defaults to True. Behind nginx TLS, leave it true and pass REQUEST_SCHEME
# and HTTPS from uwsgi_params (see the deployment docs). Local HTTP only:
# REQUIRE_HTTPS = False

