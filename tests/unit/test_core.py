"""Unit tests of the application configuration."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from poorwsgi import Application

from poleom import __name__ as appname
from poleom.lib import core
from poleom.lib.core import App, Request, db_connect


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Valid minimal environment."""
    monkeypatch.setenv("app_db", "mysql://user@localhost/poleom")
    monkeypatch.setenv("app_secret_key", "secret")
    monkeypatch.setenv("app_smtp", "smtp://localhost/root@localhost")
    monkeypatch.setenv("app_attachments", str(tmp_path))
    # Application is a per-name singleton, the imported one has the name
    names = Application._Application__instances
    monkeypatch.setattr(Application, "_Application__instances",
                        [name for name in names if name != appname])
    return monkeypatch


@pytest.mark.usefixtures("env")
def test_defaults():
    app = App()

    assert app.title == "Poleom"
    assert app.default_lang == "en"
    assert app.change_request_ttl == 86400
    assert app.db_conf == {
        "host": "localhost",
        "port": 3306,
        "database": "poleom",
        "charset": "utf8mb4",
        "user": "user",
    }
    assert app.terms["en"] == "/not-found?lang=en"
    assert app.smtp.timeout == 10


def test_full_dsn(env):
    env.setenv("app_db", "mysql://user:pass@db.example.com:3307/forum::utf8")
    app = App()

    assert app.db_conf == {
        "host": "db.example.com",
        "port": 3307,
        "database": "forum",
        "charset": "utf8",
        "user": "user",
        "password": "pass",
    }


def test_options(env):
    env.setenv("app_title", "My forum")
    env.setenv("app_default_lang", "cs")
    env.setenv("app_terms_cs", "/terms")
    env.setenv("app_change_request_ttl", "60")
    app = App()

    assert app.title == "My forum"
    assert app.default_lang == "cs"
    assert app.terms["cs"] == "/terms"
    assert app.change_request_ttl == 60


def test_debug(env):
    env.setenv("app_debug", "True")
    assert App().debug


def test_invalid_db(env):
    env.setenv("app_db", "invalid")
    with pytest.raises(ValueError, match="app_db"):
        App()


def test_missing_secret_key(env):
    env.delenv("app_secret_key")
    with pytest.raises(ValueError, match="secret_key"):
        App()


def test_attachments_is_not_directory(env, tmp_path):
    env.setenv("app_attachments", str(tmp_path / "missing"))
    with pytest.raises(ValueError, match="not directory"):
        App()


@pytest.mark.usefixtures("env")
def test_attachments_is_not_writable():
    with patch.object(core, "access", return_value=False), \
            pytest.raises(ValueError, match="not writable"):
        App()


def test_request_properties():
    req = Request({"REQUEST_STARTTIME": 0, "PATH_INFO": "/"}, core.app)
    req.db = "connection"
    req.lang = "cs"

    assert req.db == "connection"
    assert req.lang == "cs"


def test_db_connect():
    req = SimpleNamespace()
    with patch.object(core, "connect", return_value="conn") as connect:
        db_connect(req)

    assert req.db == "conn"
    assert req.lang == core.app.default_lang
    assert connect.call_args.kwargs["database"] == core.app.db_conf["database"]
