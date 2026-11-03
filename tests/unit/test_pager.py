"""Unit tests for the Pager."""
from types import SimpleNamespace

from poorwsgi.request import Args

from poleom.lib.pager import Pager


def args(query: str) -> Args:
    """Return parsed query string as request arguments."""
    return Args(SimpleNamespace(query=query))  # type: ignore[arg-type]


def test_defaults():
    pager = Pager()
    assert (pager.offset, pager.limit, pager.order, pager.sort) == \
        (0, 10, "", "asc")
    assert pager.total == 0
    assert pager.params == ""


def test_pages():
    pager = Pager(limit=10)
    pager.total = 25
    assert pager.pages == 2
    assert pager.last == 20


def test_pages_exact_multiple():
    pager = Pager(limit=10)
    pager.total = 20
    assert pager.pages == 1
    assert pager.last == 10


def test_page():
    pager = Pager(offset=30, limit=10)
    assert pager.page == 3


def test_bind():
    pager = Pager()
    pager.bind(args("offset=20&limit=5&order=name&sort=desc"))
    assert (pager.offset, pager.limit, pager.order, pager.sort) == \
        (20, 5, "name", "desc")


def test_bind_keeps_defaults():
    pager = Pager(offset=3, limit=7, order="id")
    pager.bind(args(""))
    assert (pager.offset, pager.limit, pager.order, pager.sort) == \
        (3, 7, "id", "asc")


def test_bind_ignores_invalid_sort():
    pager = Pager()
    pager.bind(args("sort=DROP+TABLE"))
    assert pager.sort == "asc"


def test_set_params():
    pager = Pager()
    pager.set_params(q="abc", lang="en")
    assert pager.params == "q=abc&lang=en"


def test_sql_dict():
    pager = Pager(offset=10, limit=5)
    assert pager.sql_dict() == {"OFFSET": 10, "LIMIT": 5}
