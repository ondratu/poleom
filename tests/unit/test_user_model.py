"""Unit tests for the User model."""
import json

import pytest

from poleom.lib.user import User

ROW = {
    "user_id": 7,
    "name": "Alice",
    "email": "alice@example.org",
    "signature": "Bye",
    "state": "ACTIVE",
    "role": "MODERATOR",
    "data": '{"theme": "dark"}',
    "auth_sub": "42",
}


def make_user(role=User.Role.MEMBER):
    return User(1, "Alice", "alice@example.org", None, User.State.ACTIVE,
                role)


@pytest.mark.parametrize("password", [
    "Abcdefgh12",  # lower, upper, digit, 10 chars
    "abcdefghi!",  # 10 chars with a non-alphanumeric one
    "abcdefghijklmno",  # 15 chars
])
def test_valid_password(password):
    assert User.VALID_PASSWORD_REGEX.match(password)


@pytest.mark.parametrize("password", [
    "",
    "Abcdefg12",  # 9 chars
    "abcdefghij",  # 10 lowercase chars only
    "ABCDEFGHIJ1",  # no lowercase letter
    "abcdefghijklmn",  # 14 chars only
])
def test_invalid_password(password):
    assert not User.VALID_PASSWORD_REGEX.match(password)


def test_from_row():
    user = User.from_row(ROW)
    assert user.id == 7
    assert user.name == "Alice"
    assert user.email == "alice@example.org"
    assert user.signature == "Bye"
    assert user.state is User.State.ACTIVE
    assert user.role is User.Role.MODERATOR
    assert user.data == {"theme": "dark"}
    assert user.auth_sub == "42"


def test_from_row_unknown_state():
    with pytest.raises(ValueError, match="UNKNOWN"):
        User.from_row(dict(ROW, state="UNKNOWN"))


def test_to_dict_roundtrip():
    user = User.from_row(ROW)
    values = user.to_dict()
    assert values["id"] == 7
    assert values["state"] is User.State.ACTIVE
    assert values["role"] is User.Role.MODERATOR
    assert json.loads(ROW["data"]) == values["data"]
    assert "password" not in values


def test_id_is_read_only():
    user = make_user()
    with pytest.raises(AttributeError):
        user.id = 2  # type: ignore[misc]


@pytest.mark.parametrize(("role", "moderator", "admin"), [
    (User.Role.MEMBER, False, False),
    (User.Role.MODERATOR, True, False),
    (User.Role.ADMIN, True, True),
])
def test_roles(role, moderator, admin):
    user = make_user(role)
    assert user.is_moderator() is moderator
    assert user.is_admin() is admin
