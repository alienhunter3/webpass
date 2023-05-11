"""Module containing scripts working with keepass objects."""
from pykeepass import PyKeePass, entry, group
from .util import is_uuid
from uuid import UUID


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




