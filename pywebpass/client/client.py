"""Unified client facade and domain models for secrets and attachments."""

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
import json

same_fields = ["url", "notes", "username", "password", "uuid"]


class AccessDeniedError(Exception):
    """Raised when the client is denied access to a resource."""


@dataclass
class Attachment:
    """A file attached to a :class:`Secret`.

    Attributes:
        index: Attachment id within the parent secret.
        file_name: Original file name.
        parent: Secret that owns this attachment.
    """

    index: int
    file_name: str
    parent: Secret

    def get_file(self):
        """Download this attachment's binary content via the parent client."""
        return self.parent.get_file(self.index)

    def delete(self):
        """Delete this attachment via the parent client (API backend only)."""
        if self.parent is None or self.parent._parent is None:
            raise RuntimeError("Parent doesn't exist. Cannot delete attached files.")
        self.parent._parent.delete_attachment(self.parent.uuid, self.index)

    def short_string(self):
        """Return a short display label like ``[0]filename.txt``."""
        return f"[{self.index}]{self.file_name}"


class Secret:
    """A KeePass entry exposed as a mutable Python object.

    Field setters track changes; call :meth:`update` to push them through the
    parent :class:`ClientProxy` when a backend supports it.
    """

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
        """Build a :class:`Secret` from a pykeepass entry object."""
        return Secret(entry_to_dict(secret))

    @property
    def dict(self) -> dict:
        """Return a dict of core fields, attachments, and custom properties."""
        output = {}
        for key in ("username", "password", "notes", "path", "url", "title", "uuid"):
            output[key] = self.__getattribute__(key)
        output['files'] = self.files
        output['custom_properties'] = self.custom_properties
        return output

    @property
    def json(self) -> str:
        """Serialize this secret to a JSON string (UUID and files normalized)."""
        d = self.dict
        d['uuid'] = str(d['uuid'])
        atts = []
        for i in d['files']:
            atts.append({'index': i.index, 'file_name': i.file_name})
        d['files'] = atts
        return json.dumps(d)

    @property
    def changed(self) -> bool:
        """Whether any tracked fields have been modified since load or last update."""
        if len(self._changed) > 0:
            return True
        else:
            return False

    @property
    def changes(self) -> list:
        """Names of fields marked dirty since load or last update."""
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
        """Update a custom property on the backend via the parent client."""
        self._parent.update_property(self, key, value)

    def update(self):
        """Persist dirty fields through the parent client, then clear the change set."""
        if not self.changed:
            return

        if self._parent is not None:
            self._parent.update_secret(self)

        self._changed = set()

    def get_file(self, file_index: int) -> IO:
        """Fetch an attachment by index through the parent client."""
        if self._parent is None:
            raise RuntimeError("Parent doesn't exist. Cannot retrieve attached files.")
        return self._parent.get_file_index(self, file_index)

    def add_file(self, new_file: Union[str, IO]):  # TODO
        """Add an attachment (not yet implemented)."""
        pass

    def json_fields(self, fields: list) -> str:
        """Serialize selected fields from :attr:`dict` to a JSON string."""
        temp = {}
        d = self.dict
        for field in fields:
            temp[field] = d[field]
            if field == "uuid":
                temp['uuid'] = str(temp['uuid'])
        return json.dumps(temp)


class Backend(Enum):
    """Supported client backends."""

    API = 1
    KEEPASS_FILE = 2
    DUMMY = 3


