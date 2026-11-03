"""Wizard class."""

from importlib.resources import files
from os.path import join

from MySQLdb.connections import Connection  # type: ignore[import-untyped]

from .user import User


class Wizard:
    """Wizard installation setup."""
    SQL_PATH = join(str(files("poleom")), "sql")

    def db_install(self, conn: Connection):
        """Create database tables."""
        _file = join(self.SQL_PATH, "init.sql")
        with open(_file, encoding="utf-8") as sql, conn.cursor() as cur:
            cur.execute(sql.read())

    def insert_admin(self, conn, name, email, password):
        """Insert first admin user to database."""
        User.create(conn, name, email, password)
