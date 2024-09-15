"""Endpoints for sections."""
import logging

from poorwsgi import state
from poorwsgi.response import (
    JSONGeneratorResponse,
    JSONResponse,
    NoContentResponse,
    Response,
    abort,
)

from . import __name__ as appname
from .lib.auth import auth_user, check_login_cookie
from .lib.core import Request, app
from .lib.exceptions import DuplicityError, FormError
from .lib.pager import Pager
from .lib.response import check_etag, create_etag
from .lib.section import Section, SectionUser
from .lib.topic import Topic
from .lib.user import User
from .lib.view import render_template

log = logging.getLogger(appname)


@app.route("/s/<path>")
@check_login_cookie
def section_detail(req, path: str):
    """Return section detail."""
    section = Section.find(req.db, path)
    if not section.has_access(req.db, req.user):
        abort(404)

    pager = Pager(limit=20)
    topics = list(Topic.list(req.db, pager, section_id=section.id))
    last_modified = 0
    for topic in topics:
        last = int(topic.last.timestamp())
        last_modified = last if last > last_modified else last_modified

    etag = create_etag(last_modified, req.user.id if req.user else None)
    check_etag(req.headers, etag)

    return Response(render_template("section.html",
                                    me=req.user,
                                    section=section,
                                    topics=topics,
                                    pager=pager),
                    headers={"ETag": etag})


# Section administration


def bind_section(section_id: int, form):
    """Bind Form to Session."""
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    private = "private" in form
    state_ = form.get("state", "").strip()

    errors = {}
    if not title:
        errors["title"] = FormError.MISSING
    if not description:
        errors["description"] = FormError.MISSING
    if not state_:
        errors["state"] = FormError.MISSING
    try:
        state_ = Section.State(state_)
    except ValueError:
        state_ = Section.State.OPEN
        errors["state"] = FormError.INVALID

    section = Section(section_id, title, description, state_, private)
    if not section.path:
        errors["path"] = FormError.INVALID

    return section, errors


@app.route("/sections")
@auth_user(User.Role.MODERATOR)
def section_list(req):
    """Return list of sections for administration."""
    pager = Pager()
    pager.bind(req.args)

    # Admin see all sections
    user_id = None if req.user.is_admin() else req.user.id
    sections = Section.list(req.db, user_id)
    return render_template("section/list.html",
                           me=req.user,
                           sections=sections,
                           pager=pager)


@app.route("/sections/<section_id:int>", method=state.METHOD_PATCH)
@auth_user(role=User.Role.MODERATOR)  # only moderator can do that
def section_patch(req: Request, section_id: int):
    """Update user role."""
    if state_ := req.json.get("state", "").upper():
        try:
            state_ = Section.State(state_)
        except ValueError as err:
            log.warning("state: %s (%s)", err, state_)
            abort(state.HTTP_BAD_REQUEST)
    if weight := req.json.get("weight", 0):
        try:
            weight = 1 if weight > 0 else -1
        except TypeError as err:
            log.warning("weight: %s (%s)", err, weight)
            abort(state.HTTP_BAD_REQUEST)
    if (private := req.json.get("private")) is not None:
        private = bool(private)

    section = Section.get(req.db, section_id)
    if not section:
        abort(state.HTTP_NOT_FOUND)

    if state_:
        section.state = state_
    if private is not None:
        section.private = private

    section.update(req.db)

    if weight:
        section.swap(req.db, weight)

    json = section.to_dict()
    json["state"] = section.state.value
    return JSONResponse({"section": json})


@app.route("/sections/new")
@app.route("/sections/<section_id:int>")
@auth_user(role=User.Role.MODERATOR)
def section_edit(req, section_id: int = 0):
    """Return section detail."""
    if section_id:
        section = Section.get(req.db, section_id)
        if not section or not section.has_access(req.db, req.user):
            abort(state.HTTP_NOT_FOUND)
    else:
        section = Section(0, "", "", Section.State.OPEN, False)

    return render_template("section/form.html", me=req.user, section=section)


@app.route("/sections", method=state.METHOD_POST)
@app.route("/sections/<section_id:int>", method=state.METHOD_POST)
@auth_user(role=User.Role.MODERATOR)
def section_update(req, section_id: int = 0):
    """Update or Create section"""
    if section_id:
        section = Section.get(req.db, section_id)
        if not section or not section.has_access(req.db, req.user):
            abort(state.HTTP_NOT_FOUND)

    section, errors = bind_section(section_id, req.form)

    if not errors:
        try:
            if section.id:
                section.update(req.db)
            else:
                section.create(req.db)
        except DuplicityError:
            errors["title"] = FormError.DUPLICITY
            errors["path"] = FormError.DUPLICITY

    return render_template("section/form.html",
                           me=req.user,
                           section=section,
                           errors=errors)


@app.route("/sections/<section_id:int>/users")
@auth_user(role=User.Role.MODERATOR)
def section_users(req, section_id: int):
    """Return list of associates users."""
    section = Section.get(req.db, section_id)
    if not section or not section.has_access(req.db, req.user):
        abort(state.HTTP_NOT_FOUND)

    users = SectionUser.list(req.db, section_id)
    return JSONGeneratorResponse(users=users)


@app.route("/sections/<section_id:int>/users/<user_id:int>",
           method=state.METHOD_POST)
@auth_user(role=User.Role.MODERATOR)
def section_user_add(req, section_id: int, user_id: int):
    """Add user to associates users."""
    section = Section.get(req.db, section_id)
    if not section or not section.has_access(req.db, req.user):
        abort(state.HTTP_NOT_FOUND)
    user = User.get(req.db, user_id)
    if not user:
        abort(state.HTTP_NOT_FOUND)

    try:
        SectionUser.add(req.db, section_id, user_id)
    except DuplicityError:
        abort(state.HTTP_CONFLICT)
    return NoContentResponse()


@app.route("/sections/<section_id:int>/users/<user_id:int>",
           method=state.METHOD_DELETE)
@auth_user(role=User.Role.MODERATOR)
def section_user_delete(req, section_id: int, user_id: int):
    """Remove user from associates users."""
    section = Section.get(req.db, section_id)
    if not section or not section.has_access(req.db, req.user):
        abort(state.HTTP_NOT_FOUND)
    user = User.get(req.db, user_id)
    if not user:
        abort(state.HTTP_NOT_FOUND)

    SectionUser.remove(req.db, section_id, user_id)
    return NoContentResponse()
