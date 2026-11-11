# Deployment

Recommended production setup with a virtualenv, uWSGI, and systemd.

The instance folder holds `passwords.kdbx` and `config.py`. Copy `<venv>/var/pywebpass-instance/` aside before rebuilding the virtualenv, then copy it back. `create_app()` exits if the configured database is missing or not readable. The example uWSGI config sets `need-app = true`, so uWSGI exits when the app fails to load.

1. Use [`webpass.service.example`](examples/webpass.service.example) as a guide for where the Python virtualenv should live.

2. Create a new Python virtualenv in that location (matching the service file) with appropriate permissions.
   You may want a dedicated user added to the web server group (`www-data` or equivalent).

3. Clone this repository somewhere on the host.

4. Activate the virtualenv:

```bash
source /path/to/venv/bin/activate
```

5. Install the package:

```bash
pip install /path/to/cloned/repo
```

6. Create `webpass.ini` from [`webpass.ini.example`](examples/webpass.ini.example) and place it in the virtualenv root. Keep `need-app = true` so uWSGI exits when the app fails to load.

7. Place `wsgi.py` in the virtualenv root.

8. Create a `webpass.service` from [`webpass.service.example`](examples/webpass.service.example). Adjust paths, user/groups, and set `APP_PATH` to the URL path prefix for the app on the host.

9. Copy the unit file to `/etc/systemd/system` and run `systemctl daemon-reload`.

10. Start the service once so it creates the instance folder, then stop it. With no database the process exits during startup.

11. The instance folder for a virtualenv install is `<venv>/var/pywebpass-instance/` (Flask's `<prefix>/var/<app name>-instance`). A checkout that is not installed into `site-packages` uses `<repo>/instance/` instead.

12. Put `passwords.kdbx` and `config.py` in that folder. See [Examples](examples/index.md). `passwords.kdbx` has to exist and be readable or startup raises `FileNotFoundError` / `PermissionError` and includes the path it checked. `config.py` holds logging settings and any other overrides. Local development can omit `config.py` and use the built-in defaults. pip leaves this directory alone only while the virtualenv itself is kept; rebuilding the venv removes it, so copy the folder out and back as described above.

13. Reverse proxy with nginx, for example:

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

14. Create a static directory in the webroot for that virtual host and copy the `js` and `css` folders from the `pywebpass` package `static` directory into it.

15. Reload/restart nginx (or Apache) and restart `webpass.service`.
