"""Integrity tests of the section models with SQLite database."""
from unittest.mock import patch

import pytest

from poleom.lib.section import Section, SectionUser
from poleom.lib.sqlite import DictCursor
from poleom.lib.user import User


@pytest.fixture(autouse=True)
def sqlite_cursor():
    with patch("poleom.lib.section.DictCursor", DictCursor):
        yield


def make_user(db, name, role):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (name, email, password, state, role, data)
            VALUES (%(name)s, %(email)s, '', 'ACTIVE', %(role)s, '{}')
            """, {"name": name, "email": f"{name}@example.com",
                  "role": role})
        db.commit()
        user_id = cur.lastrowid
    with patch("poleom.lib.user.DictCursor", DictCursor):
        return User.get(db, user_id)


def test_get_and_find_default_section(db):
    section = Section.find(db, "en", "general")
    assert section is not None
    assert section.title == "General"
    assert Section.get(db, section.id) == section


def test_get_and_find_missing(db):
    assert Section.get(db, 9999) is None
    assert Section.find(db, "en", "missing") is None


def test_total(db):
    assert Section.total(db) == 10


def test_create_sets_id_and_weight(db):
    section = Section(0, "New Section", "en", "Description")
    section.create(db)

    assert section.id > 0
    stored = Section.get(db, section.id)
    assert stored is not None
    assert stored.path == "new-section"
    assert stored.weight == section.id


def test_update(db):
    section = Section.find(db, "en", "ideas")
    assert section is not None
    section.title = "Better ideas"
    section.state = Section.State.LOCKED
    section.update(db)

    stored = Section.get(db, section.id)
    assert stored is not None
    assert stored.title == "Better ideas"
    assert stored.state is Section.State.LOCKED


def test_delete(db):
    section = Section.find(db, "en", "ideas")
    assert section is not None
    Section.delete(db, section.id)
    assert Section.get(db, section.id) is None


def test_swap_down_and_up(db):
    first = Section.find(db, "en", "general")
    second = Section.find(db, "en", "ideas")
    assert first is not None
    assert second is not None
    assert first.weight < second.weight

    assert first.swap(db, 1)

    new_first = Section.get(db, first.id)
    new_second = Section.get(db, second.id)
    assert new_first is not None
    assert new_second is not None
    assert new_first.weight == second.weight
    assert new_second.weight == first.weight

    assert new_first.swap(db, -1)
    assert Section.get(db, first.id) == first


def test_swap_at_the_end_does_nothing(db):
    last = Section.find(db, "cs", "pochlub-se")
    assert last is not None
    assert not last.swap(db, 1)


def test_has_access_public(db):
    section = Section.find(db, "en", "general")
    assert section is not None
    assert section.has_access(db, None)


def test_has_access_private(db):
    section = Section(0, "Secret", "en", "Private", private=True)
    section.create(db)
    member = make_user(db, "member", "MEMBER")
    other = make_user(db, "other", "MEMBER")
    admin = make_user(db, "boss", "ADMIN")

    assert not section.has_access(db, None)
    assert not section.has_access(db, member)
    assert section.has_access(db, admin)

    SectionUser.add(db, section.id, member.id)
    assert section.has_access(db, member)
    assert not section.has_access(db, other)


def test_section_users(db):
    section = Section.find(db, "en", "general")
    assert section is not None
    member = make_user(db, "member", "MEMBER")

    assert not SectionUser.user_in(db, section.id, member.id)
    SectionUser.add(db, section.id, member.id)
    assert SectionUser.user_in(db, section.id, member.id)
    assert list(SectionUser.list(db, section.id)) == [
        {"user_id": member.id, "name": "member"}]

    SectionUser.remove(db, section.id, member.id)
    assert not SectionUser.user_in(db, section.id, member.id)
    assert not list(SectionUser.list(db, section.id))
