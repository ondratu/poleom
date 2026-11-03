"""Unit tests of the logging MySQL cursors."""
import logging
from unittest.mock import patch

from MySQLdb import cursors

from poleom.lib.mysql import LoggingCursor


def test_query_is_logged(caplog):
    with patch.object(cursors.BaseCursor, "_query", return_value=3) as query, \
            caplog.at_level(logging.INFO, logger="poleom"):
        result = LoggingCursor._query(
            object.__new__(LoggingCursor), b"SELECT 1")

    assert result == 3
    query.assert_called_once()
    assert "SELECT 1" in caplog.text
