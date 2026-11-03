"""Authentication backends, see docs/auth-backends.rst."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING

from poorwsgi.response import RedirectResponse, Response
from poorwsgi.session import PoorSession, SessionError

from .exceptions import DuplicityError
from .user import User

if TYPE_CHECKING:
    from .core import App, Request

# `return None` is the explicit default of the optional hooks
# pylint: disable=useless-return

log = logging.getLogger(__name__)


@dataclass
class Identity:
    """Who is the user of the request according to the auth backend."""

    subject: str  # stable id at the provider, never changes
    name: str
    email: str
    lang: str | None = None
    active: bool = True


def local_session(secret_key: str | bytes) -> PoorSession:
    """Return the session of the local login."""
    return PoorSession(secret_key, same_site="Strict")


class AuthBackend(ABC):
    """Base class of the authentication plugins."""

    # True only for the backend which logs in by the e-mail and the password
    allows_local_login = False

    def init_app(self, app: "App") -> None:
        """Call once at the start, register own routes here."""
        del app

    @abstractmethod
    def identity(self, req: "Request") -> Identity | None:
        """Return the identity of the request or None."""

    @abstractmethod
    def login_url(self, req: "Request", next_url: str) -> str:
        """Return where to send the user to log in, then back to next_url."""

    def signup_url(self, req: "Request", next_url: str) -> str | None:
        """Return where to register, None hides the link."""
        del req, next_url
        return None

    def profile_url(self, req: "Request") -> str | None:
        """Return where the user changes the password, None hides the link."""
        del req
        return None

    @abstractmethod
    def logout(self, req: "Request") -> Response:
        """Destroy the session and return the response (a redirect)."""

    def load_user(self, req: "Request") -> User | None:
        """Return the local user of the request or None."""
        identity = self.identity(req)
        if not identity or not identity.active:
            return None
        try:
            return User.from_identity(req.db, identity)
        except DuplicityError:
            log.warning("E-mail %s of the identity %s is used by another user",
                        identity.email, identity.subject)
            return None


class LocalAuthBackend(AuthBackend):
    """Accounts and passwords of the forum, the session cookie of the forum."""

    allows_local_login = True

    def __init__(self):
        self.secret_key: str | bytes = ""

    def init_app(self, app: "App") -> None:
        self.secret_key = app.secret_key

    def identity(self, req: "Request") -> Identity | None:
        """The local login has no identity, see `load_user`."""
        del req
        return None

    def load_user(self, req: "Request") -> User | None:
        session = local_session(self.secret_key)
        try:
            session.load(req.cookies)
        except SessionError:
            return None
        user_id = session.data.get("user_id") if session.data else None
        if user_id is None:
            return None
        return User.get(req.db, user_id)

    def login_url(self, req: "Request", next_url: str) -> str:
        del next_url
        return f"/login?lang={req.lang}"

    def signup_url(self, req: "Request", next_url: str) -> str | None:
        del next_url
        return f"/signup?lang={req.lang}"

    def profile_url(self, req: "Request") -> str | None:
        return f"/user/account?lang={req.lang}"

    def logout(self, req: "Request") -> Response:
        session = local_session(self.secret_key)
        try:
            session.load(req.cookies)
            if session.data:
                session.destroy()
        except SessionError:
            pass
        res = RedirectResponse("/")
        session.header(res)
        return res


def load_backend(spec: str | None) -> AuthBackend:
    """Return the backend of `module:Class`, the local one when not set."""
    if not spec:
        return LocalAuthBackend()
    module_name, _, class_name = spec.partition(":")
    try:
        cls = getattr(import_module(module_name), class_name)
    except (ImportError, AttributeError, ValueError) as err:
        msg = f"Can not load `app_auth_backend` `{spec}` (module:Class): {err}"
        raise ValueError(msg) from err
    if not (isinstance(cls, type) and issubclass(cls, AuthBackend)):
        msg = f"`app_auth_backend` `{spec}` is not an AuthBackend class."
        raise ValueError(msg)  # noqa: TRY004
    return cls()
