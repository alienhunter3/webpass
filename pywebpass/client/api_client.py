"""HTTP client for the pywebpass REST API."""

import typing

import requests
from typing import Union
from uuid import UUID
from urllib.parse import quote_plus
from io import BytesIO


class ApiClient:
    """Low-level REST client using HTTP Basic auth (KeePass master password).

    Args:
        base_url: API base URL including the ``/api`` prefix (trailing slash stripped).
        password: KeePass master password.
        ssl_verify: Whether to verify TLS certificates.
    """

    def __init__(self, base_url: str, password: str, ssl_verify: bool = True):
        self.base_url = base_url
        self.password = password
        self.creds = ('', password)
        self.ssl_verify = ssl_verify
        if self.base_url[-1] == '/':
            self.base_url = self.base_url[:-1]

    @property
    def group_url(self) -> str:
        """URL for the ``/group`` resource."""
        return self.base_url + "/group"

    @property
    def secret_url(self) -> str:
        """URL for the ``/secret`` resource."""
        return self.base_url + "/secret"

    @property
    def groups(self) -> list:
        """List all groups (``GET /group``)."""
        r = requests.get(self.group_url, auth=self.creds, verify=self.ssl_verify)
        if r.status_code != 200:
            raise requests.HTTPError(f"Request to {self.group_url} returned {r.status_code}")
        return r.json()['data']

    @property
    def all_secrets(self) -> list:
        """List all secrets with full details (``GET /secret?fetch_all=true``)."""
        r = requests.get(self.secret_url, params={'fetch_all': "true"}, auth=self.creds, verify=self.ssl_verify)
        if r.status_code != 200:
            raise requests.HTTPError(f"Request to {self.group_url} returned {r.status_code}")
        return r.json()['data']

    def authenticate(self):
        """Validate credentials by fetching the group list."""
        throw_away = self.groups

    def search(self, needle: str) -> list:
        """Search secrets (``GET /secret?fetch_all=true&search=...``)."""
        r = requests.get(self.secret_url, params={'fetch_all': "true", "search": needle}, auth=self.creds, verify=self.ssl_verify)
        if r.status_code != 200:
            raise requests.HTTPError(f"Request to {self.group_url} returned {r.status_code}")
        return r.json()['data']

    def secret_uuid(self, uuid: Union[str, UUID]) -> dict:
        """Fetch one secret by UUID (``GET /secret/<uuid>``)."""
        uuid = quote_plus(str(uuid))
        r = requests.get(self.secret_url + "/" + uuid, params={'fetch_all': "true"}, auth=self.creds, verify=self.ssl_verify)
        if r.status_code == 404:
            raise KeyError("Couldn't find secret with provided UUID")
        elif r.status_code == 200:
            pass
        else:
            raise requests.HTTPError(f"Request to {self.group_url} returned {r.status_code}")
        return r.json()['data']

    def secret_group_name(self, group_name: str) -> list:
        """Return full details for secrets in the named group (case-insensitive)."""
        group_name = group_name.strip().lower()
        groups = self.groups
        secrets = []
        for group in groups:
            if group_name == group['name'].strip().lower():
                r = requests.get(f"{self.group_url}/{group['uuid']}/secrets", params={'fetch_all': "true"},
                                 auth=self.creds, verify=self.ssl_verify)
                for secret in r.json()['data']:
                    secrets.append(secret)
        return secrets

    def secret_attachment(self, uuid: Union[str, UUID], index: int) -> BytesIO:
        """Download an attachment (``GET /secret/<uuid>/attachment/<index>``)."""
        uuid = quote_plus(str(uuid))
        url = f"{self.secret_url}/{uuid}/attachment/{int(index)}"
        r = requests.get(url, auth=self.creds, verify=self.ssl_verify)
        if r.status_code == 404:
            raise KeyError("Couldn't find secret with provided UUID")
        elif r.status_code == 200:
            return BytesIO(r.content)
        else:
            raise requests.HTTPError(f"Request to {self.group_url} returned {r.status_code}")

    def post_secret_attachment(self, uuid: Union[str, UUID], file_object: typing.BinaryIO, file_name: str):
        """Upload an attachment (``POST /secret/<uuid>/attachment``)."""
        uuid = quote_plus(str(uuid))
        url = f"{self.secret_url}/{uuid}/attachment"

        files = {'attachment': (file_name, file_object)}

        r = requests.post(url, auth=self.creds, files=files, verify=self.ssl_verify)
        if r.status_code == 404:
            raise KeyError("Couldn't find secret with provided UUID")
        elif r.status_code != 201:
            raise requests.HTTPError(f"Request to {self.group_url} returned {r.status_code}:\n{r.text}")

    def delete_secret_attachment(self, uuid: Union[str, UUID], index: int):
        """Delete an attachment (``DELETE /secret/<uuid>/attachment/<index>``)."""
        uuid = quote_plus(str(uuid))
        url = f"{self.secret_url}/{uuid}/attachment/{int(index)}"
        r = requests.delete(url, auth=self.creds, verify=self.ssl_verify)
        if r.status_code == 404:
            try:
                msg = r.json().get("msg", r.text)
            except Exception:
                msg = r.text
            raise KeyError(msg)
        elif r.status_code != 200:
            raise requests.HTTPError(f"Request to {url} returned {r.status_code}:\n{r.text}")

    def post_secret(
        self,
        title: str,
        username: str = "",
        password: str = "",
        url: str = "",
        notes: str = "",
        group: str = "",
        extra: Union[dict, None] = None,
    ) -> str:
        """Create a new secret via ``POST /secret``.

        Returns:
            New secret UUID string.
        """
        payload = {
            "title": title,
            "username": username,
            "password": password,
            "url": url,
            "notes": notes,
            "group": group,
        }
        if extra:
            payload["extra"] = extra

        r = requests.post(
            self.secret_url,
            json=payload,
            auth=self.creds,
            verify=self.ssl_verify,
        )
        if r.status_code == 401:
            raise requests.HTTPError(f"Authentication failed for {self.secret_url}")
        if r.status_code == 400:
            try:
                msg = r.json().get("msg", r.text)
            except Exception:
                msg = r.text
            raise ValueError(msg)
        if r.status_code != 201:
            raise requests.HTTPError(
                f"Request to {self.secret_url} returned {r.status_code}:\n{r.text}"
            )
        return r.json()["secret"]

    def update_secret(
        self,
        uuid: Union[str, UUID],
        *,
        title: Union[str, None] = None,
        username: Union[str, None] = None,
        password: Union[str, None] = None,
        url: Union[str, None] = None,
        notes: Union[str, None] = None,
        extra: Union[dict, None] = None,
    ) -> str:
        """Update fields on an existing secret via ``PUT /secret/<uuid>``.

        Returns:
            Secret UUID string.
        """
        payload = {}
        if title is not None:
            payload["title"] = title
        if username is not None:
            payload["username"] = username
        if password is not None:
            payload["password"] = password
        if url is not None:
            payload["url"] = url
        if notes is not None:
            payload["notes"] = notes
        if extra:
            payload["extra"] = extra

        if not payload:
            raise ValueError("at least one field must be provided to update")

        uuid_str = quote_plus(str(uuid))
        endpoint = f"{self.secret_url}/{uuid_str}"
        r = requests.put(
            endpoint,
            json=payload,
            auth=self.creds,
            verify=self.ssl_verify,
        )
        if r.status_code == 401:
            raise requests.HTTPError(f"Authentication failed for {endpoint}")
        if r.status_code == 404:
            raise KeyError("Couldn't find secret with provided UUID")
        if r.status_code == 400:
            try:
                msg = r.json().get("msg", r.text)
            except Exception:
                msg = r.text
            raise ValueError(msg)
        if r.status_code != 200:
            raise requests.HTTPError(
                f"Request to {endpoint} returned {r.status_code}:\n{r.text}"
            )
        return r.json()["secret"]
