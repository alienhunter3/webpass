# REST API

All API blueprints are registered under the `/api` prefix (optionally preceded by `APP_PATH`, for example `/password/api`).

## Authentication

Most endpoints require **HTTP Basic** authentication. The password is the KeePass database master password; the username is ignored.

`/api/file` also accepts the master password in a form field named `password` (used for multipart uploads).

Unauthorized or invalid credentials return `401`. Missing credentials use `{"msg": "login with http basic auth"}`. A wrong master password uses `{"msg": "login invalid"}`. Both are 401 so an access log can match them (for example with fail2ban).

With `REQUIRE_HTTPS` left at its default, a request that did not arrive over HTTPS gets `403` `{"msg": "HTTPS is required"}` and the database is not opened.

The server opens the database with the password for that request and then drops it. It does not put the password in a session, cookie, or cache. API responses send `Cache-Control: no-store`.

`GET /api/group/tree` returns every group and entry summary (uuid, title, username, group) and omits passwords, notes, URLs, and custom properties. The web UI loads this once after login. `GET /api/secret/<uuid>` still returns the secret values for one entry.

## Resources

| Prefix | Blueprint | Description |
|--------|-----------|-------------|
| `/api/secret` | `api_secret` | List, search, create, update secrets and attachments |
| `/api/group` | `api_group` | List groups, one group tree without secret values, and secrets in a group |
| `/api/file` | `api_datafile` | Download/upload the `.kdbx` database and metadata |

Query flags used by several list endpoints:

- `fetch_all=true` — return full entry details (including password) instead of a short summary
- `POST /api/secret/search` with JSON `{"search": "<term>", "fetch_all": false}` — filter by title, username, notes, or attachment name. The term is not a query parameter.
- `GET /api/secret?search=<term>` — deprecated. Same filter, and the term is in the URL. The response carries a `Warning` header.

See the [endpoint reference](reference.md) for per-route documentation generated from the source.
