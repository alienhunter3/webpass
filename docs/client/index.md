# Client library

The Python client talks to either the remote REST API or a local KeePass file through a shared facade.

## Backends

| Backend | Class | Use case |
|---------|-------|----------|
| REST API | `ApiClient` | Live server; supports create/update/attachments |
| KeePass file | `KeepassClient` | Direct `.kdbx` access; read-oriented |
| Facade | `ClientProxy` | Unified API over either backend |

Construct a proxy with:

```python
from pywebpass.client.client import ClientProxy

# Remote API (password is the KeePass master password via HTTP Basic)
client = ClientProxy.api_proxy("https://example.com/password/api", password="secret")

# Local database file
client = ClientProxy.keepass_proxy("/path/to/passwords.kdbx", password="secret")
```

Mutating operations (`create_secret`, `update_secret_fields`, `add_attachment`, `delete_attachment`) require the API backend; a local KeePass proxy raises `RuntimeError` for those calls.

## Domain types

- `Secret` — entry with title, credentials, notes, path, attachments, and custom properties
- `Attachment` — file attached to a secret
- `AccessDeniedError` — raised when access is denied
- `Backend` — enum of supported backends

Password generation lives in `pywebpass.client.password.generate_password`. CLI config and cache helpers are in `pywebpass.client.config`.

See the [full reference](reference.md) for generated API docs.
