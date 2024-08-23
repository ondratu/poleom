"""Section record model"""
from dataclasses import dataclass, field
from enum import Enum

from MySQLdb import IntegrityError  # type: ignore[import-untyped]
from MySQLdb.connections import Connection  # type: ignore[import-untyped]
from MySQLdb.cursors import DictCursor  # type: ignore[import-untyped]

from .exceptions import MYSQL_DUPLICITY, DuplicityError

# pylint: disable=duplicate-code


@dataclass
class Section:
    """Section record model class."""

    class State(Enum):
        """Section state enum."""
        OPEN = "OPEN"
        LOCKED = "LOCKED"
        ARCHIVED = "ARCHIVED"

    _id: int
    title: str
    description: str
    state: State = State.OPEN
    private: bool = False
    count: int = field(init=False, default=0)

    @property
    def id(self):
        """Section.id is read only."""
        return self._id

    def to_dict(self):
        """Return dictionary from instance.

        It uses only databases row values.
        """
        return {
            "id": self._id,
            "title": self.title,
            "description": self.description,
            "state": self.state,
            "private": self.private,
        }

    @staticmethod
    def from_row(row):
        """Return section entity from DB row."""
        return Section(row["section_id"], row["title"], row["description"],
                       Section.State(row["state"]), row["private"])

    @staticmethod
    def create(conn: Connection, title: str, description: str,
               state: State = State.OPEN, private: bool = False):
        """Create new section in db."""
        section = Section(0, title, description, state, private)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sections (title, description, state, private)
                    VALUES (%(title)s, %(description)s, %(state)s, %(private)s)
                """, dict(section.to_dict(), state=section.state.value))
                section._id = cur.lastrowid  # pylint: disable=protected-access
                conn.commit()
                return section
        except IntegrityError as err:
            if err.args[0] == MYSQL_DUPLICITY:
                raise DuplicityError from err
            raise

    @staticmethod
    def get(conn: Connection, _id: int):
        """Get section record from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute("SELECT * FROM sections WHERE section_id=%(id)s",
                        {"id": _id})
            row = cur.fetchone()
            if not row:
                return None
            return Section.from_row(row)

    @staticmethod
    def find(conn: Connection, title: str):
        """Found item by title."""
        with conn.cursor(DictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM sections WHERE title=%(title)s
                """, {"title": title})
            row = cur.fetchone()
            if not row:
                return None
            return Section.from_row(row)

    @staticmethod
    def delete(conn: Connection, _id: int):
        """Delete existing section in db."""
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sections WHERE section_id=%(id)s",
                        {"id": _id})

    def update(self, conn: Connection):
        """Update existing section in db."""
        cols = ["title", "description", "state", "private"]
        vals = self.to_dict()
        vals["state"] = self.state.value

        sql = ",".join(f"{col}=%({col})s" for col in cols)

        with conn.cursor() as cur:
            # ruff: noqa: S608
            cur.execute(
                f"UPDATE sections SET {sql} WHERE section_id = %(id)s", vals)

    @staticmethod
    def list(conn: Connection):
        """Get list of sections from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute("""
                SELECT *, count(T.section_id) AS count FROM sections AS S
                    LEFT JOIN topics AS T ON (T.section_id = S.section_id)
                GROUP BY S.section_id
            """)
            for row in cur:
                section = Section.from_row(row)
                section.count = row["count"]
                yield section

    @staticmethod
    def total(conn: Connection):
        """Return total count of sections in db."""
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sections")
            return cur.fetchone()[0]
