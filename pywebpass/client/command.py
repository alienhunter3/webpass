from argparse import ArgumentParser

import requests

from .client import ClientProxy, Secret, AccessDeniedError
from .config import load_config, create_local_data, get_file_time, map_string_to_cache_file
from .config import create_local_data, write_config_template, create_cache_dir, cache_file_expired
from .password import generate_password
from typing import Union
import json
from getpass import getpass
from configparser import ConfigParser
import sys
import base64
from io import BytesIO
from importlib.metadata import PackageNotFoundError, version as package_version

import os
from os.path import join, isdir, isfile, basename, getsize
from tempfile import TemporaryFile

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
PACKAGE_NAME = "pywebpass"


def handle_args():
    parser = ArgumentParser(description="Interact with secrets.")
    parser.add_argument("-a", "--address", type=str)
    parser.add_argument("-p", "--password", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("-k", "--allow-ssl", action="store_true")
    parser.add_argument("-S", "--sync", action="store_true")
    parser.add_argument("-C", "--no-config", action="store_true")
    parser.add_argument("-F", "--show-file", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)
    get_parser = subparsers.add_parser("get", help="Search and retrieve secrets.")
    get_parser.add_argument("-u", "--uuid", type=str)
    get_parser.add_argument("-f", "--format", choices=['pretty', 'json', 'row'], default="row")
    get_parser.add_argument("-n", "--no-header", action="store_true")
    get_parser.add_argument("-c", "--column", action="append")
    get_parser.add_argument("--show-all", action='store_true')
    get_parser.add_argument("-s", "--search", type=str)
    get_parser.add_argument("-g", "--group", type=str)
    get_parser.add_argument("-i", "--file-index", type=int)
    get_parser.add_argument("-o", "--file-out", type=str)

    gen_parser = subparsers.add_parser("generate", help="Generate a random password.")
    gen_parser.add_argument("-l", "--length", type=int, default=24, help="Password length (default: 24)")
    gen_parser.add_argument("-n", "--count", type=int, default=1, help="Number of passwords to generate (default: 1)")
    gen_parser.add_argument("--no-lowercase", action="store_true", help="Exclude lowercase letters")
    gen_parser.add_argument("--no-uppercase", action="store_true", help="Exclude uppercase letters")
    gen_parser.add_argument("--no-digits", action="store_true", help="Exclude digits")
    gen_parser.add_argument("--no-symbols", action="store_true", help="Exclude symbols")
    gen_parser.add_argument("--allowed-symbols", type=str, default=None,
                            help="Subset of allowed symbols (string of characters from the default set)")
    gen_parser.add_argument("--no-ambiguous", action="store_true",
                            help="Exclude ambiguous characters (0, O, 1, l, I, |)")

    add_parser = subparsers.add_parser("add", help="Create a new secret via the API.")
    add_parser.add_argument("-t", "--title", type=str, required=True, help="Secret title")
    add_parser.add_argument("-u", "--username", type=str, default="", help="Username")
    add_parser.add_argument("-P", "--entry-password", type=str, default=None,
                            help="Password for the secret (prompted if omitted and --generate is not set)")
    add_parser.add_argument("--generate", action="store_true",
                            help="Generate a random password for the secret")
    add_parser.add_argument("-l", "--length", type=int, default=24,
                            help="Generated password length (default: 24; requires --generate)")
    add_parser.add_argument("--no-lowercase", action="store_true", help="Exclude lowercase letters from generated password")
    add_parser.add_argument("--no-uppercase", action="store_true", help="Exclude uppercase letters from generated password")
    add_parser.add_argument("--no-digits", action="store_true", help="Exclude digits from generated password")
    add_parser.add_argument("--no-symbols", action="store_true", help="Exclude symbols from generated password")
    add_parser.add_argument("--allowed-symbols", type=str, default=None,
                            help="Subset of allowed symbols for generated password")
    add_parser.add_argument("--no-ambiguous", action="store_true",
                            help="Exclude ambiguous characters from generated password")
    add_parser.add_argument("--url", type=str, default="", help="URL")
    add_parser.add_argument("-n", "--notes", type=str, default="", help="Notes")
    add_parser.add_argument("-g", "--group", type=str, default="",
                            help="Group name, path (e.g. /Work), or UUID (default: root)")
    add_parser.add_argument("-e", "--extra", action="append", default=[],
                            help="Custom property as KEY=VALUE (repeatable)")

    upd_parser = subparsers.add_parser("update", help="Update an existing secret via the API.")
    upd_parser.add_argument("-u", "--uuid", type=str, required=True, help="UUID of the secret to update")
    upd_parser.add_argument("-t", "--title", type=str, default=None, help="New title")
    upd_parser.add_argument("--username", type=str, default=None, help="New username")
    upd_parser.add_argument("-P", "--entry-password", nargs="?", const="", default=None,
                            help="New password (omit value to prompt; do not set to leave unchanged)")
    upd_parser.add_argument("--generate", action="store_true",
                            help="Generate a new random password for the secret")
    upd_parser.add_argument("-l", "--length", type=int, default=24,
                            help="Generated password length (default: 24; requires --generate)")
    upd_parser.add_argument("--no-lowercase", action="store_true", help="Exclude lowercase letters from generated password")
    upd_parser.add_argument("--no-uppercase", action="store_true", help="Exclude uppercase letters from generated password")
    upd_parser.add_argument("--no-digits", action="store_true", help="Exclude digits from generated password")
    upd_parser.add_argument("--no-symbols", action="store_true", help="Exclude symbols from generated password")
    upd_parser.add_argument("--allowed-symbols", type=str, default=None,
                            help="Subset of allowed symbols for generated password")
    upd_parser.add_argument("--no-ambiguous", action="store_true",
                            help="Exclude ambiguous characters from generated password")
    upd_parser.add_argument("--url", type=str, default=None, help="New URL")
    upd_parser.add_argument("-n", "--notes", type=str, default=None, help="New notes")
    upd_parser.add_argument("-e", "--extra", action="append", default=[],
                            help="Custom property as KEY=VALUE (repeatable)")

    att_parser = subparsers.add_parser(
        "add-attachment",
        help="Add an attachment to an existing secret via the API.",
    )
    att_parser.add_argument("-u", "--uuid", type=str, required=True, help="UUID of the secret")
    att_parser.add_argument(
        "-f", "--file", type=str, default=None,
        help="Path to a local file to attach (max 10MB; filename taken from the path)",
    )
    att_parser.add_argument(
        "-n", "--name", type=str, default=None,
        help="Attachment name (required with --stdin or --base64)",
    )
    att_parser.add_argument(
        "--stdin", action="store_true",
        help="Read attachment bytes from stdin (requires --name)",
    )
    att_parser.add_argument(
        "-b", "--base64", type=str, default=None,
        help="Base64-encoded attachment data (requires --name)",
    )

    subparsers.add_parser("version", help="Print the installed pywebpass package version.")
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
    arg_parser = handle_args()
    args = arg_parser.parse_args()

    if args.command == "generate":
        _run_generate(args)
        return

    if args.command == "version":
        _run_version()
        return

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

    # mutating commands always use the API; never write to the local KeePass cache
    if args.command in ("add", "update", "add-attachment"):
        client = ClientProxy.api_proxy(cfg['API']['api_address'], cfg['API']['api_password'])
        if args.command == "add":
            _run_add(args, client)
        elif args.command == "update":
            _run_update(args, client)
        else:
            _run_add_attachment(args, client)
        return

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

    if args.command == "get":
        _run_get(args, client)


def _parse_extra(extra_args: list) -> dict:
    props = {}
    for item in extra_args:
        if "=" not in item:
            raise RuntimeError(f"Invalid --extra value '{item}'; expected KEY=VALUE")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise RuntimeError(f"Invalid --extra value '{item}'; key must not be empty")
        props[key] = value
    return props


def _resolve_entry_password(args) -> str:
    generate_flags = [
        args.no_lowercase, args.no_uppercase, args.no_digits, args.no_symbols,
        args.no_ambiguous, args.allowed_symbols is not None,
    ]
    # length differs from default only matters with --generate; still require --generate for charset flags
    if any(generate_flags) and not args.generate:
        raise RuntimeError("Password generation options require --generate")
    if args.generate and args.entry_password is not None:
        raise RuntimeError("Cannot use --generate together with -P/--entry-password")

    if args.generate:
        return generate_password(
            args.length,
            lowercase=not args.no_lowercase,
            uppercase=not args.no_uppercase,
            digits=not args.no_digits,
            symbols=not args.no_symbols,
            allowed_symbols=args.allowed_symbols,
            exclude_ambiguous=args.no_ambiguous,
        )
    if args.entry_password is not None:
        return args.entry_password
    return getpass("Password for new secret:")


def _resolve_update_password(args) -> Union[str, None]:
    """Return a new password to set, or None if the password should be left unchanged."""
    generate_flags = [
        args.no_lowercase, args.no_uppercase, args.no_digits, args.no_symbols,
        args.no_ambiguous, args.allowed_symbols is not None,
    ]
    if any(generate_flags) and not args.generate:
        raise RuntimeError("Password generation options require --generate")
    if args.generate and args.entry_password is not None:
        raise RuntimeError("Cannot use --generate together with -P/--entry-password")

    if args.generate:
        return generate_password(
            args.length,
            lowercase=not args.no_lowercase,
            uppercase=not args.no_uppercase,
            digits=not args.no_digits,
            symbols=not args.no_symbols,
            allowed_symbols=args.allowed_symbols,
            exclude_ambiguous=args.no_ambiguous,
        )
    if args.entry_password is not None:
        if args.entry_password == "":
            return getpass("New password for secret:")
        return args.entry_password
    return None


def _run_add(args, client: ClientProxy):
    password = _resolve_entry_password(args)
    extra = _parse_extra(args.extra) if args.extra else None
    uuid = client.create_secret(
        title=args.title,
        username=args.username,
        password=password,
        url=args.url,
        notes=args.notes,
        group=args.group,
        extra=extra,
    )
    if args.generate:
        print(password, file=sys.stderr)
    print(uuid)


def _run_update(args, client: ClientProxy):
    password = _resolve_update_password(args)
    extra = _parse_extra(args.extra) if args.extra else None

    if all(v is None for v in (args.title, args.username, password, args.url, args.notes)) and not extra:
        raise RuntimeError("Must specify at least one field to update")

    uuid = client.update_secret_fields(
        args.uuid,
        title=args.title,
        username=args.username,
        password=password,
        url=args.url,
        notes=args.notes,
        extra=extra,
    )
    if args.generate:
        print(password, file=sys.stderr)
    print(uuid)


def _check_attachment_size(size: int, label: str) -> None:
    if size > MAX_ATTACHMENT_BYTES:
        raise RuntimeError(
            f"{label} is {size} bytes; attachments must be at most {MAX_ATTACHMENT_BYTES} bytes (10MB)"
        )
    if size == 0:
        raise RuntimeError(f"{label} is empty; refusing to upload an empty attachment")


def _run_add_attachment(args, client: ClientProxy):
    file_mode = args.file is not None
    stdin_mode = args.stdin
    b64_mode = args.base64 is not None

    mode_count = sum([file_mode, stdin_mode, b64_mode])
    if mode_count == 0:
        raise RuntimeError("Must supply attachment data via --file, --stdin, or --base64")
    if mode_count > 1:
        raise RuntimeError("Use only one of --file, --stdin, or --base64")

    if file_mode:
        if args.name is not None:
            raise RuntimeError("Cannot use --name with --file (filename is taken from the path)")
        if not isfile(args.file):
            raise RuntimeError(f"File not found: {args.file}")
        size = getsize(args.file)
        _check_attachment_size(size, args.file)
        file_name = basename(args.file)
        with open(args.file, "rb") as fh:
            client.add_attachment(args.uuid, fh, file_name)
        return

    if args.name is None or args.name.strip() == "":
        raise RuntimeError("--name is required when using --stdin or --base64")
    file_name = args.name.strip()

    if stdin_mode:
        data = sys.stdin.buffer.read()
        _check_attachment_size(len(data), "stdin input")
    else:
        try:
            data = base64.b64decode(args.base64, validate=True)
        except Exception as e:
            raise RuntimeError(f"Invalid base64 data: {e}") from e
        _check_attachment_size(len(data), "base64 input")

    client.add_attachment(args.uuid, BytesIO(data), file_name)


def _run_generate(args):
    if args.count < 1:
        raise RuntimeError("count must be at least 1")
    if args.length < 1:
        raise RuntimeError("length must be at least 1")

    for _ in range(args.count):
        print(generate_password(
            args.length,
            lowercase=not args.no_lowercase,
            uppercase=not args.no_uppercase,
            digits=not args.no_digits,
            symbols=not args.no_symbols,
            allowed_symbols=args.allowed_symbols,
            exclude_ambiguous=args.no_ambiguous,
        ))


def _run_version():
    try:
        print(package_version(PACKAGE_NAME))
    except PackageNotFoundError:
        raise RuntimeError(
            f"Package '{PACKAGE_NAME}' is not installed; install it (e.g. pip install -e .) to report a version"
        )


def _run_get(args, client):
    output = []
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

    # check search flags
    search_count = 0
    for i in [args.group, args.search, args.uuid]:
        if i is not None:
            search_count = search_count + 1
    if search_count > 1:
        raise RuntimeError("Cannot use more than one of [-s, -g, -u].")

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
