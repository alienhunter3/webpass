# PLACE THIS IN THE INSTANCE FOLDER, NEXT TO passwords.kdbx
# Development checkout: <repo>/instance/config.py
# Virtualenv install: <venv>/var/pywebpass-instance/config.py
# Optional for local runs (built-in logging defaults apply). Keep this file
# with passwords.kdbx when rebuilding a virtualenv; pip does not preserve it.
# DATABASE defaults to <instance_path>/passwords.kdbx and can be set here.

import logging

LOG_TO_SYSTEMD = True
LOG_LEVEL = logging.DEBUG

