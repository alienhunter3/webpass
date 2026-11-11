import logging
import os
import re

import pytest

from pywebpass import create_app


def _capture_logger():
    logger = logging.getLogger('pywebpass')
    messages = []

    class _ListHandler(logging.Handler):
        def emit(self, record):
            messages.append(record.getMessage())

    handler = _ListHandler(level=logging.DEBUG)
    logger.addHandler(handler)
    return logger, handler, messages


def test_missing_database_refuses_to_start(tmp_path):
    db_path = tmp_path / 'passwords.kdbx'
    with pytest.raises(FileNotFoundError, match=re.escape(str(db_path))):
        create_app(instance_path=str(tmp_path))


def test_unreadable_database_refuses_to_start(tmp_path):
    db_path = tmp_path / 'passwords.kdbx'
    db_path.write_bytes(b'x')
    db_path.chmod(0)
    if os.access(db_path, os.R_OK):
        pytest.skip('process can still read mode 000 files')
    with pytest.raises(PermissionError, match=re.escape(str(db_path))):
        create_app(instance_path=str(tmp_path))


def test_readable_database_starts(tmp_path, monkeypatch):
    db_path = tmp_path / 'passwords.kdbx'
    db_path.write_bytes(b'not-a-real-kdbx')
    monkeypatch.setenv('WEBPASS_SYSTEMD', '0')
    app = create_app(instance_path=str(tmp_path))
    assert app.config['DATABASE'] == str(db_path)


def test_configured_database_path_is_checked(tmp_path):
    custom = tmp_path / 'vault' / 'other.kdbx'
    (tmp_path / 'config.py').write_text(
        f'DATABASE = {str(custom)!r}\nLOG_TO_SYSTEMD = False\n'
    )
    with pytest.raises(FileNotFoundError, match=re.escape(str(custom))):
        create_app(instance_path=str(tmp_path))


def test_configured_database_path_that_exists(tmp_path, monkeypatch):
    custom = tmp_path / 'other.kdbx'
    custom.write_bytes(b'x')
    (tmp_path / 'config.py').write_text(
        f'DATABASE = {str(custom)!r}\nLOG_TO_SYSTEMD = False\n'
    )
    monkeypatch.delenv('WEBPASS_SYSTEMD', raising=False)
    app = create_app(instance_path=str(tmp_path))
    assert app.config['DATABASE'] == str(custom)


def test_test_config_skips_database_check(tmp_path):
    missing = tmp_path / 'missing.kdbx'
    app = create_app(test_config={
        'DATABASE': str(missing),
        'LOG_TO_SYSTEMD': False,
    })
    assert app.config['DATABASE'] == str(missing)


def test_test_config_can_opt_in_to_database_check(tmp_path):
    missing = tmp_path / 'missing.kdbx'
    with pytest.raises(FileNotFoundError, match=re.escape(str(missing))):
        create_app(
            test_config={
                'DATABASE': str(missing),
                'LOG_TO_SYSTEMD': False,
            },
            require_database=True,
        )


def test_blank_database_setting_raises():
    with pytest.raises(RuntimeError, match='DATABASE'):
        create_app(
            test_config={'DATABASE': '', 'LOG_TO_SYSTEMD': False},
            require_database=True,
        )


def test_startup_does_not_print_secrets(tmp_path, monkeypatch):
    db_path = tmp_path / 'passwords.kdbx'
    db_path.write_bytes(b'x')
    (tmp_path / 'config.py').write_text(
        'import logging\n'
        "SECRET_KEY = 'super-secret-value'\n"
        'LOG_TO_SYSTEMD = False\n'
        'LOG_LEVEL = logging.DEBUG\n'
    )
    monkeypatch.delenv('WEBPASS_SYSTEMD', raising=False)
    printed = []
    monkeypatch.setattr(
        'builtins.print',
        lambda *args, **kwargs: printed.append(' '.join(str(arg) for arg in args)),
    )
    logger, handler, messages = _capture_logger()
    try:
        create_app(instance_path=str(tmp_path))
    finally:
        logger.removeHandler(handler)

    blob = '\n'.join(printed + messages)
    assert 'super-secret-value' not in blob
    assert 'SECRET_KEY' not in blob
    assert str(db_path) in blob


def test_missing_instance_config_still_starts(tmp_path, monkeypatch):
    db_path = tmp_path / 'passwords.kdbx'
    db_path.write_bytes(b'x')
    monkeypatch.setenv('WEBPASS_SYSTEMD', '0')
    logger, handler, messages = _capture_logger()
    try:
        app = create_app(instance_path=str(tmp_path))
    finally:
        logger.removeHandler(handler)
    assert app.config['DATABASE'] == str(db_path)
    assert any('config.py' in message for message in messages)
    assert all('SECRET_KEY' not in message for message in messages)
