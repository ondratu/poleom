"""Unit tests for the MySQL value converters."""
from datetime import UTC, datetime, timedelta, timezone

from poleom.lib.mysql import DB_CONV, as_utc, dict2str, enum2str
from poleom.lib.user import User


def test_dict2str():
    # MySQL string literal, double quotes are escaped as well
    assert dict2str({"a": 1}, None) == b"'{\\\"a\\\": 1}'"


def test_dict2str_escapes_quotes():
    assert b"it\\'s" in dict2str({"a": "it's"}, None)


def test_enum2str():
    assert enum2str(User.Role.ADMIN, None) == b"'ADMIN'"


def test_converters_are_registered():
    assert DB_CONV[dict] is dict2str
    assert DB_CONV[User.State] is enum2str
    assert DB_CONV[User.Role] is enum2str


class TestAsUtc:
    """The database returns naive datetime in UTC."""

    def test_none(self):
        assert as_utc(None) is None

    def test_naive_is_utc(self):
        value = as_utc(datetime(2026, 1, 1, 12))
        assert value == datetime(2026, 1, 1, 12, tzinfo=UTC)
        assert value.utcoffset() == timedelta(0)

    def test_aware_is_converted(self):
        plus_two = timezone(timedelta(hours=2))
        value = as_utc(datetime(2026, 1, 1, 12, tzinfo=plus_two))
        assert value == datetime(2026, 1, 1, 10, tzinfo=UTC)
        assert value.utcoffset() == timedelta(0)
