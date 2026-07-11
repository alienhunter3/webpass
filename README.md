# pywebpass

Self-hosted KeePass password manager with a Flask REST API, web UI, and `webpass-client` CLI.

## Install

```bash
pip install .
# or editable:
pip install -e .
```

## Run locally

```bash
mkdir -p instance
# add instance/config.py and instance/passwords.kdbx
flask --app pywebpass run --debug
```

See [docs/getting-started.md](docs/getting-started.md) and [docs/deployment.md](docs/deployment.md).

## Documentation

Build and preview the MkDocs site (client + REST API reference via mkdocstrings):

```bash
pip install -r requirements-docs.txt
pip install -e .
mkdocs serve
```

Then open the URL printed by MkDocs (typically http://127.0.0.1:8000).
