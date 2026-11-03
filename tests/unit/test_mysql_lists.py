"""Unit tests of the listings which use MySQL only SQL.

SQLite cannot run these queries, so the cursor is mocked and the tests
check the processing of the rows.
"""
from unittest.mock import MagicMock

from poleom.lib.pager import Pager
from poleom.lib.section import Section
from poleom.lib.topic import Topic


def conn_with(rows, fetchone=None):
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.__iter__.return_value = iter(rows)
    cursor.fetchone.return_value = fetchone
    return conn, cursor


def test_section_list():
    row = {"section_id": 1, "title": "General", "lang": "en",
           "description": "d", "state": "OPEN", "private": 0,
           "path": "general", "weight": 1, "count": 5}
    conn, cursor = conn_with([row])

    sections = list(Section.list(conn, "en", 3))

    assert [(s.title, s.count) for s in sections] == [("General", 5)]
    assert cursor.execute.call_count == 2  # sql_mode and the query
    assert "SU.user_id = %(user_id)s" in cursor.execute.call_args.args[0]


def test_section_list_without_user():
    conn, cursor = conn_with([])

    assert not list(Section.list(conn, "en"))
    assert "SU.user_id =" not in cursor.execute.call_args.args[0]


def test_topic_list():
    row = {"topic_id": 1, "section_id": 2, "title": "Topic",
           "path": "topic", "state": "OPEN", "pinned": 0, "count": 4,
           "last": "2026-01-01", "U.name": "alice"}
    conn, _ = conn_with([row], {"count": 9})
    pager = Pager()

    topics = list(Topic.list(conn, pager, 2))

    assert [(t.title, t.count, t.user_name) for t in topics] == [
        ("Topic", 4, "alice")]
    assert pager.total == 9


def test_topic_list_order():
    conn, cursor = conn_with([], {"count": 0})
    pager = Pager()
    pager.order = "title"
    pager.sort = "desc"

    assert not list(Topic.list(conn, pager, 2))
    assert "ORDER BY title DESC" in cursor.execute.call_args_list[1].args[0]
