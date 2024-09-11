"""Enpoints for attachments."""
from os import path

from poorwsgi import state
from poorwsgi.headers import parse_range, time_to_http
from poorwsgi.request import Request
from poorwsgi.response import FileResponse, NoContentResponse, abort

from .lib.attachment import Attachment
from .lib.auth import auth_user
from .lib.core import app
from .lib.post import Post
from .lib.response import check_etag, check_modified, create_etag


@app.route("/a/<hexdigest:hex>/<file_name>")
@app.route("/a/<hexdigest:hex>")
def get_attachment(req: Request, hexdigest: str, file_name: str = ""):
    """Return attachment."""
    attachment = Attachment.get(req.db, hexdigest)
    if not attachment or (file_name and file_name != attachment.file_name):
        abort(state.HTTP_NOT_FOUND)

    file_path = path.join(attachment.path, attachment.hexdigest)
    last_modified = int(path.getctime(file_path))
    etag = create_etag(last_modified)

    check_etag(req.headers, etag)
    check_modified(req.headers, last_modified)

    headers = {"E-Tag": etag, "Last-Modified": time_to_http(last_modified)}
    response = FileResponse(file_path, attachment.mime_type, headers)

    ranges = {}
    if "Range" in req.headers:
        ranges = parse_range(req.headers["Range"])
    response.make_partial(ranges.get("bytes", None))

    return response


@app.route("/a/<hexdigest:hex>", method=state.METHOD_DELETE)
@auth_user()
def delete_attachment(req, hexdigest: str):
    """Return attachment."""
    attachment = Attachment.get(req.db, hexdigest)
    if not attachment:
        abort(state.HTTP_NOT_FOUND)

    post = Post.get(req.db, attachment.post_id)
    if req.user.id != post.user_id:
        abort(state.HTTP_FORBIDDEN)

    Attachment.delete(req.db, hexdigest)
    return NoContentResponse()
