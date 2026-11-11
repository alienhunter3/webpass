import io
import logging
from pathlib import Path

from pykeepass import create_database

from pywebpass import create_app


MASTER = 'master-secret-value'
ENTRY_PASSWORD = 'entry-secret-value'
NOTE = 'note-secret-value'
URL = 'https://secret.example/path'
CUSTOM = 'otp-secret-value'
HTML_NAME = '<img src=x onerror=alert(1)>'


def _database(tmp_path):
    path = tmp_path / 'passwords.kdbx'
    db = create_database(str(path), password=MASTER)
    group = db.add_group(db.root_group, HTML_NAME)
    entry = db.add_entry(
        group,
        'Email',
        'ada',
        ENTRY_PASSWORD,
        url=URL,
        notes=NOTE,
    )
    entry.set_custom_property('recovery', CUSTOM)
    db.save()
    return path, str(group.uuid), str(entry.uuid)


def _app(tmp_path, **config):
    path, group_uuid, entry_uuid = _database(tmp_path)
    settings = {
        'DATABASE': str(path),
        'LOG_TO_SYSTEMD': False,
        'TESTING': True,
    }
    settings.update(config)
    app = create_app(test_config=settings, require_database=True)
    return app, group_uuid, entry_uuid


def test_tree_requires_auth_and_omits_secrets(tmp_path):
    app, group_uuid, entry_uuid = _app(tmp_path)
    client = app.test_client()

    missing = client.get('/api/group/tree')
    assert missing.status_code == 401
    assert MASTER not in missing.get_data(as_text=True)

    wrong = client.get('/api/group/tree', auth=('user', 'not-the-password'))
    assert wrong.status_code == 401
    assert 'not-the-password' not in wrong.get_data(as_text=True)
    assert MASTER not in wrong.get_data(as_text=True)

    res = client.get('/api/group/tree', auth=('user', MASTER))
    assert res.status_code == 200
    assert 'no-store' in res.headers['Cache-Control'].lower()
    body = res.get_data(as_text=True)
    for secret in (MASTER, ENTRY_PASSWORD, NOTE, URL, CUSTOM):
        assert secret not in body
    payload = res.get_json()['data']
    assert all('password' not in entry for entry in payload['entries'])
    assert all('notes' not in entry for entry in payload['entries'])
    groups = {item['uuid']: item for item in payload['groups']}
    assert groups[group_uuid]['name'] == HTML_NAME
    assert groups[group_uuid]['parent']
    matched = [item for item in payload['entries'] if item['uuid'] == entry_uuid]
    assert matched == [{
        'uuid': entry_uuid,
        'title': 'Email',
        'username': 'ada',
        'group': group_uuid,
    }]


def test_secret_detail_still_returns_password_without_caching(tmp_path):
    app, _group_uuid, entry_uuid = _app(tmp_path)
    client = app.test_client()
    res = client.get(f'/api/secret/{entry_uuid}', auth=('user', MASTER))
    assert res.status_code == 200
    assert res.get_json()['data']['password'] == ENTRY_PASSWORD
    assert 'no-store' in res.headers['Cache-Control'].lower()


def test_failed_login_and_attachment_body_are_not_logged(tmp_path):
    app, _group_uuid, entry_uuid = _app(tmp_path, LOG_LEVEL=logging.DEBUG)
    client = app.test_client()
    logger = logging.getLogger('pywebpass')
    messages = []

    class _ListHandler(logging.Handler):
        def emit(self, record):
            messages.append(record.getMessage())

    handler = _ListHandler(level=logging.DEBUG)
    logger.addHandler(handler)
    try:
        client.get('/api/group/tree', auth=('user', MASTER + '-wrong'))
        uploaded = client.post(
            f'/api/secret/{entry_uuid}/attachment',
            data={'attachment': (io.BytesIO(b'SECRET-BYTES-MARKER'), 'note.txt')},
            auth=('user', MASTER),
        )
    finally:
        logger.removeHandler(handler)

    assert uploaded.status_code == 201
    logged = '\n'.join(messages)
    assert MASTER not in logged
    assert 'SECRET-BYTES-MARKER' not in logged
    assert ENTRY_PASSWORD not in logged


def test_ui_timeouts_and_no_store(tmp_path):
    app, _group_uuid, _entry_uuid = _app(tmp_path)
    res = app.test_client().get('/')
    assert res.status_code == 200
    page = res.get_data(as_text=True)
    assert 'data-idle-timeout="900"' in page
    assert 'data-absolute-timeout="28800"' in page
    assert 'no-store' in res.headers['Cache-Control'].lower()
    assert 'refreshTreeClick' in page
    assert 'logOut' in page


def test_ui_timeout_overrides_and_invalid_values(tmp_path):
    path = tmp_path / 'other.kdbx'
    create_database(str(path), password=MASTER).save()
    app = create_app(
        test_config={
            'DATABASE': str(path),
            'LOG_TO_SYSTEMD': False,
            'UI_IDLE_TIMEOUT': 120,
            'UI_ABSOLUTE_TIMEOUT': 'nope',
        },
        require_database=True,
    )
    page = app.test_client().get('/').get_data(as_text=True)
    assert 'data-idle-timeout="120"' in page
    assert 'data-absolute-timeout="28800"' in page

    disabled = create_app(
        test_config={
            'DATABASE': str(path),
            'LOG_TO_SYSTEMD': False,
            'UI_IDLE_TIMEOUT': 0,
            'UI_ABSOLUTE_TIMEOUT': -8,
        },
        require_database=True,
    )
    page = disabled.test_client().get('/').get_data(as_text=True)
    assert 'data-idle-timeout="900"' in page
    assert 'data-absolute-timeout="28800"' in page


def test_ui_script_does_not_store_password_or_inject_html():
    text = (Path(__file__).resolve().parents[1] / 'pywebpass/static/js/webpass.js').read_text()
    assert 'localStorage.setItem' not in text
    assert 'sessionStorage.setItem' not in text
    assert 'innerHTML = g.name' not in text
    assert 'innerHTML = s.username' not in text
    assert 'innerHTML = pair[1]' not in text
    assert 'fetch_all' not in text
    assert "/tree" in text
