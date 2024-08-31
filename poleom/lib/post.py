"""Post record model"""
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from MySQLdb.connections import Connection  # type: ignore[import-untyped]

from .mysql import DictCursor
from .pager import Pager


@dataclass
class Post:
    """Post record model class."""
    # pylint: disable=too-many-instance-attributes
    _id: int
    topic_id: int
    parent: str | None  # parent post hexdigest
    created: datetime | None
    user_id: int
    hexdigest: str
    body: str

    @property
    def id(self):
        """Post.id is read only."""
        return self._id

    def to_dict(self):
        """Return dictionary from instance.

        It uses only databases row values.
        """
        return {
            "id": self._id,
            "topic_id": self.topic_id,
            "parent": self.parent,
            "created": self.created,
            "user_id": self.user_id,
            "hexdigest": self.hexdigest,
            "body": self.body,
        }

    @staticmethod
    def from_row(row):
        """Return Post from row."""
        return Post(row["post_id"], row["topic_id"], row["parent"],
                    row["created"], row["user_id"], row["hexdigest"],
                    row["body"])

    @staticmethod
    def create(conn: Connection,
               topic_id: int,
               user_id: int,
               body: str,
               parent: str | None = None):
        """Create new post in db."""
        created = datetime.now(UTC)
        hexdigest = sha256(
            f"{created.timestamp()}.{user_id}".encode()).hexdigest()[:10]
        post = Post(0, topic_id, parent, created, user_id, hexdigest, body)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO posts (topic_id, parent, created, user_id,
                        hexdigest, body)
                VALUES (%(topic_id)s, %(parent)s, %(created)s, %(user_id)s,
                        %(hexdigest)s, %(body)s)
            """, post.to_dict())
            post._id = cur.lastrowid  # pylint: disable=protected-access
            conn.commit()
            return post

    @staticmethod
    def get(conn: Connection, _id: int):
        """Get post record from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute("SELECT * FROM posts WHERE post_id=%(id)s",
                        {"id": _id})
            row = cur.fetchone()
            if not row:
                return None
            return Post.from_row(row)

    @staticmethod
    def find(conn: Connection, hexdigest: str):
        """Find post record by hexdigest in db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute("SELECT * FROM posts WHERE hexdigest=%(hexdigest)s",
                        {"hexdigest": hexdigest})
            row = cur.fetchone()
            if not row:
                return None
            return Post.from_row(row)

    @staticmethod
    def delete(conn: Connection, _id: int):
        """Delete existing item in db."""
        with conn.cursor() as cur:
            cur.execute("DELETE FROM posts WHERE post_id=%(id)s", {"id": _id})

    def update(self, conn: Connection):
        """Update existing item in db."""
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE posts SET
                    body=%(body)s
                WHERE post_id = %(id)s
            """, {
                    "body": self.body,
                    "id": self._id,
                })

    @staticmethod
    def list(conn: Connection, pager: Pager, topic_id: int):
        """Get list of sections from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM posts AS P
                    LEFT JOIN users AS U ON (U.user_id = P.user_id)
                WHERE topic_id=%(topic_id)s ORDER BY post_id
                LIMIT %(OFFSET)s, %(LIMIT)s
            """, dict(pager.sql_dict(), topic_id=topic_id))
            for row in cur:
                post = Post.from_row(row)
                yield post

            cur.execute(
                """
                SELECT COUNT(*) AS count FROM posts
                WHERE topic_id=%(topic_id)s
            """, {"topic_id": topic_id})
            pager.total = cur.fetchone()["count"]

    @staticmethod
    def count(conn: Connection, topic_id: int):
        """Return total count of sections in db."""
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM posts WHERE
                WHERE topic_id=%(topic_id)s""", {"topic_id": topic_id})
            return cur.fetchone()[0]
