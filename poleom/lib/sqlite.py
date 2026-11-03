"""Sqlite wrapper."""

import re
import sqlite3
from datetime import UTC, datetime

from MySQLdb import IntegrityError  # type: ignore[import-untyped]

from .exceptions import MYSQL_DUPLICITY

# MySQL style ``%(name)s`` placeholder used by models
PYFORMAT = re.compile(r"%\((\w+)\)s")


class Cursor(sqlite3.Cursor):
    """Add context manager protocol methods to cursor."""

    def execute(self, sql, parameters=()):
        """Execute SQL, MySQL ``%(name)s`` placeholders are converted.

        MySQL only ``SET sql_mode`` is ignored. The unique constraint error
        is raised as the MySQL duplicate entry error.
        """
        if sql.lstrip().startswith("SET sql_mode"):
            return self
        try:
            return super().execute(PYFORMAT.sub(r":\1", sql), parameters)
        except sqlite3.IntegrityError as err:
            # the models expect the MySQL error of the duplicate entry
            code = MYSQL_DUPLICITY if "UNIQUE" in str(err) else 1451
            raise IntegrityError(code, str(err)) from err

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self.connection.rollback()


class DictCursor(Cursor):
    """Implementation of Dictionary cursor for sqlite."""

    def __next__(self):
        """Return next row as `sqlite3.Row`."""
        row = super().__next__()
        return sqlite3.Row(self, row) if row else None

    def fetchone(self):
        """Return one row as `sqlite3.Row`."""
        row = super().fetchone()
        return sqlite3.Row(self, row) if row else None

    def fetchall(self):
        """Return all rows as `sqlite3.Row`."""
        rows = super().fetchall()
        return [sqlite3.Row(self, row) for row in rows]

    def fetchmany(self, size=None):
        """Return rows as `sqlite3.Row`, `arraysize` rows by default."""
        rows = super().fetchmany(self.arraysize if size is None else size)
        return [sqlite3.Row(self, row) for row in rows]


class Connection(sqlite3.Connection):
    """Connection which returns context manager `Cursor` by default."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # MySQL function used by the models
        self.create_function("NOW", 0, lambda: datetime.now(UTC).isoformat())

    # the delegation is not useless, it changes the default factory
    # pylint: disable-next=useless-parent-delegation
    def cursor(self, factory=Cursor):  # type: ignore[override]
        """Return cursor, `Cursor` by default."""
        return super().cursor(factory)
