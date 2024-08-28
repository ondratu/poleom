"""Response utils"""
from hashlib import sha256

from poorwsgi.headers import Headers, http_to_time, time_to_http
from poorwsgi.response import HTTPException, NotModifiedResponse


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
