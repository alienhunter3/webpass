# Getting started

Run pywebpass locally for development (for example from PyCharm or with a virtualenv activated).

1. Create an `instance` folder inside the repository root.

2. Optionally create `instance/config.py`. See [Examples](examples/index.md) for a template.

3. Create a KeePass database named `passwords.kdbx` in the instance folder and add some entries for testing.

4. Start the Flask development server:

```bash
flask --app pywebpass run --debug
```

The UI is available at the app root. REST endpoints live under `/api` (or under `APP_PATH` + `/api` if that environment variable is set).
