from pywebpass import keepass
from pykeepass import PyKeePass, entry, group
from typing import Union, IO
from uuid import UUID
from io import BytesIO


class KeepassClient:

    def __init__(self, db_file: Union[IO, str], password: str):
        self.db = PyKeePass(db_file, password)

    @property
    def groups(self) -> list:
        data = [{'uuid': str(x.uuid), 'name': x.name} for x in self.db.groups]
        return data

    @property
    def all_secrets(self) -> list:
        data = []
        for secret in self.db.entries:
            d = keepass.entry_to_dict(secret)
            data.append(d)
        return data

    def search(self, needle: str) -> list:
        entries = keepass.search_secrets(self.db, needle)
        data = []
        for secret in entries:
            d = keepass.entry_to_dict(secret)
            data.append(d)
        return data

    def secret_uuid(self, uuid: Union[str, UUID, bytes, int]) -> dict:
        secret = keepass.secret_by_uuid(self.db, uuid)
        return keepass.entry_to_dict(secret)

    def secret_group_name(self, group_name: str) -> list:
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
        secret = keepass.secret_by_uuid(self.db, uuid)
        attachment = None
        for a in secret.attachments:
            if index == a.id:
                attachment = a
                break
        if attachment is None:
            raise KeyError(f"Secret didn't contain attachment with index {index}")
        return BytesIO(a.binary)
