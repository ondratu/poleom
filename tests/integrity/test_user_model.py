"""Integrity tests of the User model with SQLite database."""
import pytest

from poleom.lib.auth_backend import Identity
from poleom.lib.exceptions import DuplicityError
from poleom.lib.pager import Pager
from poleom.lib.user import User

PASSWORD = "Str0ngPassw0rd"


def test_create_and_get(db):
    user = User.create(db, "Alice", "alice@example.com", PASSWORD, "sig")

    assert user.id > 0
    assert user.state is User.State.REGISTERED
    stored = User.get(db, user.id)
    assert stored is not None
    assert stored.to_dict() == user.to_dict()
    assert User.get(db, 9999) is None


def test_find_checks_password(db, make_user):
    user = make_user("alice")

    found = User.find(db, "alice@example.com", PASSWORD)
    assert found is not None
    assert found.id == user.id
    assert User.find(db, "alice@example.com") is not None
    assert User.find(db, "alice@example.com", "Wrong") is None
    assert User.find(db, "nobody@example.com", PASSWORD) is None


def test_find_user_without_password(db):
    """The default administrator has no password, nobody can log in."""
    assert User.find(db, "root@localhost", PASSWORD) is None


def test_update_changes_password(db, make_user):
    user = make_user("alice")
    user.name = "Alice B."
    user.update(db, "N3wPassw0rd")

    assert User.find(db, "alice@example.com", PASSWORD) is None
    found = User.find(db, "alice@example.com", "N3wPassw0rd")
    assert found is not None
    assert found.name == "Alice B."


def test_delete_anonymizes(db, make_user):
    user = make_user("alice", User.Role.MODERATOR)
    user.delete(db)

    stored = User.get(db, user.id)
    assert stored is not None
    assert stored.state is User.State.DELETED
    assert stored.role is User.Role.MEMBER
    assert stored.email == f"{user.id}@invalid"
    assert stored.name == f"Member {user.id}"
    assert User.find(db, "alice@example.com") is None


def test_list_and_count(db, make_user):
    make_user("alice")
    make_user("bob")

    assert User.count(db) == 3  # with default administrator
    pager = Pager()
    users = list(User.list(db, pager))
    assert [user.name for user in users] == ["Admin", "alice", "bob"]


def test_search(db, make_user):
    make_user("alice")
    bob = make_user("bob")
    bob.delete(db)

    assert [item["name"] for item in User.search(db, "ali")] == ["alice"]
    assert [item["name"] for item in User.search(db, "example")] == ["alice"]
    assert not list(User.search(db, "bob"))


def test_find_user_without_password_hash(db):
    """The user of the auth backend has no password, NULL in the database."""
    user = User.from_identity(db, Identity("1", "Ann", "ann@example.com"))

    assert User.find(db, user.email, PASSWORD) is None
    assert User.find(db, user.email) is not None  # without the password


def test_from_identity_creates_user(db):
    identity = Identity("sub-1", "Ann", "ann@example.com", "cs")

    user = User.from_identity(db, identity)

    assert user.id > 0
    assert user.state is User.State.ACTIVE
    assert user.role is User.Role.MEMBER
    assert user.auth_sub == "sub-1"
    assert user.data == {"lang": "cs"}
    assert User.get(db, user.id).to_dict() == user.to_dict()


def test_from_identity_without_lang(db):
    user = User.from_identity(db, Identity("1", "Ann", "ann@example.com"))

    assert not user.data


def test_from_identity_finds_user(db):
    first = User.from_identity(db, Identity("1", "Ann", "ann@example.com"))

    second = User.from_identity(db, Identity("1", "Ann", "ann@example.com"))

    assert second.id == first.id
    assert User.count(db) == 2  # the default administrator is the first


def test_from_identity_syncs_changes_and_keeps_local_data(db):
    user = User.from_identity(db, Identity("1", "Ann", "ann@example.com"))
    user.role = User.Role.MODERATOR
    user.state = User.State.BANNED
    user.data = {"theme": "dark"}
    user.update(db)

    changed = Identity("1", "Ann B.", "annb@example.com", "en")
    synced = User.from_identity(db, changed)

    stored = User.get(db, user.id)
    assert synced.id == user.id
    assert (stored.name, stored.email) == ("Ann B.", "annb@example.com")
    assert stored.data == {"theme": "dark", "lang": "en"}
    assert stored.role is User.Role.MODERATOR
    assert stored.state is User.State.BANNED


def test_from_identity_duplicate_email(db, make_user):
    make_user("ann")

    with pytest.raises(DuplicityError):
        User.from_identity(db, Identity("1", "Ann", "ann@example.com"))


def test_find_user_with_corrupted_password(db, make_user):
    user = make_user("alice")
    with db.cursor() as cur:
        cur.execute("UPDATE users SET password='corrupted' "
                    "WHERE user_id=%(id)s", {"id": user.id})

    assert User.find(db, "alice@example.com", PASSWORD) is None
