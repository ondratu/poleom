"""Unit tests for the SQLite wrapper used by tests."""
import pytest
from MySQLdb import IntegrityError

from poleom.lib.exceptions import MYSQL_DUPLICITY
from poleom.lib.sqlite import Connection, DictCursor


@pytest.fixture
def conn():
    connection = Connection(":memory:")
    cur = connection.cursor()
    cur.execute("CREATE TABLE t (id INTEGER, name TEXT)")
    cur.executemany("INSERT INTO t VALUES (?, ?)",
                    [(1, "a"), (2, "b"), (3, "c")])
    connection.commit()
    return connection


def test_named_placeholders(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM t WHERE id=%(id)s", {"id": 2})
        assert cur.fetchone() == ("b",)


def test_same_placeholder_twice(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM t WHERE id=%(i)s OR id=%(i)s", {"i": 1})
        assert cur.fetchall() == [("a",)]


def test_dict_cursor_rows(conn):
    with conn.cursor(DictCursor) as cur:
        cur.execute("SELECT * FROM t ORDER BY id")
        row = cur.fetchone()
        assert (row["id"], row["name"]) == (1, "a")
        assert [item["id"] for item in cur.fetchall()] == [2, 3]


def test_dict_cursor_no_row(conn):
    with conn.cursor(DictCursor) as cur:
        cur.execute("SELECT * FROM t WHERE id=99")
        assert cur.fetchone() is None


def test_dict_cursor_fetchmany(conn):
    with conn.cursor(DictCursor) as cur:
        cur.execute("SELECT * FROM t ORDER BY id")
        assert [row["id"] for row in cur.fetchmany(2)] == [1, 2]


def test_dict_cursor_iteration(conn):
    with conn.cursor(DictCursor) as cur:
        cur.execute("SELECT * FROM t ORDER BY id")
        assert [row["name"] for row in cur] == ["a", "b", "c"]


def test_rollback_on_error(conn):
    def fail():
        with conn.cursor() as cur:
            cur.execute("INSERT INTO t VALUES (4, 'd')")
            raise RuntimeError

    with pytest.raises(RuntimeError):
        fail()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM t")
        assert cur.fetchone() == (3,)


def test_dict_cursor_fetchmany_default_size(conn):
    with conn.cursor(DictCursor) as cur:
        cur.execute("SELECT * FROM t ORDER BY id")
        assert [row["id"] for row in cur.fetchmany()] == [1]


def test_mysql_sql_mode_is_ignored(conn):
    with conn.cursor() as cur:
        cur.execute("SET sql_mode=(SELECT REPLACE(@@sql_mode,'A',''))")
        assert cur.fetchone() is None


def test_now_function(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT NOW()")
        assert cur.fetchone()[0].startswith("20")


def test_unique_violation_is_mysql_duplicity(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE TABLE u (id INTEGER UNIQUE)")
        cur.execute("INSERT INTO u VALUES (1)")
        with pytest.raises(IntegrityError) as err:
            cur.execute("INSERT INTO u VALUES (1)")

    assert err.value.args[0] == MYSQL_DUPLICITY


def test_other_integrity_error_has_another_code(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE TABLE n (id INTEGER NOT NULL)")
        with pytest.raises(IntegrityError) as err:
            cur.execute("INSERT INTO n VALUES (NULL)")

    assert err.value.args[0] != MYSQL_DUPLICITY
