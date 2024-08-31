"""Endpoints for posts."""
from urllib import parse

from poorwsgi import state
from poorwsgi.response import JSONResponse, abort, redirect

from .lib.auth import auth_user
from .lib.core import app
from .lib.post import Post
from .topic import find_topic


@app.route("/s/<section_path>/<topic_path>", method=state.METHOD_POST)
@auth_user
def create_post(req, section_path: str, topic_path: str):
    """Return section detail."""
    _, topic = find_topic(req.db, section_path, topic_path)

    parent = req.form.get("parent", "").strip() or None
    body = req.form.get("body", "").strip()
    uri = parse.urlparse(req.referer)

    if not body:
        redirect(uri._replace(fragment="empty_topic_body").geturl())

    post = Post.create(req.db, topic.id, req.user.id, body, parent)
    redirect(uri._replace(fragment=post.hexdigest).geturl())


@app.route("/p/<hexdigest:hex>")
@auth_user
def get_post(req, hexdigest: str):
    """Return post data identify by hexdigest."""
    post = Post.find(req.db, hexdigest)
    if not post:
        abort(state.HTTP_NOT_FOUND)
    post_dict = post.to_dict()
    post_dict["created"] = int(post_dict["created"].timestamp())
    return JSONResponse(post=post_dict)
