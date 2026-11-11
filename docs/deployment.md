# Deployment

Recommended production setup with a virtualenv, uWSGI, nginx, and systemd. uWSGI is what serves the app behind nginx. It is a separate program from the `pywebpass` package.

`pip install pywebpass` and `requirements.txt` do not install uWSGI. uWSGI publishes no wheels, so pip compiles it from source. On Debian, install the compilers first:

```bash
sudo apt install build-essential python3-dev
```

Then, with the virtualenv's own interpreter (not system `pip`):

```bash
/path/to/venv/bin/python -m pip install uwsgi
ls /path/to/venv/bin/uwsgi
```

`ls` must print that path. The example unit runs `<venv>/bin/uwsgi --ini webpass.ini`. If the binary is missing, systemd cannot start the service.

## Do not rebuild the venv with `--clear`

`python3 -m venv --clear <dir>` deletes everything already in that directory and creates a new empty virtualenv. That includes:

- the hand-installed `bin/uwsgi`
- `wsgi.py` and `webpass.ini`, which live in the venv root next to each other
- `<venv>/var/pywebpass-instance/` (`passwords.kdbx` and `config.py`)

Copy those out before a rebuild, or keep `wsgi.py`, `webpass.ini`, and the instance folder outside the venv directory. Recreating the venv with `--clear` and then installing only `pywebpass` leaves no `uwsgi` binary. That is enough to take the site down. After any rebuild, install uWSGI again and confirm `ls <venv>/bin/uwsgi` before starting the unit.

The instance folder is also not part of the package. `create_app()` exits if `passwords.kdbx` is missing or not readable. Copy `<venv>/var/pywebpass-instance/` aside even for an upgrade that does not use `--clear`, then copy it back. The example uWSGI config sets `need-app = true`, so uWSGI exits when the app fails to load instead of staying up with no application.

## Install

1. Use [`webpass.service.example`](examples/webpass.service.example) as a guide for where the Python virtualenv should live.

2. Install `build-essential` and `python3-dev` (see above). Create a new Python virtualenv in that location (matching the service file) with appropriate permissions. You may want a dedicated user added to the web server group (`www-data` or equivalent). Do not point `python3 -m venv --clear` at a directory that already holds this deployment.

3. Clone this repository somewhere on the host.

4. Activate the virtualenv:

```bash
source /path/to/venv/bin/activate
```

5. Install the package. This does not install uWSGI:

```bash
pip install /path/to/cloned/repo
```

6. Install uWSGI into the same virtualenv and confirm the binary:

```bash
/path/to/venv/bin/python -m pip install uwsgi
ls /path/to/venv/bin/uwsgi
```

7. Create `webpass.ini` from [`webpass.ini.example`](examples/webpass.ini.example) and place it in the virtualenv root. The example sets `module = wsgi:app` and `need-app = true`. Keep `need-app = true` so uWSGI exits when the app fails to load.

8. Place `wsgi.py` in that same directory (the venv root, next to `webpass.ini`). uWSGI loads `module = wsgi:app` from the process working directory, which the example unit sets to the venv root. The factory is `create_app` in the `pywebpass` package:

```python
from pywebpass import create_app

app = create_app()
```

That is the same file shipped as `wsgi.py` in this repository.

9. Create a `webpass.service` from [`webpass.service.example`](examples/webpass.service.example). `ExecStart` must be `<venv>/bin/uwsgi --ini webpass.ini`. Adjust paths, user/groups, and set `APP_PATH` to the URL path prefix for the app on the host.

10. Copy the unit file to `/etc/systemd/system` and run `systemctl daemon-reload`.

11. Start the service once so it creates the instance folder, then stop it. With no database the process exits during startup.

12. The instance folder for a virtualenv install is `<venv>/var/pywebpass-instance/` (Flask's `<prefix>/var/<app name>-instance`). A checkout that is not installed into `site-packages` uses `<repo>/instance/` instead. This directory is inside the venv, so `python3 -m venv --clear` deletes it.

13. Put `passwords.kdbx` and `config.py` in that folder. See [Examples](examples/index.md). `passwords.kdbx` has to exist and be readable or startup raises `FileNotFoundError` / `PermissionError` and includes the path it checked. `config.py` holds logging settings and any other overrides. Local development can omit most of `config.py` and use the built-in defaults, but HTTP `flask run` needs `REQUIRE_HTTPS = False`. pip does not recreate this folder. Copy it out and back when rebuilding the venv, as described above.

14. Reverse proxy with nginx. `REQUIRE_HTTPS` defaults to true, so the app returns `403` until nginx tells uWSGI the real scheme. `include uwsgi_params;` on current Debian already sends `HTTPS` and `REQUEST_SCHEME`. Repeat them in the location so a trimmed params file still works. `$https` and `$scheme` come from nginx's connection, not from the browser. `request.is_secure` alone is not enough, because uWSGI copies a client `X-Forwarded-Proto` into `wsgi.url_scheme` before it looks at `HTTPS`. Overwrite that header with nginx's scheme:

```nginx
location /password {
    include uwsgi_params;
    # Repeat these so a trimmed uwsgi_params file still tells the app the
    # real scheme. $https and $scheme come from nginx's connection, not from
    # the browser. HTTPS=on / REQUEST_SCHEME=https is what Flask sees in the
    # WSGI environ; request.is_secure alone is not enough, because uWSGI
    # copies a client X-Forwarded-Proto into wsgi.url_scheme first.
    uwsgi_param HTTPS $https if_not_empty;
    uwsgi_param REQUEST_SCHEME $scheme;
    # Overwrite any client X-Forwarded-Proto. Do not pass the browser's value.
    uwsgi_param HTTP_X_FORWARDED_PROTO $scheme;
    uwsgi_pass unix:/srv/http/webpass-venv/webpass.sock;
}
```

Terminate TLS on this virtual host. The app refuses every request (`403`, `{"msg": "HTTPS is required"}`) unless `REQUEST_SCHEME` or `HTTPS` says the connection is TLS, and it does that before opening the KeePass file. `REQUIRE_HTTPS` defaults to true. Do not publish the uWSGI HTTP socket, and if you use `http-socket` bind it to `127.0.0.1` only. Leave Flask's debugger off (`flask run` without `--debug`).

Failed logins are HTTP 401 (`login with http basic auth` when the password was not sent, `login invalid` when it was wrong), which is what fail2ban matches in the nginx access log. A missing TLS connection is 403, not 401.

The web UI clears its in-memory password after `UI_IDLE_TIMEOUT` seconds of inactivity (default 900) or `UI_ABSOLUTE_TIMEOUT` seconds after login (default 28800). Set those in the instance `config.py` to override. Use `LOG_LEVEL = logging.INFO` or `logging.WARNING` there. If an existing config still sets `logging.DEBUG`, change it; the example used to recommend DEBUG.

With Apache, unix sockets may not work; configure uWSGI with a TCP listener instead and adjust `webpass.ini` accordingly. See the [uWSGI configuration docs](https://uwsgi-docs.readthedocs.io/en/latest/Configuration.html).

15. Create a static directory in the webroot for that virtual host and copy the `js` and `css` folders from the `pywebpass` package `static` directory into it.

16. Reload/restart nginx (or Apache) and restart `webpass.service`. Confirm `<venv>/bin/uwsgi` still exists first if the venv was recreated.
