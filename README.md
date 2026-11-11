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
# required: instance/passwords.kdbx
# optional: instance/config.py
flask --app pywebpass run --debug
```

Startup exits if `passwords.kdbx` is missing or not readable. `config.py` is optional for a local run. Production keeps both files in the virtualenv instance folder and must copy that folder when rebuilding the venv. uWSGI should set `need-app = true` so a failed app load stops the process.

See [docs/getting-started.md](docs/getting-started.md) and [docs/deployment.md](docs/deployment.md).

## Documentation

Build and preview the MkDocs site (client + REST API reference via mkdocstrings):

```bash
pip install -r requirements-docs.txt
pip install -e .
mkdocs serve
```

Then open the URL printed by MkDocs (typically http://127.0.0.1:8000).
