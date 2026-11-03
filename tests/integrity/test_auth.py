"""Integrity tests of the login cookie and the authorization decorators."""
from time import time
from unittest.mock import patch

import pytest
from poorwsgi import state
from poorwsgi.request import Request
from poorwsgi.response import HTTPException
from poorwsgi.session import PoorSession, SessionError

from poleom.lib.auth import (
    auth_user,
    check_login_cookie,
    create_login_cookie,
)
from poleom.lib.user import User
from poleom.main import application as app


def make_request(db, session=None, cookie=None):
    """Return request, which has the session cookie."""
    env = {"REQUEST_STARTTIME": time(), "PATH_INFO": "/"}
    if session:
        session.write()
        env["HTTP_COOKIE"] = session.cookie.output(header="").strip()
    if cookie:
        env["HTTP_COOKIE"] = cookie
    req = Request(env, app)
    req.db = db
    req.user = None
    return req


def session_for(user):
    return create_login_cookie(user.id)


@check_login_cookie
def whoami(req):
    return req.user


@auth_user()
def member_only(req):
    return req.user


@auth_user(User.Role.ADMIN)
def admin_only(req):
    return req.user


def test_create_cookie():
    session = create_login_cookie(7)

    assert session.data["user_id"] == 7


def test_no_cookie_means_no_user(db):
    assert whoami(make_request(db)) is None


def test_invalid_cookie_means_no_user(db):
    assert whoami(make_request(db, cookie="SID=invalid")) is None


def test_active_user_is_set(db, make_user):
    user = make_user()
    req = make_request(db, session_for(user))
    assert whoami(req).id == user.id


def test_not_active_user_is_not_set(db, make_user):
    user = make_user()
    user.state = User.State.BANNED
    user.update(db)

    assert whoami(make_request(db, session_for(user))) is None


def test_missing_user_is_not_set(db):
    assert whoami(make_request(db, create_login_cookie(9999))) is None


def test_auth_requires_login(db):
    with pytest.raises(HTTPException) as err:
        member_only(make_request(db))
    assert err.value.status_code == state.HTTP_UNAUTHORIZED


def test_auth_member_passes(db, make_user):
    user = make_user()
    assert member_only(make_request(db, session_for(user))).id == user.id


def test_auth_needs_role(db, make_user):
    member = make_user("member")
    admin = make_user("boss", User.Role.ADMIN)

    with pytest.raises(HTTPException) as err:
        admin_only(make_request(db, session_for(member)))
    assert err.value.status_code == state.HTTP_FORBIDDEN
    assert admin_only(make_request(db, session_for(admin))).id == admin.id


def test_session_error_means_no_user(db):
    req = make_request(db)
    with patch.object(PoorSession, "load", side_effect=SessionError):
        assert whoami(req) is None


def test_auth_not_active_user_is_forbidden(db, make_user):
    user = make_user()
    user.state = User.State.BANNED
    req = make_request(db)
    req.user = user  # check_login_cookie does not set not active users

    with pytest.raises(HTTPException) as err:
        member_only(req)
    assert err.value.status_code == state.HTTP_FORBIDDEN
