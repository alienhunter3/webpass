"""Keep master passwords and decrypted API responses out of caches.

The password is taken from the current request and used to open the database
for that request only. It is not written to a session, a cookie, or a log.
"""

from flask import g, request


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
