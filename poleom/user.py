"""User / Account / Auth routes."""
from datetime import datetime, timedelta
from urllib import parse

from poorwsgi import abort, redirect, state
from poorwsgi.response import RedirectResponse, Response

from .lib.auth import (
    auth_user,
    check_login_cookie,
    create_login_cookie,
    destroy_login_cookie,
)
from .lib.change_request import ChangeRequest
from .lib.core import Request, app
from .lib.exceptions import DuplicityError, FormError
from .lib.smtp import Email
from .lib.user import User
from .lib.view import render_template


@app.route("/login")
@check_login_cookie
def login_page(req):
    """Return log in page."""
    if req.user:
        redirect(req.referer or "/")
    return render_template("user/login.html", redirect_url=req.referer)


@app.route("/login", method=state.METHOD_POST)
def login(req):
    """Create login cookie."""
    email = req.form.get("email")
    password = req.form.get("password")
    redirect_url = req.form.get("redirect_url")

    user = User.find(req.db, email, password)
    if not user:
        uri = parse.urlparse(req.referer)
        return render_template("user/login.html",
                               email=email,
                               redirect_url=req.referer,
                               error=True)

    session = create_login_cookie(user.id)
    uri = parse.urlparse(redirect_url)
    redirect_url = uri._replace(scheme="", netloc="").geturl()
    res = RedirectResponse(redirect_url)
    session.header(res)
    return res


@app.route("/logout")
def logout(req):
    """Create login cookie."""
    session = destroy_login_cookie(req.cookies)
    res = RedirectResponse(req.referer)
    session.header(res)
    return res


@app.route("/signup")
@check_login_cookie
def signup_page(_):
    """Return log in page."""
    return render_template("user/signup.html", errors={})


@app.route("/signup-check")
def signup_check(_):
    """Test check page only"""
    return render_template("user/signup-check.html", sender=app.smtp.sender)


@app.route("/signup", method=state.METHOD_POST)
def signup(req):
    """Create account."""
    name = req.form.get("name", "").strip()
    email = req.form.get("email", "").strip()
    signature = req.form.get("signature", "").strip() or None
    password = req.form.get("password", "").strip()
    password_again = req.form.get("password_again", "").strip()
    accept_terms = req.form.get("accept_terms")

    errors = {}
    if not name:
        errors["name"] = FormError.MISSING
    if not email:
        errors["email"] = FormError.MISSING
    if not Email.check(email):
        errors["email"] = FormError.INVALID
    if not password:
        errors["password"] = FormError.MISSING
    if not User.VALID_PASSWORD_REGEX.match(password):
        errors["password"] = FormError.INVALID
    if password != password_again:
        errors["password_again"] = FormError.MISMATCH
    if not accept_terms:
        errors["accept_terms"] = FormError.MISSING

    if errors:
        return render_template("user/signup.html",
                               name=name,
                               email=email,
                               signature=signature,
                               accept_terms=accept_terms,
                               errors=errors)

    try:
        user = User.create(req.db, name, email, password, signature)
    except DuplicityError:
        errors["email"] = FormError.DUPLICITY
        return render_template("user/signup.html",
                               name=name,
                               email=email,
                               signature=signature,
                               errors=errors)

    change_request = ChangeRequest.create(
        req.db, user.id, ChangeRequest.State.REGISTER, {
            "request_ip": req.remote_addr,
            "request_browser": req.user_agent,
        })
    change_request.send_email(app.smtp, user, req.construct_url(""))

    return render_template("user/signup-check.html", sender=app.smtp.sender)


@app.route("/user/profile")
@check_login_cookie
def user_profile(req: Request):
    """Return user profile."""
    user_id = req.args.getfirst("user_id", None, int)
    if user_id:
        user = User.get(req.db, user_id)
        if user is None:
            abort(state.HTTP_NOT_FOUND)
    else:
        user = req.user
        if user is None:
            abort(state.HTTP_FORBIDDEN)

    return render_template("user/profile.html", user=user, me=req.user)


@app.route("/user/account")
@auth_user
def user_account(req):
    """Return user account form."""
    return render_template("user/account.html", user=req.user)


