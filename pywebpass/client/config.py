from configparser import ConfigParser
import os
from os.path import isfile, join, exists
from pathlib import Path
from .constants import config_template
import hashlib
from datetime import timedelta, datetime


if "XDG_CONFIG_HOME" in os.environ:
    xdg_config_dir = join(os.environ.get("XDG_CONFIG_HOME"), ".config")
else:
    xdg_config_dir = str(Path.home().joinpath(".config"))

if "XDG_CACHE_HOME" in os.environ:
    rel_cache_path = join(".local", "share")
    xdg_data_dir = join(os.environ.get("XDG_CACHE_HOME"), rel_cache_path)
else:
    xdg_data_dir = str(Path.home().joinpath(".local", "share"))

config_dir = join(xdg_config_dir, "webpass")
data_dir = join(xdg_data_dir, "webpass")
cache_db_dir = join(data_dir, "cache")
config_file_path = join(config_dir, 'config.ini')


def write_config_template():
    Path(config_dir).mkdir(parents=True, exist_ok=True)
    if not exists(config_file_path):
        open(config_file_path, 'w').write(config_template)


def create_local_data():
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    Path(cache_db_dir).mkdir(parents=True, exist_ok=True)
    write_config_template()


def create_cache_dir():
    Path(cache_db_dir).mkdir(parents=True, exist_ok=True)


def map_string_to_cache_file(string: str) -> str:
    hash_str = hashlib.md5(string.encode('utf-8')).hexdigest()
    file_name = hash_str + ".kdbx"
    return join(cache_db_dir, file_name)


def load_config(use_local=True) -> ConfigParser:
    config = ConfigParser()
    config.add_section("API")
    config['API']['cache'] = 'yes'
    config['API']['cache_timeout'] = "1h"
    config['API']['api_password'] = ""
    if use_local:
        create_local_data()
        write_config_template()
        if isfile(config_file_path):
            config.read(config_file_path)

    if "WEBPASS_PASSWD" in os.environ:
        config['API']['api_password'] = os.environ['WEBPASS_PASSWD']

    if "WEBPASS_ADDRESS" in os.environ:
        config['API']['api_address'] = os.environ['WEBPASS_ADDRESS']

    return config


def parse_delta(delta: str) -> timedelta:
    if not str.isalnum(delta):
        raise ValueError("timeout string must be in form of <quantity><unit_code>. Ex: 1h, 10s, 1d")

    if str.isnumeric(delta):
        return timedelta(seconds=int(delta))

    if not str.isalpha(delta[-1]) or (len(delta) < 2):
        raise ValueError("timeout string must be in form of <quantity><unit_code>. Ex: 1h, 10s, 1d")

    if not str.isnumeric(delta[:-1]):
        raise ValueError("timeout string must be in form of <quantity><unit_code>. Ex: 1h, 10s, 1d")

    unit = delta[-1].lower()
    quant = int(delta[:-1])

    if unit == "s":
        second_factor = 1
    elif unit == "m":
        second_factor = 60
    elif unit == "h":
        second_factor = 3600
    elif unit == "d":
        second_factor = 86400
    else:
        raise ValueError("Supported time units are ['h', 's', 'm', 'd']")

    return timedelta(seconds=(second_factor * quant))


def get_file_time(file_path: str) -> datetime:
    stamp = os.path.getmtime(file_path)
    return datetime.fromtimestamp(stamp)


def cache_file_expired(cfg: ConfigParser, file_path) -> bool:
    timeout = cfg['API'].get('cache_timeout', fallback="1h")
    td = parse_delta(timeout)
    file_time = get_file_time(file_path)
    if datetime.now() > file_time + td:
        return True
    else:
        return False
