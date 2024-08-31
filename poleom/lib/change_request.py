"""User change request model."""
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256

from MySQLdb.connections import Connection  # type: ignore[import-untyped]

from .core import app
from .mysql import DB_CONV, DictCursor, enum2str
from .smtp import Smtp
from .user import User
from .view import render_template


@dataclass
class ChangeRequest:
    """User change request model class."""

    class State(Enum):
        """Change Request state enum."""
        REGISTER = "REGISTER"
        PASSWORD = "PASSWORD"  # noqa: S105
        INFO_CHANGED = "INFO_CHANGED"
        INFO_BANNED = "INFO_BANNED"
        INFO_ACTIVATEDD = "INFO_ACTIVATED"
        INFO_DELETED = "INFO_DELETED"

    user_id: int
    created: datetime
    accepted: datetime | None
    hexdigest: str
    state: State
    data: dict

    def to_dict(self):
        """Return dictionary from instance.

        It uses only databases row values.
        """
        return {
            "user_id": self.user_id,
            "created": self.created,
            "accepted": self.accepted,
            "hexdigest": self.hexdigest,
            "state": self.state,
            "data": self.data,
        }

    @staticmethod
    def from_row(row):
        """Return entity from DB row."""
        return ChangeRequest(row["user_id"], row["created"],
                             row["accepted"], row["hexdigest"],
                             ChangeRequest.State(row["state"]),
                             json.loads(row["data"]))

    @staticmethod
    def create(conn: Connection, user_id: int, state: State, data: dict):
        """Create or update change request for user in db."""
        created = datetime.now(UTC)
        hexdigest = sha256(
            f"{created.timestamp()}.{user_id}".encode()).hexdigest()
        change_request = ChangeRequest(user_id, created, None, hexdigest,
                                       state, data)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO change_request
                    (user_id, created, hexdigest, state, data)
                VALUES
                    (%(user_id)s, %(created)s, %(hexdigest)s, %(state)s,
                     %(data)s)
                """, change_request.to_dict())
            conn.commit()
            return change_request

    def accept(self, conn: Connection):
        """Accept existing change_request in db."""
        self.accepted = datetime.now(UTC)
        with conn.cursor() as cur:
            cur.execute(
                """
                    UPDATE change_request SET accepted=%(accepted)s
                    WHERE hexdigest = %(hexdigest)s
                """, self.to_dict())
            conn.commit()

    @staticmethod
    def get(conn: Connection, hexdigest: str):
        """Get post record from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute(
                "SELECT * FROM change_request WHERE hexdigest=%(hexdigest)s",
                {"hexdigest": hexdigest})
            row = cur.fetchone()
            if not row:
                return None
            return ChangeRequest.from_row(row)

    def send_email(self, smtp: Smtp, user: User, url: str):
        """Send email depend of type of change request."""
        if self.state == ChangeRequest.State.REGISTER:
            subject = f"Sign up to {app.title} confirmation"
            template = "user/registered.jinja"
        elif self.state == ChangeRequest.State.PASSWORD:
            subject = f"Reset password request from {app.title}"
            template = "user/reset-password-request.jinja"
        elif self.state == ChangeRequest.State.INFO_CHANGED:
            subject = f"Credetials for {app.title} changed"
            template = "user/changed.jinja"
        else:
            msg = "No mail template selected"
            raise RuntimeError(msg)

        smtp.send_email_txt(
            subject, user.email,
            render_template(template, user=user, change_request=self, url=url))


DB_CONV[ChangeRequest.State] = enum2str
