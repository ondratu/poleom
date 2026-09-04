"""Authentication and authorization library."""
from functools import wraps

from poorwsgi import state
from poorwsgi.response import abort
from poorwsgi.session import PoorSession, SessionError

from .core import app
from .user import User


def check_login_cookie(fun):
    """Check login session."""
    @wraps(fun)
    def handler(req, *args, **kwargs):
        session = PoorSession(app.secret_key, same_site="Strict")
        try:
            session.load(req.cookies)
            if session.data:
                user = User.get(req.db, session.data.get("user_id"))
                if user and user.state == User.State.ACTIVE:
                    req.user = user
        except SessionError:
            pass
        return fun(req, *args, **kwargs)
    return handler


def create_login_cookie(user_id: int) -> PoorSession:
    """Create PoorSession object with user_id."""
    session = PoorSession(app.secret_key, same_site="Strict")
    session.data["user_id"] = user_id
    return session


def destroy_login_cookie(cookies) -> PoorSession:
    """Destroy existed session cookie."""
    session = PoorSession(app.secret_key, same_site="Strict")
    try:
        session.load(cookies)
        if session.data:
            session.destroy()
    except SessionError:
        pass
    return session


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
