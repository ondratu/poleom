"""User change request model."""
import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from MySQLdb.connections import Connection  # type: ignore[import-untyped]
from MySQLdb.cursors import DictCursor  # type: ignore[import-untyped]

from .smtp import Smtp
from .user import User
from .view import generate_page


@dataclass
class ChangeRequest:
    """User change request model class."""

    user_id: int
    created: datetime
    accepted: datetime | None
    hexdigest: str
    data: dict

    def to_dict(self):
        """Return dictionary from instance.

        It uses only databases row values.
        """
        return {
            "user_id": self.user_id,
            "created": self.created,
            "accepted": self.accepted,
            "data": self.data,
            "hexdigest": self.hexdigest,
        }

    @staticmethod
    def from_row(row):
        """Return entity from DB row."""
        return ChangeRequest(row["user_id"], row["created"], row["accepted"],
                             row["hexdigest"], json.loads(row["data"]))

    @staticmethod
    def create(conn: Connection, user_id: int, data: dict):
        """Create or update change request for user in db."""
        created = datetime.now()
        hexdigest = sha256(
            f"{created.timestamp()}.{user_id}".encode()).hexdigest()
        change_request = ChangeRequest(user_id, created, None, hexdigest, data)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO change_request
                    (user_id, created, data, hexdigest)
                VALUES
                    (%(user_id)s, %(created)s, %(data)s, %(hexdigest)s)
                """,
                dict(change_request.to_dict(),
                     data=json.dumps(change_request.data)))
            conn.commit()
            return change_request

    def accept(self, conn: Connection):
        """Accept existing change_request in db."""
        self.accepted = datetime.now()
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

    def send_email(self,
                   smtp: Smtp,
                   service_title: str,
                   user: User,
                   url: str):
        """Send email depend of type of change request."""
        if user.state == User.State.REGISTERED:
            subject = f"Sign up to {service_title} confirmation"
            template = "user/registered.jinja"
        elif self.data.get("password", False) is None:
            subject = f"Reset password request from {service_title}"
            template = "user/reset-password-request.jinja"
        elif "old_email" in self.data or "password" in self.data:
            subject = f"Credetials for {service_title} changed"
            template = "user/changed.jinja"
        else:
            msg = "No mail template selected"
            raise RuntimeError(msg)

        smtp.send_email_txt(
            subject,
            user.email,
            generate_page(template, user=user, change_request=self, url=url))
