"""Topic record model."""
from dataclasses import dataclass, field

from MySQLdb import IntegrityError  # type: ignore[import-untyped]
from MySQLdb.connections import Connection  # type: ignore[import-untyped]
from MySQLdb.cursors import DictCursor  # type: ignore[import-untyped]

from .exceptions import MYSQL_DUPLICITY, DuplicityError
from .pager import Pager


@dataclass
class Topic:
    """Topic record model class."""
    _id: int
    section_id: int
    title: str
    count: int = field(init=False, default=0)

    @property
    def id(self):
        """Topic.id is read only."""
        return self._id

    def dict(self):
        """Return dictionary from instance.

        It uses only databases row values.
        """
        return {
            "id": self._id,
            "section_id": self.section_id,
            "title": self.title,
        }

    @staticmethod
    def create(conn: Connection, section_id: int, title: str):
        """Create new topic in db."""
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO topics (section_id, title)
                    VALUES (%(section_id)s, %(title)s)
                """, {
                        "section_id": section_id,
                        "title": title,
                    })
                _id = cur.lastrowid
                conn.commit()
                return Topic(_id, section_id, title)
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
            return Topic(_id, row["section_id"], row["title"])

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
            return Topic(row["topic_id"], row["section_id"], row["title"])

    @staticmethod
    def delete(conn: Connection, _id: int):
        """Delete existing topic in db."""
        with conn.cursor() as cur:
            cur.execute("DELETE FROM topics WHERE topic_id=%(id)s",
                        {"id": _id})

    def update(self, conn: Connection):
        """Update existing topic in db."""
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE sections SET
                    section_id=%(section_id)s, title=%(title)s
                WHERE topic_id = %(id)d
            """, self.dict())

    @staticmethod
    def list(conn: Connection, pager: Pager, section_id: int):
        """Get list of topics from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute("""
                SELECT *, count(P.topic_id) AS count FROM topics AS T
                    LEFT JOIN posts AS P ON (P.topic_id = T.topic_id)
                WHERE section_id=%(section_id)s
                GROUP BY T.topic_id
                LIMIT %(OFFSET)s, %(LIMIT)s
            """, dict(pager.sql_dict(), section_id=section_id))
            for row in cur:
                topic = Topic(row["topic_id"], row["section_id"], row["title"])
                topic.count = row["count"]
                yield topic

            cur.execute("""
                SELECT COUNT(*) AS count FROM topics
                WHERE section_id=%(section_id)s
            """, {"section_id": section_id})
            pager.total = cur.fetchone()["count"]
