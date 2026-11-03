"""Fixtures with in-memory SQLite database."""
import json
from contextlib import ExitStack
from datetime import datetime
from importlib.resources import files
from os.path import join
from sqlite3 import connect, register_adapter
from unittest.mock import patch

import pytest

from poleom.lib.change_request import ChangeRequest
from poleom.lib.section import Section
from poleom.lib.sqlite import Connection, Cursor, DictCursor
from poleom.lib.topic import Topic
from poleom.lib.user import User

SQL_INIT = join(str(files("poleom")), "sqlite", "init.sql")


@pytest.fixture(autouse=True, scope="session")
def _sqlite_adapters():
    """Enums are converted for MySQL by DB_CONV, register them for SQLite."""
    for enum in (User.State, User.Role, Section.State, Topic.State,
                 ChangeRequest.State):
        register_adapter(enum, lambda item: item.name)
    register_adapter(dict, json.dumps)  # JSON columns
    # the default adapter is deprecated
    register_adapter(datetime, lambda value: value.isoformat(" "))


@pytest.fixture
def db():
    conn = connect(":memory:", factory=Connection)
    with conn.cursor(Cursor) as cur:
        with open(SQL_INIT, encoding="utf-8") as sql:
            cur.executescript(sql.read())
        conn.commit()
    return conn


@pytest.fixture(autouse=True)
def sqlite_models():
    """Patch `DictCursor` of all models with the SQLite one."""
    with ExitStack() as stack:
        for module in ("attachment", "change_request", "post", "section",
                       "settings", "topic", "user"):
            stack.enter_context(
                patch(f"poleom.lib.{module}.DictCursor", DictCursor))
        yield


@pytest.fixture
def make_user(db):
    """Return function which creates an active user."""
    def create(name="member", role=User.Role.MEMBER,
               password="Str0ngPassw0rd"):
        user = User.create(db, name, f"{name}@example.com", password)
        user.state = User.State.ACTIVE
        user.role = role
        user.update(db)
        return user
    return create
