"""Endpoints for sections."""
from urllib import parse

from poorwsgi import state
from poorwsgi.response import abort, redirect

from .lib.auth import auth_user, check_login_cookie
from .lib.core import app
from .lib.exceptions import DuplicityError
from .lib.pager import Pager
from .lib.section import Section
from .lib.topic import Topic
from .lib.view import generate_page


@app.route("/s", method=state.METHOD_POST)
@auth_user
def create_section(req):
    """Create new section."""
    title = req.form.get("title").strip()
    description = req.form.get("description").strip()
    if not title:
        uri = parse.urlparse(req.referer)
        redirect(uri._replace(fragment="empty_section_title").geturl())

    try:
        Section.create(req.db, title, description)
    except DuplicityError:
        uri = parse.urlparse(req.referer)
        redirect(uri._replace(fragment="duplicity_section_title").geturl())

    redirect(f"/s/{title}")


@app.route("/s/<title>")
@check_login_cookie
def section_detail(req, title: str):
    """Return section detail."""
    section = Section.find(req.db, title)
    if not section:
        abort(404)

    pager = Pager(limit=20)
    topics = Topic.list(req.db, pager, section_id=section.id)
    return generate_page("section.html",
                         user=req.user,
                         section=section,
                         topics=topics,
                         pager=pager)
