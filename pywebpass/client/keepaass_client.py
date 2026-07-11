"""Direct KeePass (``.kdbx``) backend used by :class:`~pywebpass.client.client.ClientProxy`."""

from pywebpass import keepass
from pykeepass import PyKeePass, entry, group
from typing import Union, IO
from uuid import UUID
from io import BytesIO


class KeepassClient:
    """Read-oriented client that opens a local KeePass database.

    Args:
        db_file: Path or file-like object for the ``.kdbx`` database.
        password: KeePass master password.
    """

    def __init__(self, db_file: Union[IO, str], password: str):
        self.db = PyKeePass(db_file, password)

    @property
    def groups(self) -> list:
        """List all groups as ``{"uuid", "name"}`` dicts."""
        data = [{'uuid': str(x.uuid), 'name': x.name} for x in self.db.groups]
        return data

    @property
    def all_secrets(self) -> list:
        """Return all entries as dicts (see :func:`pywebpass.keepass.entry_to_dict`)."""
        data = []
        for secret in self.db.entries:
            d = keepass.entry_to_dict(secret)
            data.append(d)
        return data

    def search(self, needle: str) -> list:
        """Search entries and return matching dicts."""
        entries = keepass.search_secrets(self.db, needle)
        data = []
        for secret in entries:
            d = keepass.entry_to_dict(secret)
            data.append(d)
        return data

    def secret_uuid(self, uuid: Union[str, UUID, bytes, int]) -> dict:
        """Return one entry by UUID as a dict."""
        secret = keepass.secret_by_uuid(self.db, uuid)
        return keepass.entry_to_dict(secret)

    def secret_group_name(self, group_name: str) -> list:
        """Return entries in the named group (case-insensitive) as dicts."""
        group_name = group_name.strip().lower()
        groups = self.groups
        secrets = []
        for group in groups:
            if group_name == group['name'].strip().lower():
                guuid = UUID(group['uuid'])
                group_obj = self.db.find_groups_by_uuid(guuid, first=True)
                for secret in group_obj.entries:
                    secrets.append(keepass.entry_to_dict(secret))
        return secrets

    def secret_attachment(self, uuid: Union[str, UUID, bytes, int], index: int) -> BytesIO:
        """Return attachment binary data for ``index`` on the given secret."""
        secret = keepass.secret_by_uuid(self.db, uuid)
        attachment = None
        for a in secret.attachments:
            if index == a.id:
                attachment = a
                break
        if attachment is None:
            raise KeyError(f"Secret didn't contain attachment with index {index}")
        return BytesIO(a.binary)
