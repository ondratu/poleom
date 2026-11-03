"""Fixtures with in-memory SQLite database."""
from importlib.resources import files
from os.path import join
from sqlite3 import connect, register_adapter

import pytest

from poleom.lib.section import Section
from poleom.lib.sqlite import Connection, Cursor
from poleom.lib.topic import Topic
from poleom.lib.user import User

SQL_INIT = join(str(files("poleom")), "sqlite", "init.sql")


@pytest.fixture(autouse=True, scope="session")
def _sqlite_adapters():
    """Enums are converted for MySQL by DB_CONV, register them for SQLite."""
    for enum in (User.State, User.Role, Section.State, Topic.State):
        register_adapter(enum, lambda item: item.name)


@pytest.fixture
def db():
    conn = connect(":memory:", factory=Connection)
    with conn.cursor(Cursor) as cur:
        with open(SQL_INIT, encoding="utf-8") as sql:
            cur.executescript(sql.read())
        conn.commit()
    return conn
