# Getting started

Run pywebpass locally for development (for example from PyCharm or with a virtualenv activated).

1. Create an `instance` folder inside the repository root.

2. Optionally create `instance/config.py`. See [Examples](examples/index.md) for a template.

3. Create a KeePass database named `passwords.kdbx` in the instance folder and add some entries for testing. Startup fails if this file is missing or not readable.

4. Start the Flask development server:

```bash
flask --app pywebpass run
```

Do not pass `--debug` when the port is reachable by anyone else. The debugger can display the master password from the request. The UI keeps that password in tab memory and clears it after 15 minutes idle or 8 hours, unless `UI_IDLE_TIMEOUT` and `UI_ABSOLUTE_TIMEOUT` (seconds) are set in `instance/config.py`.

The UI is available at the app root. REST endpoints live under `/api` (or under `APP_PATH` + `/api` if that environment variable is set).
