"""Core page output."""
from MySQLdb import ProgrammingError  # type: ignore[import-untyped]
from poorwsgi import redirect, state
from poorwsgi.response import JSONResponse

from .lib.auth import auth_user, check_login_cookie
from .lib.core import app
from .lib.pager import Pager
from .lib.section import Section
from .lib.topic import Topic
from .lib.view import md2rst, parse_system_messages, render_template, rst2html

TABLE_DOESNT_EXIST_ERR = 1146


@app.route("/")
@check_login_cookie
def root(req):
    """Root / page"""
    try:
        sections = list(Section.list(req.db))

        pager = Pager()
        pager.limit = 3
        for section in sections:
            section.topics = Topic.list(req.db, pager, section.id)
    except ProgrammingError as err:
        if err.args[0] == TABLE_DOESNT_EXIST_ERR:
            redirect("/wizard")
    return render_template("index.html", me=req.user, sections=sections)


@app.route("/terms")
def terms(_):
    """Return Terms."""
    return render_template("terms.html")


@app.route("/preview", method=state.METHOD_POST)
@auth_user()
def preview(req):
    """Check markdown and return preview."""
    source = req.form.getfirst("source", "").strip()
    if not source:
        return JSONResponse(errors=[], html="")

    html, errors = rst2html(md2rst(source))
    return JSONResponse(status_code=200 if not errors else 202,
                        html=html,
                        errors=parse_system_messages(errors))