class ClientProxy:
    """Facade over :class:`ApiClient` or :class:`KeepassClient`.

    Prefer the factory methods :meth:`api_proxy` and :meth:`keepass_proxy`.
    Create/update/attachment helpers require the API backend.
    """

    def __init__(self, client: Union[ApiClient, KeepassClient]):
        self.client = client

    @staticmethod
    def api_proxy(base_url: str, password: str) -> ClientProxy:
        """Create a proxy backed by the remote REST API.

        Args:
            base_url: API base URL including the ``/api`` prefix.
            password: KeePass master password (HTTP Basic password).
        """
        return ClientProxy(ApiClient(base_url, password))

    @staticmethod
    def keepass_proxy(db_file: Union[str, IO], password: str) -> ClientProxy:
        """Create a proxy backed by a local ``.kdbx`` file.

        Args:
            db_file: Path or file-like object for the database.
            password: KeePass master password.
        """
        return ClientProxy(KeepassClient(db_file, password))

    def get_secret_uuid(self, uuid: Union[UUID, int, bytes, str]) -> Secret:
        """Load a single secret by UUID."""
        secret_raw = self.client.secret_uuid(resolve_uuid(uuid))
        return Secret(secret_raw, client=self)

    def get_all_secrets(self) -> list:
        """Return all secrets as :class:`Secret` instances."""
        secrets = self.client.all_secrets
        return [Secret(x, client=self) for x in secrets]

    def update_secret(self, secret: Secret):  # TODO
        """Push a dirty :class:`Secret` to the backend (not yet implemented)."""
        pass

    def get_file_index(self, secret: Secret, index: int) -> IO:
        """Download attachment ``index`` from ``secret``."""
        return self.client.secret_attachment(secret.uuid, index)

    def update_property(self, secret: Secret, key: str, value: str):  # TODO
        """Update a custom property on ``secret`` (not yet implemented)."""
        pass

    def get_groups(self) -> list:
        """Return group summaries (``uuid``, ``name``)."""
        return self.client.groups

    def get_group_secrets(self, group: str) -> list:
        """Return secrets in the group matching ``group`` by name (case-insensitive)."""
        secrets = self.client.secret_group_name(group)
        return [Secret(x, client=self) for x in secrets]

    def search(self, needle: str) -> list:
        """Search secrets and return matching :class:`Secret` instances."""
        return [Secret(x, client=self) for x in self.client.search(needle)]

    def create_secret(
        self,
        title: str,
        username: str = "",
        password: str = "",
        url: str = "",
        notes: str = "",
        group: str = "",
        extra: Union[dict, None] = None,
    ) -> str:
        """Create a secret via the API backend.

        Returns:
            New secret UUID string.

        Raises:
            RuntimeError: If the backend is not :class:`ApiClient`.
        """
        if not isinstance(self.client, ApiClient):
            raise RuntimeError("Creating secrets requires the API backend; local KeePass cache is read-only.")
        return self.client.post_secret(
            title=title,
            username=username,
            password=password,
            url=url,
            notes=notes,
            group=group,
            extra=extra,
        )

    def update_secret_fields(
        self,
        uuid: Union[UUID, int, bytes, str],
        *,
        title: Union[str, None] = None,
        username: Union[str, None] = None,
        password: Union[str, None] = None,
        url: Union[str, None] = None,
        notes: Union[str, None] = None,
        extra: Union[dict, None] = None,
    ) -> str:
        """Update fields on an existing secret via the API backend.

        Only non-``None`` keyword arguments are sent.

        Returns:
            Secret UUID string.

        Raises:
            RuntimeError: If the backend is not :class:`ApiClient`.
        """
        if not isinstance(self.client, ApiClient):
            raise RuntimeError("Updating secrets requires the API backend; local KeePass cache is read-only.")
        return self.client.update_secret(
            resolve_uuid(uuid),
            title=title,
            username=username,
            password=password,
            url=url,
            notes=notes,
            extra=extra,
        )

    def add_attachment(
        self,
        uuid: Union[UUID, int, bytes, str],
        file_object: IO,
        file_name: str,
    ) -> None:
        """Upload a file attachment to a secret via the API backend.

        Raises:
            RuntimeError: If the backend is not :class:`ApiClient`.
        """
        if not isinstance(self.client, ApiClient):
            raise RuntimeError("Adding attachments requires the API backend; local KeePass cache is read-only.")
        self.client.post_secret_attachment(resolve_uuid(uuid), file_object, file_name)

    def delete_attachment(
        self,
        uuid: Union[UUID, int, bytes, str],
        index: int,
    ) -> None:
        """Delete an attachment from a secret via the API backend.

        Raises:
            RuntimeError: If the backend is not :class:`ApiClient`.
        """
        if not isinstance(self.client, ApiClient):
            raise RuntimeError("Deleting attachments requires the API backend; local KeePass cache is read-only.")
        self.client.delete_secret_attachment(resolve_uuid(uuid), index)

