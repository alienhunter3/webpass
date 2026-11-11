"""Keep master passwords and decrypted API responses out of caches.

The password is taken from the current request and used to open the database
for that request only. It is not written to a session, a cookie, or a log.
"""

from flask import current_app, g, make_response, request

# nginx's uwsgi_params set these from $https / $scheme. They are uwsgi
# protocol variables, not client headers.
_HTTPS_FLAGS = {'on', '1', 'true'}


def request_master_password():
    """Return the master password supplied with this request, or ``None``.

    Multipart uploads may send it in the ``password`` form field. Other
    requests send it as the HTTP Basic password. The username is ignored.
    """
    if request.form and 'password' in request.form:
        return request.form['password']
    auth = request.authorization
    if auth is None or auth.password is None:
        return None
    return auth.password


def request_is_trusted_https():
    """Return whether this request arrived on HTTPS, without trusting the client.

    nginx's ``uwsgi_params`` sends ``REQUEST_SCHEME=$scheme`` and
    ``HTTPS=$https``. uWSGI copies those into the WSGI environ under those
    names. A browser cannot set them. ``$scheme`` / ``$https`` describe the
    connection nginx accepted.

    ``request.is_secure`` is only a fallback. uWSGI prefers a client
    ``X-Forwarded-Proto`` header over ``HTTPS`` when it fills
    ``wsgi.url_scheme``, so that property alone can be spoofed on plain HTTP.
    When ``REQUEST_SCHEME`` is present it wins, including over
    ``X-Forwarded-Proto``. The header is not read here. Trust it only by
    having nginx overwrite it (``uwsgi_param HTTP_X_FORWARDED_PROTO $scheme``),
    which makes ``REQUEST_SCHEME`` and the header the same value.
    """
    scheme = str(request.environ.get('REQUEST_SCHEME') or '').strip().lower()
    if scheme in ('https', 'http'):
        return scheme == 'https'
    https_flag = str(request.environ.get('HTTPS') or '').strip().lower()
    if https_flag:
        return https_flag in _HTTPS_FLAGS
    return bool(request.is_secure)


def install_https_requirement(app):
    """Reject every request that did not arrive over HTTPS.

    Runs before blueprint handlers, so a plain-HTTP call never opens the
    KeePass file. ``REQUIRE_HTTPS`` defaults to true; local HTTP dev sets it
    false.
    """

    @app.before_request
    def _require_https():
        if not current_app.config.get('REQUIRE_HTTPS', True):
            return None
        if request_is_trusted_https():
            return None
        return make_response({'msg': 'HTTPS is required'}, 403)


def install_secret_guards(blueprint):
    """Forbid caching of blueprint responses and drop request-local credentials."""

    @blueprint.after_request
    def _no_store(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @blueprint.teardown_request
    def _drop_secrets(_exception=None):
        # PyKeePass keeps the password on the instance. Dropping the reference
        # ends the request-local hold. CPython cannot reliably zero the string.
        g.pop('db', None)
        g.pop('pw', None)
