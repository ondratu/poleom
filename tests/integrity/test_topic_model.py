"""Integrity tests of the topic model with SQLite database."""
from unittest.mock import patch

import pytest

from poleom.lib.section import Section
from poleom.lib.sqlite import DictCursor
from poleom.lib.topic import Topic


@pytest.fixture(autouse=True)
def sqlite_cursor():
    with patch("poleom.lib.topic.DictCursor", DictCursor):
        yield


@pytest.fixture
def section(db):
    with patch("poleom.lib.section.DictCursor", DictCursor):
        found = Section.find(db, "en", "general")
    assert found is not None
    return found


def test_create_builds_path_from_title(db, section):
    topic = Topic.create(db, section.id, "Hello, World!")

    assert topic.id > 0
    assert topic.path == "hello-world"
    assert topic.state is Topic.State.OPEN
    assert not topic.pinned


def test_get_and_find(db, section):
    topic = Topic.create(db, section.id, "First topic")

    # Topic has no __eq__ usable before it is listed (last is not set)
    for found in (Topic.get(db, topic.id),
                  Topic.find(db, section.id, "first-topic")):
        assert found is not None
        assert found.to_dict() == topic.to_dict()


def test_get_and_find_missing(db, section):
    assert Topic.get(db, 9999) is None
    assert Topic.find(db, section.id, "missing") is None


def test_find_is_limited_to_section(db, section):
    Topic.create(db, section.id, "First topic")

    assert Topic.find(db, section.id + 1, "first-topic") is None


def test_update(db, section):
    topic = Topic.create(db, section.id, "First topic")
    topic.title = "Renamed topic"
    topic.state = Topic.State.LOCKED
    topic.pinned = True
    topic.update(db)

    stored = Topic.get(db, topic.id)
    assert stored is not None
    assert stored.title == "Renamed topic"
    assert stored.state is Topic.State.LOCKED
    assert stored.pinned
    assert stored.path == "first-topic"


def test_delete(db, section):
    topic = Topic.create(db, section.id, "First topic")
    Topic.delete(db, topic.id)

    assert Topic.get(db, topic.id) is None
