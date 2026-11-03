"""Integrity tests of the authentication backends with SQLite database."""
from time import time
from unittest.mock import patch

from poorwsgi.request import Request
from poorwsgi.response import RedirectResponse
from poorwsgi.session import PoorSession, SessionError

from poleom.lib.auth import check_login_cookie, create_login_cookie
from poleom.lib.auth_backend import AuthBackend, Identity
from poleom.lib.core import app
from poleom.lib.user import User


class FakeBackend(AuthBackend):
    """Backend with the identity set by the test."""

    def __init__(self, identity=None):
        self.current = identity

    def identity(self, req):
        return self.current

    def login_url(self, req, next_url):
        return "/fake-login"

    def logout(self, req):
        return RedirectResponse("/fake-logout")


def make_request(db, cookie=""):
    env = {"REQUEST_STARTTIME": time(), "PATH_INFO": "/"}
    if cookie:
        env["HTTP_COOKIE"] = cookie
    req = Request(env, app)
    req.db = db
    req.lang = "cs"
    return req


def test_load_user_creates_user(db):
    backend = FakeBackend(Identity("1", "Ann", "ann@example.com", "cs"))

    user = backend.load_user(make_request(db))

    assert user is not None
    assert user.auth_sub == "1"
    assert User.get(db, user.id).email == "ann@example.com"


def test_load_user_without_identity(db):
    assert FakeBackend().load_user(make_request(db)) is None


def test_load_user_inactive_identity(db):
    backend = FakeBackend(Identity("1", "Ann", "ann@example.com",
                                   active=False))

    assert backend.load_user(make_request(db)) is None
    assert User.count(db) == 1  # only the default administrator


def test_load_user_duplicate_email(db, make_user, caplog):
    make_user("ann")
    backend = FakeBackend(Identity("1", "Ann", "ann@example.com"))

    assert backend.load_user(make_request(db)) is None
    assert "used by another user" in caplog.text


def test_local_load_user(db, make_user):
    user = make_user()
    session = create_login_cookie(user.id)
    session.write()
    cookie = session.cookie.output(header="").strip()

    loaded = app.auth_backend.load_user(make_request(db, cookie))

    assert loaded.id == user.id


def test_local_load_user_without_session(db):
    backend = app.auth_backend

    assert backend.load_user(make_request(db)) is None
    assert backend.load_user(make_request(db, "SID=invalid")) is None
    with patch.object(PoorSession, "load", side_effect=SessionError):
        assert backend.load_user(make_request(db)) is None


def test_local_urls(db):
    backend = app.auth_backend
    req = make_request(db)

    assert backend.login_url(req, "/") == "/login?lang=cs"
    assert backend.signup_url(req, "/") == "/signup?lang=cs"
    assert backend.profile_url(req) == "/user/account?lang=cs"


def test_local_logout_destroys_session(db, make_user):
    session = create_login_cookie(make_user().id)
    session.write()
    cookie = session.cookie.output(header="").strip()

    res = app.auth_backend.logout(make_request(db, cookie))

    assert res.headers["Location"] == "/"
    assert res.headers["Set-Cookie"]


def test_local_logout_without_session(db):
    res = app.auth_backend.logout(make_request(db))

    assert res.headers["Location"] == "/"


def test_local_logout_invalid_session(db):
    with patch.object(PoorSession, "load", side_effect=SessionError):
        res = app.auth_backend.logout(make_request(db))

    assert res.headers["Location"] == "/"


@check_login_cookie
def whoami(req):
    return req.user


def test_decorator_uses_backend(db):
    backend = FakeBackend(Identity("1", "Ann", "ann@example.com"))

    with patch.object(app, "auth_backend", backend):
        user = whoami(make_request(db))

    assert user.auth_sub == "1"


def test_decorator_ignores_banned_user(db):
    backend = FakeBackend(Identity("1", "Ann", "ann@example.com"))
    user = backend.load_user(make_request(db))
    user.state = User.State.BANNED
    user.update(db)

    with patch.object(app, "auth_backend", backend):
        req = make_request(db)
        req.user = None
        assert whoami(req) is None


def test_logout_endpoint_uses_backend(client):
    with patch.object(app, "auth_backend", FakeBackend()):
        res = client.get("/logout")

    assert res.status == 302
    assert res.headers["Location"] == "/fake-logout"
