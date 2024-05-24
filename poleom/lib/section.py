"""Section record model"""
from dataclasses import dataclass

from MySQLdb import IntegrityError  # type: ignore[import-untyped]
from MySQLdb.connections import Connection  # type: ignore[import-untyped]
from MySQLdb.cursors import DictCursor  # type: ignore[import-untyped]

from .exceptions import MYSQL_DUPLICITY, DuplicityError


@dataclass
class Section:
    """Section record model class."""
    ROOT_ID = 1  # Root section

    _id: int
    title: str
    description: str

    @property
    def id(self):
        """Section.id is read only."""
        return self._id

    def dict(self):
        """Return dictionary from instance.

        It uses only databases row values.
        """
        return {
            "id": self._id,
            "title": self.title,
            "description": self.description,
        }

    @staticmethod
    def create(conn: Connection, title: str, description: str):
        """Create new section in db."""
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sections (title, description)
                    VALUES (%(title)s, %(description)s)
                """, {
                        "title": title,
                        "description": description,
                    })
                _id = cur.lastrowid
                conn.commit()
                return Section(_id, title, description)
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
            return Section(_id, row["title"], row["description"])

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
            return Section(row["section_id"], row["title"], row["description"])

    @staticmethod
    def delete(conn: Connection, _id: int):
        """Delete existing section in db."""
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sections WHERE section_id=%(id)s",
                        {"id": _id})

    def update(self, conn: Connection):
        """Update existing section in db."""
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE sections SET
                    title=%(title)s, description=%(description)s
                WHERE section_id = %(id)s
            """, self.dict())

    @staticmethod
    def list(conn: Connection):
        """Get list of sections from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute("SELECT * FROM sections")
            for row in cur:
                yield Section(row["section_id"], row["title"],
                              row["description"])

    @staticmethod
    def count(conn: Connection):
        """Return total count of sections in db."""
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sections")
            return cur.fetchone()[0]
