"""Endpoints for topics."""
from urllib import parse

from MySQLdb.connections import Connection  # type: ignore[import-untyped]
from poorwsgi import state
from poorwsgi.response import abort, redirect

from .lib.auth import auth_user, check_login_cookie
from .lib.core import app
from .lib.exceptions import DuplicityError
from .lib.pager import Pager
from .lib.post import Post
from .lib.section import Section
from .lib.topic import Topic
from .lib.user import User
from .lib.view import render_template


def find_topic(db: Connection, section_path: str, topic_path: str):
    """Find topic in section on raise 404 HTTPException."""
    section = Section.find(db, section_path)
    if not section:
        abort(404)
    topic = Topic.find(db, section.id, topic_path)
    if not topic:
        abort(404)
    return section, topic


@app.route("/s/<section_path>", method=state.METHOD_POST)
@auth_user
def create_topic(req, section_path: str):
    """Return section detail."""
    section = Section.find(req.db, section_path)
    if not section:
        abort(404)

    title = req.form.get("title", "").strip()
    body = req.form.get("body", "").strip()
    if not title:
        uri = parse.urlparse(req.referer)
        redirect(uri._replace(fragment="empty_topic_title").geturl())
    if not body:
        uri = parse.urlparse(req.referer)
        redirect(uri._replace(fragment="empty_topic_body").geturl())

    try:
        topic = Topic.create(req.db, section.id, title)
        Post.create(req.db, topic.id, req.user.id, body)
    except DuplicityError:
        uri = parse.urlparse(req.referer)
        redirect(uri._replace(fragment="duplicity_topic_title").geturl())

    redirect(f"/s/{section_path}/{topic.path}")


@app.route("/s/<section_path>/<topic_path>")
@check_login_cookie
def topic_detail(req, section_path: str, topic_path: str):
    """Return section detail."""
    section, topic = find_topic(req.db, section_path, topic_path)

    pager = Pager(limit=10)
    pager.bind(req.args)
    posts = list(Post.list(req.db, pager, topic_id=topic.id))
    for post in posts:
        post.user = User.get(req.db, post.user_id)

    return render_template("topic.html",
                           user=req.user,
                           section=section,
                           topic=topic,
                           posts=posts,
                           pager=pager)
