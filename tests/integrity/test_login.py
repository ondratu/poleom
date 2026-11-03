"""Integrity tests for login functionality."""
from unittest.mock import patch

from poleom.lib.sqlite import DictCursor
from poleom.lib.user import User

PASSWORD = "Str0ngPassw0rd"


@patch("poleom.lib.user.DictCursor", DictCursor)
class TestLogin:
    """Tests for User.find() and User.update()."""

    def test_unknown_email(self, db):
        assert User.find(db, "unknown@localhost") is None

    def test_no_password_check(self, db):
        user = User.find(db, "root@localhost")
        assert user is not None
        assert user.role == User.Role.ADMIN

    def test_bad_pass(self, db):
        user = User.find(db, "root@localhost")
        user.update(db, password=PASSWORD)
        assert User.find(db, "root@localhost", "bad-password") is None

    def test_login(self, db):
        user = User.find(db, "root@localhost")
        user.update(db, password=PASSWORD)
        assert User.find(db, "root@localhost", PASSWORD) is not None

    def test_empty_password_in_db(self, db):
        """User without password in DB can not log in."""
        assert User.find(db, "root@localhost", PASSWORD) is None
