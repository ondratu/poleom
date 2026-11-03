"""Authentication and authorization library."""
from functools import wraps

from poorwsgi import state
from poorwsgi.response import RedirectResponse, abort
from poorwsgi.session import PoorSession

from .auth_backend import local_session
from .core import app
from .user import User


def check_login_cookie(fun):
    """Set `req.user` to the active user of the auth backend."""
    @wraps(fun)
    def handler(req, *args, **kwargs):
        user = app.auth_backend.load_user(req)
        if user and user.state == User.State.ACTIVE:
            req.user = user
        return fun(req, *args, **kwargs)
    return handler


def create_login_cookie(user_id: int) -> PoorSession:
    """Create PoorSession object with user_id."""
    session = local_session(app.secret_key)
    session.data["user_id"] = user_id
    return session


def local_login_only(fun):
    """Redirect to the auth backend when the local login is turned off."""
    @wraps(fun)
    def handler(req, *args, **kwargs):
        if not app.auth_backend.allows_local_login:
            return RedirectResponse(app.auth_backend.login_url(req, "/"))
        return fun(req, *args, **kwargs)
    return handler


def auth_user(role: User.Role = User.Role.MEMBER):
    """Authorize user."""
    def wrapper(fun):
        @wraps(fun)
        @check_login_cookie
        def handler(req, *args, **kwargs):
            if not req.user:
                abort(state.HTTP_UNAUTHORIZED)
            if req.user.state != User.State.ACTIVE:
                abort(state.HTTP_FORBIDDEN)  # only active users

            if not req.user.check_role(role):
                abort(state.HTTP_FORBIDDEN)  # need some another role

            return fun(req, *args, **kwargs)
        return handler
    return wrapper
