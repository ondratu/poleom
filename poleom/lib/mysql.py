"""MySQL wrapper."""
import json
import logging
from enum import Enum

from MySQLdb import cursors  # type: ignore[import-untyped]
from MySQLdb._mysql import string_literal  # type: ignore[import-untyped]
from MySQLdb.converters import conversions  # type: ignore[import-untyped]

from .. import __name__ as appname

LOGGER = logging.getLogger(appname)


def dict2str(obj: dict, _):
    """Convert dictionary to JSON string."""
    return string_literal(json.dumps(obj))


def enum2str(enum: Enum, _):
    """Convert Enum object to it's string name."""
    return string_literal(enum.name)


DB_CONV = conversions.copy()
DB_CONV[dict] = dict2str
# JSON does not work, cause MySQL don't have JSON as type.


class LoggingCursor(cursors.BaseCursor):
    """MySQL BaseCursor with logging"""

    def _query(self, q):
        LOGGER.info(q.decode("utf-8"))
        return super()._query(q)


class Cursor(LoggingCursor, cursors.Cursor):
    """MySQL Cursor with LoggingCursor"""


class DictCursor(LoggingCursor, cursors.DictCursor):
    """MySQL Cursor with LoggingCursor"""
