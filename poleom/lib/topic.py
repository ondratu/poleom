"""Topic record model."""
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from MySQLdb import IntegrityError
from MySQLdb.connections import Connection

from .exceptions import MYSQL_DUPLICITY, DuplicityError
from .mysql import DB_CONV, DictCursor, enum2str
from .pager import Pager


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
    path: str
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
            "path": self.path,
            "state": self.state,
            "pinned": self.pinned,
        }

    @staticmethod
    def from_row(row):
        """Return section entity from DB row."""
        return Topic(row["topic_id"], row["section_id"], row["title"],
                     row["path"], Topic.State(row["state"]), row["pinned"])

    @staticmethod
    def create(conn: Connection, section_id: int, title: str,
               state: State = State.OPEN, pinned: bool = False):
        """Create new topic in db."""
        path = re.sub(r"\W+", "-", title.lower()).strip("-")
        topic = Topic(0, section_id, title, path, state, pinned)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO topics
                        (section_id, title, path, state, pinned)
                    VALUES (%(section_id)s, %(title)s, %(path)s, %(state)s,
                        %(pinned)s)
                """, topic.to_dict())
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
    def find(conn: Connection, section_id: int, path: str):
        """Found item by title."""
        with conn.cursor(DictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM topics
                WHERE section_id=%(section_id)s AND path=%(path)s
                """, {"section_id": section_id, "path": path})
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

        sql = ",".join(f"{col}=%({col})s" for col in cols)

        with conn.cursor() as cur:
            # ruff: noqa: S608
            cur.execute(
                f"UPDATE topics SET {sql} WHERE topic_id = %(id)s", vals)

    @staticmethod
    def list(conn: Connection, pager: Pager, section_id: int):
        """Get list of topics from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute(
                "SET sql_mode="
                "(SELECT REPLACE(@@sql_mode,'ONLY_FULL_GROUP_BY',''))")
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


DB_CONV[Topic.State] = enum2str
