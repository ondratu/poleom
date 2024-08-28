"""Post Attachment model."""
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from io import RawIOBase

from MySQLdb.connections import Connection  # type: ignore[import-untyped]

from .core import app
from .mysql import HEX_LEN, DictCursor

READ_WRITE_BUFFER = 10_485_760  # 10MiB


@dataclass
class File:
    """File simple class."""
    file: RawIOBase
    name: str
    mime_type: str

    @property
    def length(self):
        """Return file length."""
        pos = self.file.tell()
        try:
            self.file.seek(0, os.SEEK_END)
            return self.file.tell()
        finally:
            self.file.seek(0, pos)


@dataclass
class Attachment:
    """Post Attachment model class."""
    post_id: int
    uploaded: datetime
    mime_type: str
    file_name: str
    hexdigest: str
    data: dict

    @property
    def path(self):
        """Return path on disk."""
        return os.path.join(app.attachments, self.hexdigest[:3],
                            self.hexdigest[3:6])

    def to_dict(self):
        """Return dictionary from instance.

        It uses only databases row values.
        """
        return {
            "post_id": self.post_id,
            "uploaded": self.uploaded,
            "mime_type": self.mime_type,
            "file_name": self.file_name,
            "hexdigest": self.hexdigest,
            "data": self.data,
        }

    @staticmethod
    def from_row(row):
        """Return entity from DB row."""
        return Attachment(row["post_id"], row["uploaded"], row["mime_type"],
                          row["file_name"], row["hexdigest"],
                          json.loads(row["data"]))

    @staticmethod
    def create(conn: Connection, post_id: int, file: File):
        """Create or update change request for user in db."""
        uploaded = datetime.now(UTC)
        hexdigest = sha256(
            f"{file.name}.{post_id}".encode()).hexdigest()[:HEX_LEN]
        data = {"length": file.length}
        attachment = Attachment(post_id, uploaded, file.mime_type, file.name,
                                hexdigest, data)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO attachments
                    (post_id, uploaded, mime_type, file_name, hexdigest, data)
                VALUES
                    (%(post_id)s, %(uploaded)s, %(mime_type)s, %(file_name)s,
                     %(hexdigest)s, %(data)s)
                """, attachment.to_dict())
            os.makedirs(attachment.path, exist_ok=True)
            with open(os.path.join(attachment.path, hexdigest), "wb+") as dst:
                while raw := file.file.read(READ_WRITE_BUFFER):
                    dst.write(raw)

            conn.commit()
            return attachment

    @staticmethod
    def get(conn: Connection, hexdigest: str):
        """Get attachment record from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute(
                "SELECT * FROM attachments WHERE hexdigest=%(hexdigest)s",
                {"hexdigest": hexdigest})
            row = cur.fetchone()
            if not row:
                return None
            return Attachment.from_row(row)

    @staticmethod
    def delete(conn: Connection, hexdigest: str):
        """Delete existing item in db."""
        with conn.cursor() as cur:
            attachment = Attachment(0, datetime.now(UTC), "", "", hexdigest,
                                    {})
            file_path = os.path.join(attachment.path, attachment.hexdigest)
            os.unlink(file_path)
            cur.execute(
                "DELETE FROM attachments WHERE hexdigest=%(hexdigest)s",
                {"hexdigest": hexdigest})
            conn.commit()

    @staticmethod
    def list(conn: Connection, post_id: int):
        """Get list of sections from db."""
        with conn.cursor(DictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM attachments AS A
                WHERE post_id=%(post_id)s ORDER BY uploaded
            """, {"post_id": post_id})
            for row in cur:
                yield Attachment.from_row(row)
