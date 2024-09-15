"""Section record model"""
import re
from dataclasses import dataclass, field
from enum import Enum

from MySQLdb import IntegrityError  # type: ignore[import-untyped]
from MySQLdb.connections import Connection  # type: ignore[import-untyped]

from .exceptions import MYSQL_DUPLICITY, DuplicityError
from .mysql import DB_CONV, DictCursor, enum2str
from .user import User

# pylint: disable=duplicate-code


@dataclass
class Section:
    """Section record model class."""
    # pylint: disable=too-many-instance-attributes

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
    path: str = ""
    weight: int = 0
    count: int = field(init=False, default=0)

    def __post_init__(self):
        if not self.path:
            self.path = re.sub(r"\W+", "-", self.title.lower()).strip("-")

    @staticmethod
    def from_row(row):
        """Return section entity from DB row."""
        return Section(row["section_id"], row["title"], row["description"],
                       Section.State(row["state"]), row["private"],
                       row["path"], row["weight"])

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
            "path": self.path,
            "description": self.description,
            "state": self.state,
            "weight": self.weight,
            "private": self.private,
        }

    def has_access(self, conn: Connection, user: User | None):
        """Return True if user has access to section."""
        if not self.private:
            return True
        # section is private
        if not user:
            return False
        return user.is_admin() or SectionUser.user_in(conn, self.id, user.id)

    def create(self, conn: Connection):
        """Create new section in db."""
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sections
                        (title, path, description, state, private, weight)
                    VALUES (%(title)s, %(path)s, %(description)s, %(state)s,
                            %(private)s, 0)
                    """, self.to_dict())
                self._id = cur.lastrowid  # pylint: disable=protected-access
                cur.execute("""
                    UPDATE sections SET weight=%(id)s WHERE section_id=%(id)s
                    """, {"id": self.id})
                conn.commit()
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
    def find(conn: Connection, path: str):
        """Found item by title."""
        with conn.cursor(DictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM sections WHERE path=%(path)s
                """, {"path": path})
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
        cols = ["title", "description", "path", "state", "private"]
        vals = self.to_dict()

        sql = ",".join(f"{col}=%({col})s" for col in cols)

        try:
            with conn.cursor() as cur:
                # ruff: noqa: S608
                cur.execute(
                    f"UPDATE sections SET {sql} WHERE section_id = %(id)s",
                    vals)
                conn.commit()
        except IntegrityError as err:
            if err.args[0] == MYSQL_DUPLICITY:
                raise DuplicityError from err
            raise

    def swap(self, conn: Connection, weight: int):
        """Swap section weight with neighbor.

        :weight 1: Move section down
        :weight -1: Move section up
        """
        if weight > 0:  # move down
            sort = "ASC"
            operator = ">="
        else:  # move up
            sort = "DESC"
            operator = "<="

        sql = "UPDATE sections SET weight=%(weight)s WHERE section_id=%(id)s"
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT section_id, weight FROM sections
                WHERE weight {operator} %(weight)s
                ORDER BY weight {sort} LIMIT 2
                """, {"weight": self.weight})
            rows = cur.fetchall()
            if len(rows) < 2:  # noqa: PLR2004
                return False  # can't swap
            assert rows[0] == (self.id, self.weight), rows[0]
            cur.execute(sql, {"weight": self.weight, "id": rows[1][0]})
            cur.execute(sql, {"weight": rows[1][1], "id": self.id})
            conn.commit()
        return True

    @staticmethod
    def list(conn: Connection, user_id: int | None = 0):
        """Get list of sections from db."""
        cond = ""
        if user_id:
            cond = "AND SU.user_id = %(user_id)s"

        with conn.cursor(DictCursor) as cur:
            cur.execute(f"""
                ( SELECT
                    S.*, count(T.section_id), NULL AS count FROM sections AS S
                  LEFT JOIN topics AS T ON (T.section_id = S.section_id)
                    WHERE S.private = 0 GROUP BY S.section_id )
                UNION
                ( SELECT
                    S.*, count(T.section_id) AS count, SU.user_id
                  FROM sections AS S
                  LEFT JOIN topics AS T ON (T.section_id = S.section_id)
                  LEFT JOIN sections_users SU ON (SU.section_id = S.section_id)
                    GROUP BY S.section_id
                    HAVING S.private = 1 {cond} )
                ORDER BY weight
            """, {"user_id": user_id})

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


@dataclass
class SectionUser:
    """Section to User for private sections."""

    section_id: int
    user_id: int

    @staticmethod
    def user_in(conn: Connection, section_id: int, user_id: int):
        """Find if user is on private list for section."""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM sections_users
                WHERE section_id = %(section_id)s AND user_id = %(user_id)s
            """, {"section_id": section_id, "user_id": user_id})
            return bool(cur.fetchone())

    @staticmethod
    def add(conn: Connection, section_id: int, user_id: int):
        """Add user to private list for section."""
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sections_users (section_id, user_id)
                        VALUES (%(section_id)s, %(user_id)s)
                """, {"section_id": section_id, "user_id": user_id})
                conn.commit()
        except IntegrityError as err:
            if err.args[0] == MYSQL_DUPLICITY:
                raise DuplicityError from err
            raise

    @staticmethod
    def remove(conn: Connection, section_id: int, user_id: int):
        """Remove user from private list for section."""
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM sections_users WHERE
                    section_id = %(section_id)s AND user_id = %(user_id)s
            """, {"section_id": section_id, "user_id": user_id})
            conn.commit()

    @staticmethod
    def list(conn: Connection, section_id: int):
        """Get list of sections from db."""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT U.user_id, U.name FROM sections_users AS US
                JOIN users AS U ON (US.user_id = U.user_id)
                WHERE section_id=%(section_id)s
            """, {"section_id": section_id})

            for row in cur:
                yield {"user_id": row[0], "name": row[1]}


DB_CONV[Section.State] = enum2str
