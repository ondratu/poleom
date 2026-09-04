"""Endpoints for topics."""
from urllib import parse

from MySQLdb.connections import Connection  # type: ignore[import-untyped]
from poorwsgi import state
from poorwsgi.response import Response, abort, redirect

from .lib.attachment import Attachment
from .lib.auth import auth_user, check_login_cookie
from .lib.core import app
from .lib.exceptions import DuplicityError
from .lib.pager import Pager
from .lib.post import Post
from .lib.response import check_etag, create_etag, render_response
from .lib.rss import RSS_ITEMS, rss_response
from .lib.section import Section
from .lib.topic import Topic
from .lib.user import User

ITEMS_ON_PAGE = 10


def find_topic(db: Connection, lang: str, section_path: str, topic_path: str,
               user: User | None):
    """Find topic in section on raise 404 HTTPException."""
    section = Section.find(db, lang, section_path)
    if not section or not section.has_access(db, user):
        abort(404)
    topic = Topic.find(db, section.id, topic_path)
    if not topic:
        abort(404)
    return section, topic


def topic_page(req, topic_id: int, check: bool = False):
    """Get data for topic page."""
    pager = Pager(limit=ITEMS_ON_PAGE)
    pager.bind(req.args)
    posts = list(Post.list(req.db, pager, topic_id=topic_id))
    etag = ""
    if check:
        last_modified = 0
        for post in posts:
            last = int((post.modified or post.created).timestamp())
            last_modified = last if last > last_modified else last_modified

        etag = create_etag(last_modified, req.user.id if req.user else None)
        check_etag(req.headers, etag)

    for post in posts:
        post.user = User.get(req.db, post.user_id)
        post.attachments = list(Attachment.list(req.db, post.id))
    return posts, pager, etag


@app.route("/<lang:lang>/<section_path>", method=state.METHOD_POST)
@auth_user()
def create_topic(req, lang: str, section_path: str):
    """Create new topic."""
    section = Section.find(req.db, lang, section_path)
    if not section:
        abort(state.HTTP_NOT_FOUND)
    if section.state == Section.State.ARCHIVED:
        abort(state.HTTP_GONE)
    # Only moderator can create topic in Locked section
    if section.state == Section.State.LOCKED and not req.user.is_moderator():
        abort(state.HTTP_FORBIDDEN)

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

    redirect(f"/{lang}/{section_path}/{topic.path}")


@app.route("/<lang:lang>/<section_path>/<topic_path>/rss")
@check_login_cookie
def topic_rss(req, lang: str, section_path: str, topic_path: str):
    """Return RSS feed with topic's last posts."""
    section, topic = find_topic(req.db, lang, section_path, topic_path,
                                req.user)

    total = Post.count(req.db, topic.id)
    pager = Pager(offset=max(0, total - RSS_ITEMS), limit=RSS_ITEMS)
    posts = list(Post.list(req.db, pager, topic_id=topic.id))
    posts.reverse()
    for post in posts:
        post.user = User.get(req.db, post.user_id)

    topic_url = req.construct_url(f"/{lang}/{section_path}/{topic_path}")
    return rss_response("rss/topic.xml", req,
                        section=section, topic=topic, posts=posts,
                        topic_url=topic_url, lang=lang)


@app.route("/<lang:lang>/<section_path>/<topic_path>")
@check_login_cookie
def topic_detail(req, lang: str, section_path: str, topic_path: str):
    """Return section detail."""
    section, topic = find_topic(req.db, lang, section_path, topic_path,
                                req.user)
    posts, pager, etag = topic_page(req, topic.id, check=True)

    return Response(render_response("topic.html",
                                    req,
                                    section=section,
                                    topic=topic,
                                    posts=posts,
                                    pager=pager),
                    headers={"ETag": etag})
