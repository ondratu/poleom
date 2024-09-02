"""Endpoints for posts."""
from poorwsgi import state
from poorwsgi.response import JSONResponse, RedirectResponse, abort

from .lib.auth import auth_user
from .lib.core import Request, app
from .lib.exceptions import FormError
from .lib.pager import Pager
from .lib.post import Post
from .lib.view import render_template
from .topic import ITEMS_ON_PAGE, find_topic, topic_page


@app.route("/s/<section_path>/<topic_path>", method=state.METHOD_POST)
@auth_user
def create_post(req, section_path: str, topic_path: str):
    """Create post in topic."""
    section, topic = find_topic(req.db, section_path, topic_path)

    parent = req.form.get("parent", "").strip() or None
    body = req.form.get("body", "").strip()

    if not body:
        errors = {"body": FormError.MISSING}
        posts, pager = topic_page(req, topic.id)
        # pylint: disable=duplicate-code

        return render_template("topic.html",
                               user=req.user,
                               section=section,
                               topic=topic,
                               posts=posts,
                               pager=pager,
                               errors=errors,
                               parent=parent,
                               body=body)

    pager = Pager(limit=ITEMS_ON_PAGE)
    pager.bind(req.args)

    post = Post.create(req.db, topic.id, req.user.id, body, parent)
    pager.total = Post.count(req.db, topic.id)
    return RedirectResponse(
        f"/s/{section_path}/{topic_path}?offset={pager.last}#{post.hexdigest}")


@app.route("/s/<section_path>/<topic_path>/<hexdigest>",
           method=state.METHOD_GET)
@auth_user
def form_post(req, section_path: str, topic_path: str, hexdigest: str):
    """Create post in topic."""
    post = Post.find(req.db, hexdigest)
    if not post:
        abort(state.HTTP_NOT_FOUND)
    elif req.user.id != post.user_id:
        abort(state.HTTP_FORBIDDEN)

    section, topic = find_topic(req.db, section_path, topic_path)
    return render_template("post_form.html",
                           section=section,
                           topic=topic,
                           post=post)


@app.route("/s/<section_path>/<topic_path>/<hexdigest>",
           method=state.METHOD_POST)
@auth_user
def update_post(req, section_path: str, topic_path: str, hexdigest: str):
    """Update post."""
    post = Post.find(req.db, hexdigest)
    if post.user_id != req.user.id:
        abort(state.HTTP_FORBIDDEN)

    offset = req.args.getfirst("offset", 0, int)
    offset = f"?offset={offset}" if offset else ""

    post.body = req.form.get("body", "").strip()
    section, topic = find_topic(req.db, section_path, topic_path)

    if not post.body:
        errors = {"body": FormError.MISSING}

        return render_template("post_form.html",
                               section=section,
                               topic=topic,
                               post=post,
                               offset=offset,
                               errors=errors)

    post.update(req.db)
    return RedirectResponse(
            f"/s/{section_path}/{topic_path}{offset}#{hexdigest}")


@app.route("/p/<hexdigest:hex>")
@auth_user
def get_post(req: Request, hexdigest: str):
    """Return post data identify by hexdigest for reply."""
    post = Post.find(req.db, hexdigest)
    if not post:
        abort(state.HTTP_NOT_FOUND)

    post_dict = post.to_dict()
    post_dict["created"] = int(post_dict["created"].timestamp())
    return JSONResponse(post=post_dict)
