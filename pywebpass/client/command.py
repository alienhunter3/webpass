from argparse import ArgumentParser

import requests

from .client import ClientProxy, Secret, AccessDeniedError
from .config import load_config, create_local_data, get_file_time, map_string_to_cache_file
from .config import create_local_data, write_config_template, create_cache_dir, cache_file_expired
from typing import Union
import json
from getpass import getpass
from configparser import ConfigParser
import sys

import os
from os.path import join, isdir, isfile
from tempfile import TemporaryFile


def handle_args():
    parser = ArgumentParser(description="Interact with secrets.")
    parser.add_argument("-a", "--address", type=str)
    parser.add_argument("-u", "--uuid", type=str)
    parser.add_argument("-p", "--password", action="store_true")
    parser.add_argument("-f", "--format", choices=['pretty', 'json', 'row'], default="row")
    parser.add_argument("-n", "--no-header", action="store_true")
    parser.add_argument("-c", "--column", action="append")
    parser.add_argument("--show-all", action='store_true')
    parser.add_argument("-s", "--search", type=str)
    parser.add_argument("-g", "--group", type=str)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("-k", "--allow-ssl", action="store_true")
    parser.add_argument("-S", "--sync", action="store_true")
    parser.add_argument("-C", "--no-config", action="store_true")
    parser.add_argument("-F", "--show-file", action="store_true")
    parser.add_argument("-i", "--file-index", type=int)
    parser.add_argument("-o", "--file-out", type=str)
    return parser


def json_formatter(secrets: list[Secret], fields: list[str]):
    output_array = []
    for secret in secrets:
        if len(fields) == 0:
            output_array.append(secret.json)
            continue
        output_array.append(json.loads(secret.json_fields(fields)))
    print(json.dumps({"secrets": output_array}))


def secret_formatter(secret: Secret, fields: list[str], fmt="row") -> str:
    output = ""
    d = secret.dict
    if len(fields) == 0:
        for field in d:
            fields.append(field)
    if fmt == "pretty":
        for field in fields:
            if field not in d.keys():
                if field in d['custom_properties']:
                    output = output + f"custom_{field}: {d['custom_properties'][field]}\n"
                    continue
                else:
                    continue
            if field not in ["files", "custom_properties"]:
                output = output + f"{field}: {str(d[field])}\n"
            elif field == "files":
                output = output + "files:\n"
                for i in d['files']:
                    output = output + f"  {i.short_string()}\n"
            elif field == "custom_properties":
                output = output + "Custom Properties:\n"
                for i in d['custom_properties']:
                    output = output + f"  {i}: {d['custom_properties'][i]}\n"
    elif fmt == "row":
        first = True
        for field in fields:
            if not first:
                output = output + "|"
            else:
                first = False
            if field not in ["files", "custom_properties"]:
                if field not in d.keys():
                    if field in d['custom_properties']:
                        output = output + d['custom_properties'][field]
                        continue
                    else:
                        continue
            if field not in ["files", "custom_properties"]:
                output = output + str(d[field])
            elif field == "files":
                files = []
                for file in d['files']:
                    files.append(file.short_string())
                output = output + ",".join(files)
            elif field == "custom_properties":
                output = output + json.dumps(d['custom_properties'])
    return output


def formatter(objects: list, columns: Union[list, None] = None, fmt="row", show_all=False, no_header=False):
    if columns is None or (len(columns) == 0):
        fields = ["title", "username", "uuid"]
    else:
        fields = []
        for i in columns:
            for k in i.split(","):
                fields.append(k.strip())

    if show_all:
        fields = []

    if len(objects) == 0:
        return

    if type(objects[0]) is not Secret:
        raise ValueError("formatter function received non-secret formatted object.")

    if fmt == "json":
        return json_formatter(objects, fields)

    if (fmt == "row") and not no_header:
        print("|".join(fields))

    first = True
    for secret in objects:
        if fmt == "pretty" and not first:
            print("-----------------------------")
        print(secret_formatter(secret, fields, fmt))
        first = False


def sync_db(cfg: ConfigParser):
    db_path = map_string_to_cache_file(cfg['API']['api_address'])
    addr = cfg['API']['api_address']
    p = cfg['API']['api_password']
    r = requests.get(f"{addr}/file", auth=('', p))
    if r.status_code == 401:
        raise AccessDeniedError("Credentials incorrect.")
    if r.status_code != 200:
        raise requests.HTTPError(f"HTTP Error connecting to {addr}: {r.status_code}")
    else:
        open(db_path, 'wb').write(r.content)


def main():
    output = []
    arg_parser = handle_args()
    args = arg_parser.parse_args()
    get_attachment = False

    # pre-validation

    file_count = 0
    for i in [args.file_out, args.file_index]:
        if i is not None:
            file_count = file_count + 1

    if file_count == 1:
        raise RuntimeError("Cannot use -o without -i, or -i without -o.")

    if file_count == 2:
        if args.uuid is None:
            raise RuntimeError("Cannot use attachment retrieval operations without using -u flag.")
        get_attachment = True

    # setup config



    if args.no_config:
        cfg = load_config(use_local=False)
    else:
        cfg = load_config(use_local=True)

    if args.password:
        cfg['API']['api_password'] = getpass("Password for API:")

    if args.address is not None:
        cfg['API']['api_address'] = args.address

    if 'api_address' not in cfg['API']:
        raise RuntimeError("Must provide api_address through WEBPASS_ADDRESS, -a argument, or config_file")

    if args.no_cache:
        cfg['API']['cache'] = 'no'

    # check search flags
    search_count = 0
    for i in [args.group, args.search, args.uuid]:
        if i is not None:
            search_count = search_count + 1
    if search_count > 1:
        raise RuntimeError("Cannot use more than one of [-s, -g, -u].")

    # prepare client
    client = None
    if cfg['API'].getboolean("cache"):
        create_cache_dir()
        db_path = map_string_to_cache_file(cfg['API']['api_address'])
        if args.sync or (not isfile(db_path)) or cache_file_expired(cfg, db_path):
            sync_db(cfg)

        client = ClientProxy.keepass_proxy(db_path, cfg['API']['api_password'])

    else:
        client = ClientProxy.api_proxy(cfg['API']['api_address'], cfg['API']['api_password'])

    # break
    if args.show_file and not args.no_cache:
        print(map_string_to_cache_file(cfg['API']['api_address']))
        sys.exit(0)
    # perform query

    if (args.uuid is None) and (args.search is None) and (args.group is None):
        output = client.get_all_secrets()
    else:
        if args.uuid is not None:
            output.append(client.get_secret_uuid(args.uuid))
        elif args.search is not None:
            for i in client.search(args.search):
                output.append(i)
        else:
            for i in client.get_group_secrets(args.group):
                output.append(i)

    if get_attachment:
        if len(output) != 1:
            raise RuntimeError("UUID must match exactly one secret, to retrieve attached files.")
        found = None
        for f in output[0].files:
            if args.file_index == f.index:
                found = f
                break
        if found is None:
            raise KeyError(f"This secret doesn't contain an attachment with index {args.file_index}")

        stream = found.get_file()
        if args.file_out == "-":
            dest = sys.stdout.buffer
        else:
            dest = open(args.file_out, 'wb')
        dest.write(stream.read())
    else:
        formatter(output, args.column, fmt=args.format, show_all=args.show_all, no_header=args.no_header)


if __name__ == "__main__":
    raise SystemExit(main())