@app.route("/user/account", method=state.METHOD_POST)
@auth_user
def user_account_set(req):
    """Change user account."""
    name = req.form.get("name", "").strip()
    email = req.form.get("email", "").strip()
    signature = req.form.get("signature", "").strip() or None
    password = req.form.get("password", "").strip() or None
    password_again = req.form.get("password_again", "").strip() or None

    errors = {}
    if not name:
        errors["name"] = FormError.MISSING
    if not email:
        errors["email"] = FormError.MISSING
    if not Email.check(email):
        errors["email"] = FormError.INVALID

    if password and not User.VALID_PASSWORD_REGEX.match(password):
        errors["password"] = FormError.INVALID
    if password != password_again:
        errors["password_again"] = FormError.MISMATCH

    old_email = req.user.email
    to_request = req.user.email != email or password

    req.user.name = name
    req.user.email = email
    req.user.signature = signature

    if errors:
        return render_template("user/account.html",
                               user=req.user,
                               errors=errors)

    req.user.update(req.db, password=password)

    if to_request:
        data = {
            "request_ip": req.remote_addr,
            "request_browser": req.user_agent,
        }
        if req.user.email != old_email:
            data["old_email"] = old_email
        if password:
            data["password"] = True

        change_request = ChangeRequest.create(req.db, req.user.id,
                                              ChangeRequest.State.INFO_CHANGED,
                                              data)
        change_request.send_email(app.smtp, req.user, req.construct_url(""))

    return RedirectResponse("/user/account#save-done")


@app.route("/user/reset-password", method=state.METHOD_GET_POST)
def reset_password_request(req: Request):
    """Return user account form."""
    if req.method_number != state.METHOD_POST:
        return render_template("user/reset-password-request.html")

    email = req.form.get("email", "").strip()

    errors = {}
    if not email:
        errors["email"] = FormError.MISSING
    if not Email.check(email):
        errors["email"] = FormError.INVALID

    user = User.find(req.db, email)
    if not user:
        errors["email"] = FormError.MISMATCH

    if errors:
        return render_template("user/reset-password-request.html",
                               errors=errors)

    change_request = ChangeRequest.create(
        req.db, user.id, ChangeRequest.State.PASSWORD, {
            "request_ip": req.remote_addr,
            "request_browser": req.user_agent,
        })
    change_request.send_email(app.smtp, user, req.construct_url(""))

    return render_template("user/reset-password-request.html", sent=True)


@app.route("/chr/<hexdigest:hex>")
def accept_change_request(req: Request, hexdigest: str):
    """Accept change request / change request form."""
    change_request = ChangeRequest.get(req.db, hexdigest)
    if not change_request:
        abort(state.HTTP_NOT_FOUND)  # TODO: Request Not Found
    expiration = change_request.created + timedelta(
        seconds=app.change_request_ttl)
    if change_request.accepted or expiration < datetime.now():
        abort(state.HTTP_GONE)  # TODO: Request Is Gone

    # Accept registration
    if change_request.state == ChangeRequest.State.REGISTER:
        # Confirm registration
        user = User.get(req.db, change_request.user_id)
        user.state = User.State.ACTIVE
        user.update(req.db)
        change_request.accept(req.db)

        session = create_login_cookie(user.id)
        res = RedirectResponse("/user/profile")
        session.header(res)
        return res

    if change_request.state == ChangeRequest.State.PASSWORD:
        return render_template("user/change-request.html",
                               change_request=change_request)

    return Response(status_code=state.HTTP_BAD_REQUEST)


@app.route("/chr/<hexdigest:hex>", method=state.METHOD_POST)
def post_change_request(req, hexdigest: str):
    """Accept change request."""
    change_request = ChangeRequest.get(req.db, hexdigest)
    if not change_request:
        abort(state.HTTP_NOT_FOUND)
    expiration = change_request.created + timedelta(
        seconds=app.change_request_ttl)
    if change_request.accepted or expiration < datetime.now():
        abort(state.HTTP_GONE)

    if change_request.state == ChangeRequest.State.PASSWORD:
        password = req.form.get("password", "").strip() or None
        password_again = req.form.get("password_again", "").strip() or None

        errors = {}
        if password and not User.VALID_PASSWORD_REGEX.match(password):
            errors["password"] = FormError.INVALID
        if password != password_again:
            errors["password_again"] = FormError.MISMATCH

        if errors:
            return render_template("user/reset_password.html",
                                   change_request=change_request,
                                   errors=errors)

        user = User.get(req.db, change_request.user_id)
        user.update(req.db, password=password)
        session = create_login_cookie(user.id)
        res = RedirectResponse("/user/profile")
        session.header(res)
        return res

    return Response(status_code=state.HTTP_BAD_REQUEST)
