"""Unit tests of the authentication backends and their loading."""
from unittest.mock import MagicMock

import pytest
from poorwsgi.response import RedirectResponse

from poleom.lib.auth_backend import (
    AuthBackend,
    Identity,
    LocalAuthBackend,
    load_backend,
)
from poleom.lib.core import app


class FakeBackend(AuthBackend):
    """Backend for the tests."""

    def identity(self, req):
        return None

    def login_url(self, req, next_url):
        return "/fake-login"

    def logout(self, req):
        return RedirectResponse("/")


def test_identity_defaults():
    identity = Identity("1", "Ann", "ann@example.com")

    assert identity.lang is None
    assert identity.active


def test_base_backend_defaults():
    backend = FakeBackend()

    assert not backend.allows_local_login
    assert backend.signup_url(MagicMock(), "/") is None
    assert backend.profile_url(MagicMock()) is None
    assert backend.init_app(app) is None


def test_base_backend_is_abstract():
    with pytest.raises(TypeError, match="abstract"):
        # instantiating the abstract class is the test
        # pylint: disable-next=abstract-class-instantiated
        AuthBackend()  # type: ignore[abstract]


def test_local_backend_has_no_identity():
    assert app.auth_backend.identity(MagicMock()) is None


def test_default_backend_is_local():
    assert isinstance(load_backend(None), LocalAuthBackend)
    assert isinstance(load_backend(""), LocalAuthBackend)
    assert isinstance(app.auth_backend, LocalAuthBackend)
    assert app.auth_backend.allows_local_login


def test_load_backend():
    backend = load_backend(f"{__name__}:FakeBackend")

    assert isinstance(backend, FakeBackend)


@pytest.mark.parametrize("spec", [
    "no_such_module_xyz:Backend",  # module
    f"{__name__}:NoSuchClass",  # class
    __name__,  # missing class
    ":FakeBackend",  # missing module
])
def test_load_backend_invalid(spec):
    with pytest.raises(ValueError, match="app_auth_backend"):
        load_backend(spec)


def test_load_backend_not_a_backend():
    with pytest.raises(ValueError, match="not an AuthBackend"):
        load_backend(f"{__name__}:pytest")
    with pytest.raises(ValueError, match="not an AuthBackend"):
        load_backend("builtins:dict")
