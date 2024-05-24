"""Endpoints for posts."""
from urllib import parse

from poorwsgi import state
from poorwsgi.response import redirect

from .lib.auth import auth_user
from .lib.core import app
from .lib.post import Post
from .topics import find_topic


@app.route("/s/<section_title>/<topic_title>", method=state.METHOD_POST)
@auth_user
def create_post(req, section_title: str, topic_title: str):
    """Return section detail."""
    _, topic = find_topic(req.db, section_title, topic_title)

    body = req.form.get("body", "").strip()
    uri = parse.urlparse(req.referer)

    if not body:
        redirect(uri._replace(fragment="empty_topic_body").geturl())

    post = Post.create(req.db, topic.id, req.user.id, body)
    redirect(uri._replace(fragment=post.hexdigest).geturl())
