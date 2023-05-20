from __future__ import annotations
from .api_client import ApiClient
from .keepaass_client import KeepassClient
from typing import Union, IO
from uuid import UUID
from pywebpass.util import resolve_uuid
from pywebpass.keepass import entry_to_dict
from enum import Enum
from dataclasses import dataclass
from pykeepass import entry

from tempfile import TemporaryFile
import json

same_fields = ["url", "notes", "username", "password", "uuid"]


@dataclass
class Attachment:
    index: int
    file_name: str
    parent: Secret

    def get_file(self):
        return self.parent.get_file(self.index)

    def short_string(self):
        return f"[{self.index}]{self.file_name}"


class Secret:

    def __init__(self, data: Union[dict, None] = None, client: Union[ClientProxy, None] = None):
        self._username = ''
        self._password = ''
        self._files = []
        self._notes = ''
        self._path = ''
        self._url = ''
        self._title = ''
        self._custom = {}
        self._changed = set()
        self._uuid = None
        self._parent = client

        for field in data:
            field.strip().lower()
            if field in same_fields:
                self.__setattr__(field, data[field])
            elif field == "files":
                self._custom[field] = str(data[field])
            elif field == "attachments":
                if type(data[field]) is list:
                    for i in data[field]:
                        self._files.append(Attachment(index=i['id'], file_name=i['file_name'], parent=self))
                else:
                    continue
            elif field == 'name':
                self.__setattr__('title', data['name'])
            elif field == "title":
                self._custom[field] = str(data[field])
            elif field == "path":
                self._path = str(data["path"])
            else:
                self._custom[field] = str(data[field])
        self._changed = set()

    def __repr__(self):
        return f"Secret({str(self.uuid)})"

    def __str__(self):
        return self.__repr__()

    @staticmethod
    def secret_from_entry(secret: entry) -> Secret:
        return Secret(entry_to_dict(secret))

    @property
    def dict(self) -> dict:
        output = {}
        for key in ("username", "password", "notes", "path", "url", "title", "uuid"):
            output[key] = self.__getattribute__(key)
        output['files'] = self.files
        output['custom_properties'] = self.custom_properties
        return output

    @property
    def json(self) -> str:
        d = self.dict
        d['uuid'] = str(d['uuid'])
        atts = []
        for i in d['files']:
            atts.append({'index': i.index, 'file_name': i.file_name})
        d['files'] = atts
        return json.dumps(d)

    @property
    def changed(self) -> bool:
        if len(self._changed) > 0:
            return True
        else:
            return False

    @property
    def changes(self) -> list:
        return list(self._changed)

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, new_value: Union[str, None]):
        if new_value is None:
            new_value = ''
        self._changed.add("username")
        self._username = str(new_value)

    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, new_value: Union[str, None]):
        if new_value is None:
            new_value = ''
        self._changed.add("password")
        self._password = str(new_value)

    @property
    def notes(self) -> str:
        return self._notes

    @notes.setter
    def notes(self, new_value: Union[str, None]):
        if new_value is None:
            new_value = ''
        self._changed.add("notes")
        self._notes = str(new_value)

    @property
    def path(self) -> str:
        return self._path

    @path.setter
    def path(self, new_value):
        raise RuntimeError("Cannot manually change path")

    @property
    def url(self) -> str:
        return self._url

    @url.setter
    def url(self, new_value: Union[str, None]):
        if new_value is None:
            new_value = ''
        self._changed.add("url")
        self._url = str(new_value)

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, new_value: Union[str, None]):
        if new_value is None:
            new_value = ''
        self._changed.add("title")
        self._title = str(new_value)

    @property
    def uuid(self) -> Union[UUID, None]:
        return self._uuid

    @uuid.setter
    def uuid(self, new_value: Union[str, bytes, UUID, int]):
        t = type(new_value)
        if t is int:
            new_value = UUID(int=new_value)
        elif t is bytes:
            new_value = UUID(bytes=new_value)
        elif t is UUID:
            pass
        else:
            new_value = UUID(str(new_value))

        if new_value == self._uuid:
            return

        self._changed.add("uuid")
        self._uuid = new_value

    @property
    def files(self) -> list:
        if self._parent is None:
            return []
        else:
            return self._files

    @property
    def custom_properties(self):
        return self._custom.copy()

    def update_property(self, key: str, value: str):
        self._parent.update_property(self, key, value)

    def update(self):
        if not self.changed:
            return

        if self._parent is not None:
            self._parent.update_secret(self)

        self._changed = set()

    def get_file(self, file_index: int) -> IO:
        if self._parent is None:
            raise RuntimeError("Parent doesn't exist. Cannot retrieve attached files.")
        return self._parent.get_file_index(self, file_index)

    def add_file(self, new_file: Union[str, IO]):  # TODO
        pass

    def json_fields(self, fields: list) -> str:
        temp = {}
        d = self.dict
        for field in fields:
            temp[field] = d[field]
            if field == "uuid":
                temp['uuid'] = str(temp['uuid'])
        return json.dumps(temp)


class Backend(Enum):
    API = 1
    KEEPASS_FILE = 2
    DUMMY = 3


class ClientProxy:  # TODO

    def __init__(self, client: Union[ApiClient, KeepassClient]):
        self.client = client

    @staticmethod
    def api_proxy(base_url: str, password: str) -> ClientProxy:
        return ClientProxy(ApiClient(base_url, password))

    @staticmethod
    def keepass_proxy(db_file: Union[str, IO], password: str) -> ClientProxy:
        return ClientProxy(KeepassClient(db_file, password))

    def get_secret_uuid(self, uuid: Union[UUID, int, bytes, str]) -> Secret:
        secret_raw = self.client.secret_uuid(resolve_uuid(uuid))
        return Secret(secret_raw, client=self)

    def get_all_secrets(self) -> list:
        secrets = self.client.all_secrets
        return [Secret(x, client=self) for x in secrets]

    def update_secret(self, secret: Secret):  # TODO
        pass

    def get_file_index(self, secret: Secret, index: int) -> IO:
        return self.client.secret_attachment(secret.uuid, index)

    def update_property(self, secret: Secret, key: str, value: str):  # TODO
        pass

    def get_groups(self) -> list:
        return self.client.groups

    def get_group_secrets(self, group: str) -> list:
        secrets = self.client.secret_group_name(group)
        return [Secret(x, client=self) for x in secrets]

    def search(self, needle: str) -> list:
        return [Secret(x, client=self) for x in self.client.search(needle)]

