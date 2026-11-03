"""Unit tests for the MySQL value converters."""
from poleom.lib.mysql import DB_CONV, dict2str, enum2str
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
