"""Integrity tests of the User model with SQLite database."""
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
