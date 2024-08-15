"""Endpoints for posts."""
from urllib import parse

from poorwsgi import state
from poorwsgi.response import JSONResponse, abort, redirect

from .lib.auth import auth_user
from .lib.core import app
from .lib.post import Post
from .topics import find_topic


@app.route("/s/<section_title>/<topic_title>", method=state.METHOD_POST)
@auth_user
def create_post(req, section_title: str, topic_title: str):
    """Return section detail."""
    _, topic = find_topic(req.db, section_title, topic_title)

    parent = req.form.get("parent", "").strip() or None
    body = req.form.get("body", "").strip()
    uri = parse.urlparse(req.referer)

    if not body:
        redirect(uri._replace(fragment="empty_topic_body").geturl())

    post = Post.create(req.db, topic.id, req.user.id, body, parent)
    redirect(uri._replace(fragment=post.hexdigest).geturl())


@app.route("/p/<hexdigest>")
@auth_user
def get_post(req, hexdigest: str):
    """Return post data identify by hexdigest."""
    post = Post.find(req.db, hexdigest)
    if not post:
        abort(state.HTTP_NOT_FOUND)
    post_dict = post.dict()
    post_dict["created"] = int(post_dict["created"].timestamp())
    return JSONResponse(post=post_dict)
