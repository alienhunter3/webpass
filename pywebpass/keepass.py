"""Module containing scripts working with keepass objects."""
from pykeepass import PyKeePass, entry


def authenticate(db_file: str, password: str) -> PyKeePass:
    return PyKeePass(db_file, password=password)


def search_secrets(db_file: str, password: str) -> list[entry]:
    # @todo
    return []
