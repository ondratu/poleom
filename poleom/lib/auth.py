"""Authentication and authorization library."""
from functools import wraps

from poorwsgi.response import abort
from poorwsgi.session import PoorSession, SessionError

from .core import app
from .user import User


def check_login_cookie(fun):
    """Check login session."""
    @wraps(fun)
    def handler(req, *args, **kwargs):
        session = PoorSession(app.secret_key, same_site=True)
        try:
            session.load(req.cookies)
            if session.data:
                req.user = User.get(req.db, session.data.get("user_id"))
        except SessionError:
            pass
        return fun(req, *args, **kwargs)
    return handler


def create_login_cookie(user_id: int) -> PoorSession:
    """Create PoorSession object with user_id."""
    session = PoorSession(app.secret_key, same_site=True)
    session.data["user_id"] = user_id
    return session


def destroy_login_cookie(cookies) -> PoorSession:
    """Destroy existed session cookie."""
    session = PoorSession(app.secret_key, same_site=True)
    try:
        session.load(cookies)
        if session.data:
            session.destroy()
    except SessionError:
        pass
    return session


def auth_user(fun):
    """Authorize user.

    FIXME: at this moment all login user can anything....
    """
    @wraps(fun)
    @check_login_cookie
    def handler(req, *args, **kwargs):
        if not req.user:
            abort(401)
        return fun(req, *args, **kwargs)
    return handler
