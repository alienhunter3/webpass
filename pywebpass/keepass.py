"""Module containing scripts working with keepass objects."""
from pykeepass import PyKeePass, entry, group
from .util import is_uuid, resolve_uuid
from uuid import UUID
from typing import Union


def authenticate(db_file: str, password: str) -> PyKeePass:
    return PyKeePass(db_file, password=password)


def root_group(keydb: PyKeePass) -> group:
    return keydb.find_groups_by_path([])


def find_group(keydb: PyKeePass, needle: str):
    needle = needle.strip()
    if needle == "":
        return root_group(keydb)

    if is_uuid(needle):
        result = keydb.find_groups(uuid=UUID(needle))
    elif needle[0] == "/":
        if needle == "/":
            return root_group(keydb)
        result = keydb.find_groups(path=needle[1:].split("/"))
    else:
        result = keydb.find_groups(name=needle)

    if type(result) is group:
        return group

    if type(result) is list:
        if len(result) == 1:
            return result[0]

    raise LookupError(f"Couldn't find group corresponding to '{needle}'")


def entry_to_dict(secret: entry) -> dict:
    attachments = []
    for a in secret.attachments:
        attachments.append({'id': a.id, 'file_name': a.filename})
    data = {'name': secret.title, 'path': f"/{'/'.join(secret.path)}", 'uuid': str(secret.uuid),
            'notes': secret.notes,
            'attachments': attachments, 'username': secret.username, 'password': secret.password,
            'url': secret.url}
    for key in secret.custom_properties.keys():
        var = key
        val = secret.custom_properties[var]
        if var in data:
            var = 'custom_' + var
        data[var] = val
    return data


def search_secrets(db: PyKeePass, term: str) -> list[entry]:
    all_secrets = db.entries
    secret_set = []
    if term == '':
        secret_set = all_secrets
    else:
        for s in all_secrets:
            if type(s.title) is str and term in s.title.lower():
                secret_set.append(s)
                continue
            if type(s.username) is str and term in s.username.lower():
                secret_set.append(s)
                continue
            if type(s.notes) is str and term in s.notes.lower():
                secret_set.append(s)
                continue
            for a in s.attachments:
                if term in a.filename.lower():
                    secret_set.append(s)
                    break
    return secret_set


def secret_by_uuid(db: PyKeePass, uuid: Union[bytes, int, str, UUID]) -> entry:
    uuid = resolve_uuid(uuid)
    secret = db.find_entries_by_uuid(uuid, first=True)
    if secret is None:
        raise KeyError(f"Couldn't find entry with UUID: {uuid}")
    return secret



