"""Module containing scripts working with keepass objects."""
from pykeepass import PyKeePass, entry


def authenticate(db_file: str, password: str) -> PyKeePass:
    return PyKeePass(db_file, password=password)
