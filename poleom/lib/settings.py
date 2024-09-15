"""Models for forum settings."""
from dataclasses import dataclass

from MySQLdb.connections import Connection

from .mysql import DictCursor


@dataclass
class Language:
    """Language model class."""

    lang: str
    locale: str
    language: str
    active: bool

    def to_dict(self):
        """Return dictionary from instance."""
        return {
            "lang": self.lang,
            "locale": self.locale,
            "language": self.language,
            "active": self.active,
        }

    @staticmethod
    def from_row(row):
        """Return entity from DB row."""
        return Language(row["lang"], row["locale"], row["language"],
                        row["active"])

    @staticmethod
    def list(conn: Connection, only_active=False):
        """Get list of languages from db."""
        cond = ""
        if only_active:
            cond = "WHERE active=1"
        with conn.cursor(DictCursor) as cur:
            # ruff: noqa: S608
            cur.execute(f"SELECT * FROM languages ORDER BY lang {cond}")
            result = []
            for row in cur:
                result.append(Language.from_row(row))
            return result
