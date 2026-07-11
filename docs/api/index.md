# REST API

All API blueprints are registered under the `/api` prefix (optionally preceded by `APP_PATH`, for example `/password/api`).

## Authentication

Most endpoints require **HTTP Basic** authentication. The password is the KeePass database master password; the username is ignored.

`/api/file` also accepts the master password in a form field named `password` (used for multipart uploads).

Unauthorized or invalid credentials return `401` with a JSON body like `{"msg": "login invalid"}`.

## Resources

| Prefix | Blueprint | Description |
|--------|-----------|-------------|
| `/api/secret` | `api_secret` | List, search, create, update secrets and attachments |
| `/api/group` | `api_group` | List groups and their secrets |
| `/api/file` | `api_datafile` | Download/upload the `.kdbx` database and metadata |

Query flags used by several list endpoints:

- `fetch_all=true` — return full entry details (including password) instead of a short summary
- `search=<term>` — filter secrets by title, username, notes, or attachment name (secret list only)

See the [endpoint reference](reference.md) for per-route documentation generated from the source.
