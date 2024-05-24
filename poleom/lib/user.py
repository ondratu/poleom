"""User record model."""
from dataclasses import dataclass
from hashlib import sha3_512

import bcrypt
from MySQLdb.connections import Connection  # type: ignore[import-untyped]
from MySQLdb.cursors import DictCursor  # type: ignore[import-untyped]


@dataclass
class User:
    """Section record model class."""
    HASH_ROUNDS = 12

    _id: int
    name: str
    email: str
    signature: str | None

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
            "name": self.name,
            "email": self.email,
            "signature": self.signature,
        }

    @staticmethod
    def from_row(row):
        """Return entity from DB row."""
        return User(row["user_id"], row["name"], row["email"],
                    row["signature"])

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
        user = User(0, name, email, signature)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users
                    (name, email, password, signature)
                VALUES
                    (%(name)s, %(email)s, %(password)s, %(signature)s)
            """, dict(user.dict(), password=hashed.decode("utf-8")))
            user._id = cur.lastrowid  # pylint: disable=protected-access
            return user

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
    def find(conn: Connection, email: str, password: str):
        """Found user by email and check his password."""
        with conn.cursor(DictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM users WHERE email=%(email)s
                """, {"email": email})
            row = cur.fetchone()
            if not row:
                return None
            if not bcrypt.checkpw(sha3_512(password.encode("utf-8")).digest(),
                                  row["password"].encode("utf-8")):
                return None
            return User.from_row(row)

    @staticmethod
    def delete(conn: Connection, _id: int):
        """Delete existing user in db."""
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE user_id=%(id)s", {"id": _id})

    def update(self, conn: Connection, password: str | None = None):
        """Update existing user in db."""
        cols = ["name", "email", "signature"]
        vals = self.dict()
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

    @staticmethod
    def list(conn: Connection):
        """Get list of users from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute("SELECT name, email, signature FROM users")
            for row in cur:
                yield User.from_row(row)

    @staticmethod
    def count(conn: Connection):
        """Return total count of items in db."""
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            return cur.fetchone()[0]
