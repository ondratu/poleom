"""Unit tests for the HTTP cache helpers of lib/response.py."""
import pytest
from poorwsgi.headers import Headers, time_to_http
from poorwsgi.response import HTTPException

from poleom.lib.response import check_etag, check_modified, create_etag

NOT_MODIFIED = 304


def test_etag_is_weak():
    etag = create_etag(1700000000)
    assert etag.startswith('W/"')
    assert etag.endswith('"')


def test_etag_is_stable():
    assert create_etag(1700000000, 5) == create_etag(1700000000, 5)


def test_etag_depends_on_time_and_user():
    base = create_etag(1700000000, 5)
    assert create_etag(1700000001, 5) != base
    assert create_etag(1700000000, 6) != base
    assert create_etag(1700000000) != base


def test_check_etag_match():
    etag = create_etag(1700000000)
    headers = Headers({"If-None-Match": etag})
    with pytest.raises(HTTPException) as err:
        check_etag(headers, etag)
    assert err.value.status_code == NOT_MODIFIED


def test_check_etag_differs():
    headers = Headers({"If-None-Match": 'W/"other"'})
    check_etag(headers, create_etag(1700000000))


def test_check_etag_without_header():
    check_etag(Headers(), create_etag(1700000000))


def test_check_modified_not_changed():
    headers = Headers({"If-Modified-Since": time_to_http(1700000000)})
    with pytest.raises(HTTPException) as err:
        check_modified(headers, 1700000000)
    assert err.value.status_code == NOT_MODIFIED


def test_check_modified_changed():
    headers = Headers({"If-Modified-Since": time_to_http(1700000000)})
    check_modified(headers, 1700000100)


def test_check_modified_without_header():
    check_modified(Headers(), 1700000000)
