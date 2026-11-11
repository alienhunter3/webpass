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
# instance/config.py must set REQUIRE_HTTPS = False for this HTTP server
flask --app pywebpass run
```

Startup exits if `passwords.kdbx` is missing or not readable. `REQUIRE_HTTPS` defaults to true, so local HTTP needs that one line in `config.py`. Production keeps the instance folder (`passwords.kdbx` and `config.py`) and must copy it when rebuilding the venv. uWSGI should set `need-app = true` so a failed app load stops the process. The nginx `location` must pass `REQUEST_SCHEME` and `HTTPS` from `uwsgi_params`.

See [docs/getting-started.md](docs/getting-started.md) and [docs/deployment.md](docs/deployment.md).

## Documentation

Build and preview the MkDocs site (client + REST API reference via mkdocstrings):

```bash
pip install -r requirements-docs.txt
pip install -e .
mkdocs serve
```

Then open the URL printed by MkDocs (typically http://127.0.0.1:8000).
