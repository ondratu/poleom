"""Integrity tests of the application with an external auth backend."""
from unittest.mock import patch

import pytest
from poorwsgi.response import RedirectResponse

from poleom.lib.auth_backend import AuthBackend, Identity
from poleom.lib.core import app
from poleom.lib.user import User


class ExternalBackend(AuthBackend):
    """Backend of an external service, the identity is set by the test."""

    def __init__(self):
        self.current = None

    def identity(self, req):
        return self.current

    def login_url(self, req, next_url):
        return f"https://sso.example.com/login?next={next_url}"

    def signup_url(self, req, next_url):
        return "https://sso.example.com/signup"

    def profile_url(self, req):
        return "https://sso.example.com/me"

    def logout(self, req):
        return RedirectResponse("https://sso.example.com/logout")


@pytest.fixture
def backend():
    external = ExternalBackend()
    with patch.object(app, "auth_backend", external):
        yield external


@pytest.fixture
def logged(backend):
    backend.current = Identity("sub-1", "Ann", "ann@example.com", "cs")
    return backend


@pytest.mark.parametrize(("method", "path"), [
    ("GET", "/login"),
    ("POST", "/login"),
    ("GET", "/signup"),
    ("GET", "/signup-check"),
    ("POST", "/signup"),
    ("GET", "/user/reset-password"),
    ("POST", "/user/reset-password"),
    ("GET", "/c/" + "a" * 64),
])
def test_local_login_redirects_to_backend(client, backend, method, path):
    res = client.request(method, path)

    assert res.status == 302
    assert res.headers["Location"] == "https://sso.example.com/login?next=/"


def test_logout_goes_to_backend(client, backend):
    res = client.get("/logout")

    assert res.headers["Location"] == "https://sso.example.com/logout"


def test_anonymous_header_links_to_backend(client, backend):
    res = client.get("/en/")

    assert 'href="https://sso.example.com/login?next=/en/"' in res.text
    assert 'href="https://sso.example.com/signup"' in res.text


def test_anonymous_header_without_signup(client, backend):
    with patch.object(ExternalBackend, "signup_url", return_value=None):
        res = client.get("/en/")

    assert "Sign up" not in res.text


def test_identity_creates_user_at_first_request(client, db, logged):
    res = client.get("/user/profile")

    assert res.status == 200
    user = User.find(db, "ann@example.com")
    assert user is not None
    assert user.auth_sub == "sub-1"
    assert user.data == {"lang": "cs"}
    assert 'href="https://sso.example.com/me"' in res.text  # menu


def test_deactivated_identity_is_not_logged_in(client, logged):
    logged.current.active = False

    assert client.get("/user/profile").status == 401


def test_account_form_has_only_signature(client, logged):
    res = client.get("/user/account")

    assert res.status == 200
    assert 'name="signature"' in res.text
    assert 'name="password"' not in res.text
    assert 'name="email"' not in res.text
    assert 'href="https://sso.example.com/me"' in res.text


def test_account_form_without_profile_url(client, logged):
    with patch.object(ExternalBackend, "profile_url", return_value=None):
        res = client.get("/user/account")

    assert 'name="name"' not in res.text


def test_account_sets_only_signature(client, db, logged):
    client.get("/user/profile")  # the first request creates the user

    res = client.post("/user/account", form={
        "name": "Hacker", "email": "hacker@example.com",
        "signature": "Cheers", "password": "N3wPassw0rd",
        "password_again": "N3wPassw0rd"})

    assert res.status == 302
    user = User.find(db, "ann@example.com")
    assert user.name == "Ann"
    assert user.signature == "Cheers"
    assert User.find(db, "ann@example.com", "N3wPassw0rd") is None
