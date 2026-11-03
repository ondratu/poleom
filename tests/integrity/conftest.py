"""Fixtures with in-memory SQLite database."""
from importlib.resources import files
from os.path import join
from sqlite3 import connect

import pytest

from poleom.lib.sqlite import Connection, Cursor

SQL_INIT = join(str(files("poleom")), "sqlite", "init.sql")


@pytest.fixture
def db():
    conn = connect(":memory:", factory=Connection)
    with conn.cursor(Cursor) as cur:
        with open(SQL_INIT, encoding="utf-8") as sql:
            cur.executescript(sql.read())
        conn.commit()
    return conn
