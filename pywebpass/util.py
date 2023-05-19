import os
import os.path
from configparser import ConfigParser
import logging
from systemdlogging.toolbox import init_systemd_logging
from uuid import UUID
from typing import Union


def parse_log_level(level: str) -> int:
    level = level.strip().lower()
    if level == 'info':
        return logging.INFO
    elif level == 'debug':
        return logging.DEBUG
    elif level == 'warning':
        return logging.WARNING
    elif level == 'ERROR':
        return logging.ERROR
    elif level == 'critical':
        return logging.CRITICAL
    else:
        return 0


def parse_bool(val: str) -> bool:
    val = val.lower().strip()
    if val in ["yes", "y", "1", "true", "enabled"]:
        return True
    else:
        return False


def setup():

    c = ConfigParser()

    c.add_section('main')

    # read in config files if they exist

    if os.path.isfile('/etc/pywebpass.ini'):
        c.read('/etc/pywebpass.ini')

    if os.path.isfile('./pywebpass.ini'):
        c.read('./pywebpass.ini')

    # set up logging

    env_level = parse_log_level(os.environ.get('WEBPASS_LOG_LEVEL', default=''))
    if env_level != 0:
        c['main']['log_level'] = str(env_level)
        logging.basicConfig(level=env_level)

    if "WEBPASS_SYSTEMD" in os.environ:
        log_systemd = parse_bool(os.environ.get("WEBPASS_SYSTEMD"))
        c['main']['log_to_systemd'] = str(log_systemd)
    else:
        if 'log_to_systemd' in c['main']:
            log_systemd = c['main'].getboolean('log_to_systemd')
        else:
            log_systemd = True

    if 'WEBPASS_LOG_NAME' in os.environ:
        log_name = os.environ.get('WEBPASS_LOG_NAME')
        c['main']['logging_name'] = log_name
    else:
        log_name = c['main'].get('logging_name', fallback='pywebpass')

    if log_systemd:
        if 'INVOCATION_ID' not in os.environ:
            os.environ['INVOCATION_ID'] = 'dummy'
        init_systemd_logging(syslog_id=log_name)

    # find the db

    if 'WEBPASS_DB' in os.environ:
        db_file = os.environ.get('WEBPASS_DB')
    else:
        db_file = c['main'].get('db', fallback='./passwords.kdbx')

    if os.path.isfile(db_file):
        c['main']['db'] = db_file
    else:
        raise FileNotFoundError(f"Could not find db file at '{db_file}'.")

    configuration = c


def is_uuid(val: str) -> bool:
    try:
        temp = UUID(val.strip())
    except ValueError as e:
        return False
    return True


def resolve_uuid(uuid: Union[str, bytes, UUID, int]) -> UUID:
    t = type(uuid)
    if t is int:
        uuid = UUID(int=uuid)
    elif t is bytes:
        uuid = UUID(bytes=uuid)
    elif t is UUID:
        pass
    else:
        uuid = UUID(str(uuid))
    return uuid
