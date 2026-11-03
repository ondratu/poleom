"""Unit tests of mapping the MySQL duplicate entry error."""
from unittest.mock import MagicMock

import pytest
from MySQLdb import IntegrityError

from poleom.lib.exceptions import MYSQL_DUPLICITY, DuplicityError
from poleom.lib.section import Section, SectionUser
from poleom.lib.topic import Topic
from poleom.lib.user import User


def failing_conn(code):
    """Return connection, which fails with the MySQL integrity error."""
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.execute.side_effect = IntegrityError(code, "error")
    return conn


CALLS = {
    "section create": lambda conn: Section(0, "T", "en", "D").create(conn),
    "section update": lambda conn: Section(1, "T", "en", "D").update(conn),
    "section user": lambda conn: SectionUser.add(conn, 1, 1),
    "topic create": lambda conn: Topic.create(conn, 1, "Title"),
    "user create": lambda conn: User.create(conn, "n", "e@example.com", "p"),
}


@pytest.mark.parametrize("call", CALLS.values(), ids=CALLS.keys())
def test_duplicity(call):
    with pytest.raises(DuplicityError):
        call(failing_conn(MYSQL_DUPLICITY))


@pytest.mark.parametrize("call", CALLS.values(), ids=CALLS.keys())
def test_other_integrity_error_is_raised(call):
    with pytest.raises(IntegrityError):
        call(failing_conn(1452))
