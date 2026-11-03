"""Sqlite wrapper."""

import re
import sqlite3

# MySQL style ``%(name)s`` placeholder used by models
PYFORMAT = re.compile(r"%\((\w+)\)s")


class Cursor(sqlite3.Cursor):
    """Add context manager protocol methods to cursor."""

    def execute(self, sql, parameters=()):
        """Execute SQL, MySQL ``%(name)s`` placeholders are converted."""
        return super().execute(PYFORMAT.sub(r":\1", sql), parameters)

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

    def fetchmany(self, size=Cursor.arraysize):
        """Return rows as `sqlite3.Row`."""
        rows = super().fetchmany(size)
        return [sqlite3.Row(self, row) for row in rows]


class Connection(sqlite3.Connection):
    """Connection which returns context manager `Cursor` by default."""

    # the delegation is not useless, it changes the default factory
    # pylint: disable-next=useless-parent-delegation
    def cursor(self, factory=Cursor):  # type: ignore[override]
        """Return cursor, `Cursor` by default."""
        return super().cursor(factory)
