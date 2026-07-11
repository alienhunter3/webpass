# pywebpass

Self-hosted password management backed by a KeePass (`.kdbx`) database. The package provides:

- A Flask web app with a REST API and browser UI
- A Python client library (`ClientProxy`, `ApiClient`, `KeepassClient`)
- A `webpass-client` CLI for search, password generation, and CRUD

## Documentation

- [Getting started](getting-started.md) — local development
- [Deployment](deployment.md) — production with uWSGI and systemd
- [Client library](client/index.md) — Python API overview and [reference](client/reference.md)
- [REST API](api/index.md) — auth, conventions, and [endpoint reference](api/reference.md)
- [Examples](examples/index.md) — instance config, uWSGI, and systemd unit

## Build these docs

```bash
pip install -r requirements-docs.txt
pip install -e .
mkdocs serve
```
