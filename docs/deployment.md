# Deployment

Recommended production setup with a virtualenv, uWSGI, and systemd.

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

6. Create `webpass.ini` from [`webpass.ini.example`](examples/webpass.ini.example) and place it in the virtualenv root.

7. Place `wsgi.py` in the virtualenv root.

8. Create a `webpass.service` from [`webpass.service.example`](examples/webpass.service.example). Adjust paths, user/groups, and set `APP_PATH` to the URL path prefix for the app on the host.

9. Copy the unit file to `/etc/systemd/system` and run `systemctl daemon-reload`.

10. Start the service once so it creates the instance folder. It will likely crash without a database; stop it afterward.

11. Find the instance folder under the virtualenv (typically under a `var` path for the package).

12. Put a `config.py` and your `passwords.kdbx` file in that instance folder. See [Examples](examples/index.md).

13. Reverse proxy with nginx, for example:

```nginx
location /password {
    include uwsgi_params;
    uwsgi_pass unix:/srv/http/webpass-venv/webpass.sock;
}
```

With Apache, unix sockets may not work; configure uWSGI with a TCP listener instead and adjust `webpass.ini` accordingly. See the [uWSGI configuration docs](https://uwsgi-docs.readthedocs.io/en/latest/Configuration.html).

14. Create a static directory in the webroot for that virtual host and copy the `js` and `css` folders from the `pywebpass` package `static` directory into it.

15. Reload/restart nginx (or Apache) and restart `webpass.service`.
