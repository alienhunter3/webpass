from pywebpass import keepass
import requests
from typing import Union
from uuid import UUID
from urllib.parse import quote_plus
from io import BytesIO


class ApiClient:
    def __init__(self, base_url: str, password: str, ssl_verify: bool = True):
        self.base_url = base_url
        self.password = password
        self.creds = ('', password)
        self.ssl_verify = ssl_verify
        if self.base_url[-1] == '/':
            self.base_url = self.base_url[:-1]

    @property
    def group_url(self):
        return self.base_url + "/group"

    @property
    def secret_url(self):
        return self.base_url + "/secret"

    @property
    def groups(self):
        r = requests.get(self.group_url, auth=self.creds, verify=self.ssl_verify)
        if r.status_code != 200:
            raise requests.HTTPError(f"Request to {self.group_url} returned {r.status_code}")
        return r.json()['data']

    @property
    def all_secrets(self):
        r = requests.get(self.secret_url, params={'fetch_all': "true"}, auth=self.creds, verify=self.ssl_verify)
        if r.status_code != 200:
            raise requests.HTTPError(f"Request to {self.group_url} returned {r.status_code}")
        return r.json()['data']

    def authenticate(self):
        throw_away = self.groups

    def search(self, needle: str):
        r = requests.get(self.secret_url, params={'fetch_all': "true", "search": needle}, auth=self.creds, verify=self.ssl_verify)
        if r.status_code != 200:
            raise requests.HTTPError(f"Request to {self.group_url} returned {r.status_code}")
        return r.json()['data']

    def secret_uuid(self, uuid: Union[str, UUID]):
        uuid = quote_plus(str(uuid))
        r = requests.get(self.secret_url + "/" + uuid, params={'fetch_all': "true"}, auth=self.creds, verify=self.ssl_verify)
        if r.status_code == 404:
            raise KeyError("Couldn't find secret with provided UUID")
        elif r.status_code == 200:
            pass
        else:
            raise requests.HTTPError(f"Request to {self.group_url} returned {r.status_code}")
        return r.json()['data']

    def secret_group_name(self, group_name: str):
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
        uuid = quote_plus(str(uuid))
        url = f"{self.secret_url}/{uuid}/attachment/{int(index)}"
        r = requests.get(url, auth=self.creds, verify=self.ssl_verify)
        if r.status_code == 404:
            raise KeyError("Couldn't find secret with provided UUID")
        elif r.status_code == 200:
            return BytesIO(r.content)
        else:
            raise requests.HTTPError(f"Request to {self.group_url} returned {r.status_code}")


