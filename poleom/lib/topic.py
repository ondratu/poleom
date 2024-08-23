"""Topic record model."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from MySQLdb import IntegrityError  # type: ignore[import-untyped]
from MySQLdb.connections import Connection  # type: ignore[import-untyped]
from MySQLdb.cursors import DictCursor  # type: ignore[import-untyped]

from .exceptions import MYSQL_DUPLICITY, DuplicityError
from .pager import Pager

# pylint: disable=duplicate-code


@dataclass
class Topic:
    """Topic record model class."""
    # pylint: disable=too-many-instance-attributes

    class State(Enum):
        """Topic state enum."""
        OPEN = "OPEN"
        LOCKED = "LOCKED"
        ARCHIVED = "ARCHIVED"

    _id: int
    section_id: int
    title: str
    state: State = State.OPEN
    pinned: bool = False
    count: int = field(init=False, default=0)
    last: datetime | None = field(init=False)
    user_name: str | None = field(init=False)

    @property
    def id(self):
        """Topic.id is read only."""
        return self._id

    def to_dict(self):
        """Return dictionary from instance.

        It uses only databases row values.
        """
        return {
            "id": self._id,
            "section_id": self.section_id,
            "title": self.title,
            "state": self.state,
            "pinned": self.pinned,
        }

    @staticmethod
    def from_row(row):
        """Return section entity from DB row."""
        return Topic(row["topic_id"], row["section_id"], row["title"],
                     Topic.State(row["state"]), row["pinned"])

    @staticmethod
    def create(conn: Connection, section_id: int, title: str,
               state: State = State.OPEN, pinned: bool = False):
        """Create new topic in db."""
        topic = Topic(0, section_id, title, state, pinned)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO topics (section_id, title, state, pinned)
                    VALUES (%(section_id)s, %(title)s, %(state)s, %(pinned)s)
                """, dict(topic.to_dict(), state=topic.state.value))
                topic._id = cur.lastrowid  # pylint: disable=protected-access
                conn.commit()
                return topic
        except IntegrityError as err:
            if err.args[0] == MYSQL_DUPLICITY:
                raise DuplicityError from err
            raise

    @staticmethod
    def get(conn: Connection, _id: int):
        """Get topic record from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute("SELECT * FROM topics WHERE topic_id=%(id)s",
                        {"id": _id})
            row = cur.fetchone()
            if not row:
                return None
            return Topic.from_row(row)

    @staticmethod
    def find(conn: Connection, section_id: int, title: str):
        """Found item by title."""
        with conn.cursor(DictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM topics
                WHERE section_id=%(section_id)s AND title=%(title)s
                """, {"section_id": section_id, "title": title})
            row = cur.fetchone()
            if not row:
                return None
            return Topic.from_row(row)

    @staticmethod
    def delete(conn: Connection, _id: int):
        """Delete existing topic in db."""
        with conn.cursor() as cur:
            cur.execute("DELETE FROM topics WHERE topic_id=%(id)s",
                        {"id": _id})

    def update(self, conn: Connection):
        """Update existing topic in db."""
        cols = ["title", "state", "pinned"]
        vals = self.to_dict()
        vals["state"] = self.state.value

        sql = ",".join(f"{col}=%({col})s" for col in cols)

        with conn.cursor() as cur:
            # ruff: noqa: S608
            cur.execute(
                f"UPDATE topics SET {sql} WHERE topic_id = %(id)s", vals)

    @staticmethod
    def list(conn: Connection, pager: Pager, section_id: int):
        """Get list of topics from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute("""
                SELECT *, COUNT(P.topic_id) AS count, MAX(P.created) AS last,
                    U.name
                FROM topics AS T
                    LEFT JOIN posts AS P ON (P.topic_id = T.topic_id)
                    LEFT JOIN users AS U ON (U.user_id = P.user_id)
                WHERE section_id=%(section_id)s
                GROUP BY T.topic_id
                LIMIT %(OFFSET)s, %(LIMIT)s
            """, dict(pager.sql_dict(), section_id=section_id))
            for row in cur:
                topic = Topic.from_row(row)
                topic.count = row["count"]
                topic.last = row["last"]
                topic.user_name = row["U.name"]
                yield topic

            cur.execute("""
                SELECT COUNT(*) AS count FROM topics
                WHERE section_id=%(section_id)s
            """, {"section_id": section_id})
            pager.total = cur.fetchone()["count"]
