"""RSS feed response helpers."""
from poorwsgi.response import Response

from .core import Request
from .view import render_template

RSS_ITEMS = 30
CONTENT_TYPE = "application/rss+xml; charset=utf-8"


def rss_response(template: str, req: Request, **kwargs):
    """Render RSS template and return it as application/rss+xml Response."""
    kwargs.setdefault("self_url", req.construct_url(req.path))
    return Response(render_template(template, **kwargs),
                    content_type=CONTENT_TYPE)
