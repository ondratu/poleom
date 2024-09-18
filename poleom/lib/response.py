"""Response utils"""
from hashlib import sha256

from poorwsgi.headers import Headers, http_to_time, time_to_http
from poorwsgi.response import HTTPException, NotModifiedResponse

from .core import Request
from .settings import Language
from .view import render_template


def create_etag(last_modified: int, user_id: int | None = None):
    """Create E-Tag header value from last modified timestamp."""
    bdata = last_modified.to_bytes(4, "big")
    if user_id is not None:
        bdata += user_id.to_bytes(4, "big")

    weak = sha256(bdata).hexdigest()[:10]
    return f'W/"{weak}"'


def check_etag(headers: Headers, etag: str):
    """ Raise HTTPException with NotModifiedResponse if etag is same."""
    if etag == headers.get("If-None-Match"):
        raise HTTPException(NotModifiedResponse(etag=etag))


def check_modified(headers: Headers, last_modified: int):
    """ Raise HTTPException with NotModifiedResponse if last_modified is same.
    """
    if "If-Modified-Since" in headers:
        if_modified = http_to_time(headers.get("If-Modified-Since", ""))
        if last_modified <= if_modified:
            raise HTTPException(NotModifiedResponse(date=time_to_http()))


def render_response(template: str, req: Request, **kwargs):
    """Call render template and add some aditional values from request.

    It sets / fill next attributes
    * me from req.user
    * lang from section.lang or req.lang
    * languages from DB if is not set
    """
    kwargs["me"] = req.user
    lang = kwargs["section"].lang if "section" in kwargs else req.lang
    kwargs["lang"] = lang
    if "languages" not in kwargs:
        kwargs["languages"] = Language.map(req.db)

    return render_template(template, **kwargs)
