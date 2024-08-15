"""Core page output."""
from urllib import parse

from MySQLdb import ProgrammingError  # type: ignore[import-untyped]
from poorwsgi import redirect, state
from poorwsgi.response import JSONResponse, RedirectResponse

from .lib.auth import (
    auth_user,
    check_login_cookie,
    create_login_cookie,
    destroy_login_cookie,
)
from .lib.core import app
from .lib.pager import Pager
from .lib.section import Section
from .lib.topic import Topic
from .lib.user import User
from .lib.view import generate_page, md2rst, parse_system_messages, rst2html

TABLE_DOESNT_EXIST_ERR = 1146


@app.route("/")
@check_login_cookie
def root(req):
    """Root / page"""
    pager = Pager(limit=20)
    pager.bind(req.args)
    try:
        section = Section.get(req.db, Section.ROOT_ID)
        sections = Section.list(req.db)
        total = Section.total(req.db)

        topics = Topic.list(req.db, pager, section_id=Section.ROOT_ID)
    except ProgrammingError as err:
        if err.args[0] == TABLE_DOESNT_EXIST_ERR:
            redirect("/wizard")
    return generate_page("index.html",
                         user=req.user,
                         section=section,
                         sections=sections,
                         total=total,
                         topics=topics,
                         pager=pager)


@app.route("/login", method=state.METHOD_POST)
def login(req):
    """Create login cookie."""
    email = req.form.get("email")
    password = req.form.get("password")
    user = User.find(req.db, email, password)
    if not user:
        uri = parse.urlparse(req.referer)
        redirect(uri._replace(fragment="bad_login").geturl())
    session = create_login_cookie(user.id)
    res = RedirectResponse(req.referer)
    session.header(res)
    return res


@app.route("/logout")
def logout(req):
    """Create login cookie."""
    session = destroy_login_cookie(req.cookies)
    res = RedirectResponse(req.referer)
    session.header(res)
    return res


@app.route("/preview", method=state.METHOD_POST)
@auth_user
def preview(req):
    """Check markdown and return preview."""
    source = req.form.getfirst("source", "").strip()
    if not source:
        return JSONResponse(errors=[], html="")

    html, errors = rst2html(md2rst(source))
    return JSONResponse(status_code=200 if not errors else 202,
                        html=html,
                        errors=parse_system_messages(errors))
