"""User record model."""
import re
from dataclasses import dataclass
from enum import Enum
from hashlib import sha3_512

import bcrypt
from MySQLdb import IntegrityError  # type: ignore[import-untyped]
from MySQLdb.connections import Connection  # type: ignore[import-untyped]

from .exceptions import MYSQL_DUPLICITY, DuplicityError
from .mysql import DB_CONV, DictCursor, enum2str
from .pager import Pager

# Three options of the password format
# >= 10 chars, one lowercase letter, one uppercase letter, one number
CHECK_OPT1 = r"((?=.*[a-z])(?=.*[A-Z])(?=.*\d))[\w]{10,}$"
# >= 10 chars, one non-alphanumeric character
CHECK_OPT2 = r"((?=.*\W)(?=.*[\w])[\w\W]{10,})$"
# >= 15 chars
CHECK_OPT3 = r"[\w\W]{15,}$"


@dataclass
class User:
    """Section record model class.

    >>> user = User(0, "", "", None, User.State.ACTIVE)
    >>> user.role
    <Role.MEMBER: 'MEMBER'>
    """
    HASH_ROUNDS = 12
    VALID_PASSWORD_REGEX = re.compile(
        f"^({CHECK_OPT1}|{CHECK_OPT2}|{CHECK_OPT3})")

    class State(Enum):
        """User state enum."""
        ACTIVE = "ACTIVE"
        REGISTERED = "REGISTERED"
        BANNED = "BANNED"
        DELETED = "DELETED"

    class Role(Enum):
        """User role enum."""
        MEMBER = "MEMBER"
        MODERATOR = "MODERATOR"
        ADMIN = "ADMIN"

    _id: int
    name: str
    email: str
    signature: str | None
    state: State
    role: Role = Role.MEMBER

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
            "name": self.name,
            "email": self.email,
            "signature": self.signature,
            "state": self.state,
            "role": self.role,
        }

    def check_role(self, role: Role):
        """Return False if user has insufficient role.

        >>> user = User(0, "", "", None, User.State.ACTIVE, User.Role.MEMBER)
        >>> user.check_role(User.Role.MEMBER)
        True
        >>> user = User(0, "", "", None, User.State.ACTIVE, User.Role.MEMBER)
        >>> user.check_role(User.Role.MODERATOR)
        False
        >>> user = User(0, "", "", None, User.State.ACTIVE, User.Role.MEMBER)
        >>> user.check_role(User.Role.ADMIN)
        False
        >>> user = User(0, "", "", None, User.State.ACTIVE,
        ...             User.Role.MODERATOR)
        >>> user.check_role(User.Role.MEMBER)
        True
        >>> user = User(0, "", "", None, User.State.ACTIVE,
        ...             User.Role.MODERATOR)
        >>> user.check_role(User.Role.MODERATOR)
        True
        >>> user = User(0, "", "", None, User.State.ACTIVE,
        ...             User.Role.MODERATOR)
        >>> user.check_role(User.Role.ADMIN)
        False
        >>> user = User(0, "", "", None, User.State.ACTIVE, User.Role.ADMIN)
        >>> user.check_role(User.Role.MEMBER)
        True
        >>> user = User(0, "", "", None, User.State.ACTIVE, User.Role.ADMIN)
        >>> user.check_role(User.Role.MODERATOR)
        True
        >>> user = User(0, "", "", None, User.State.ACTIVE, User.Role.ADMIN)
        >>> user.check_role(User.Role.ADMIN)
        True
        """
        if self.role == User.Role.MEMBER and role != User.Role.MEMBER:
            return False
        if self.role == User.Role.MODERATOR and role == User.Role.ADMIN:
            return False
        return True

    def is_moderator(self):
        """Return True if user is moderator or admin."""
        return self.role != User.Role.MEMBER

    def is_admin(self):
        """Return True if user is admin."""
        return self.role == User.Role.ADMIN

    @staticmethod
    def from_row(row):
        """Return entity from DB row."""
        return User(row["user_id"], row["name"], row["email"],
                    row["signature"], User.State(row["state"]),
                    User.Role(row["role"]))

    @staticmethod
    def create(conn: Connection,
               name: str,
               email: str,
               password: str,
               signature: str | None = None):
        """Create new user in db."""
        hashed = bcrypt.hashpw(
            sha3_512(password.encode("utf-8")).digest(),
            bcrypt.gensalt(User.HASH_ROUNDS))
        user = User(0, name, email, signature, User.State.REGISTERED,
                    User.Role.MEMBER)

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users
                        (name, email, password, signature, state, role)
                    VALUES
                        (%(name)s, %(email)s, %(password)s, %(signature)s,
                         %(state)s, %(role)s)
                """, dict(user.to_dict(), password=hashed.decode("utf-8")))
                user._id = cur.lastrowid  # pylint: disable=protected-access
                conn.commit()
                return user
        except IntegrityError as err:
            if err.args[0] == MYSQL_DUPLICITY:
                raise DuplicityError from err
            raise

    @staticmethod
    def get(conn: Connection, _id: int):
        """Get user from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM users WHERE user_id=%(id)s
                """, {"id": _id})
            row = cur.fetchone()
            if not row:
                return None
            return User.from_row(row)

    @staticmethod
    def find(conn: Connection, email: str, password: str | None = None):
        """Found user by email and check his password."""
        with conn.cursor(DictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM users WHERE email=%(email)s
                """, {"email": email})
            row = cur.fetchone()
            if not row:
                return None
            try:
                if password and not bcrypt.checkpw(
                        sha3_512(password.encode("utf-8")).digest(),
                        row["password"].encode("utf-8")):
                    return None
            except ValueError:
                return None  # Invalid salt means no or corupted password in DB
            return User.from_row(row)

    def delete(self, conn: Connection):
        """Mark user as delete and anonymize his data."""
        self.email = f"{self.id}@invalid"
        self.name = f"Member {self.id}"
        self.state = User.State.DELETED
        self.role = User.Role.MEMBER
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users SET name=%(name)s, email=%(email)s, password="",
                    signature=NULL, terms=NOW(), state=%(state)s,
                    role=%(role)s, data="{}"
                WHERE user_id = %(id)s
                """, self.to_dict())
            conn.commit()

    def update(self, conn: Connection, password: str | None = None):
        """Update existing user in db."""
        cols = ["name", "email", "signature", "state", "role"]
        vals = self.to_dict()
        if password:
            cols.append("password")
            hashed = bcrypt.hashpw(
                sha3_512(password.encode("utf-8")).digest(),
                bcrypt.gensalt(User.HASH_ROUNDS))
            vals["password"] = hashed.decode("utf-8")

        sql = ",".join(f"{col}=%({col})s" for col in cols)

        with conn.cursor() as cur:
            # ruff: noqa: S608
            cur.execute(
                f"""
                UPDATE users SET {sql}
                WHERE user_id = %(id)s
            """, vals)
            conn.commit()

    @staticmethod
    def list(conn: Connection, pager: Pager):
        """Get list of users from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM users
                LIMIT %(OFFSET)s, %(LIMIT)s
                """, dict(pager.sql_dict()))
            for row in cur:
                yield User.from_row(row)

    @staticmethod
    def search(conn: Connection, query):
        """Get list of users from db when their name match the query."""
        query = f"%{query}%"
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, name FROM users
                WHERE (name LIKE %(query)s OR email LIKE %(query)s)
                    AND state != "DELETED"
                """, {"query": query})
            for row in cur:
                yield {"user_id": row[0], "name": row[1]}

    @staticmethod
    def count(conn: Connection):
        """Return total count of items in db."""
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            return cur.fetchone()[0]


DB_CONV[User.State] = enum2str
DB_CONV[User.Role] = enum2str
