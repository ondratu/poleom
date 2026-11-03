"""Tests of the poleomctl commands which use the database."""
import sqlite3
from unittest.mock import patch

import pytest
from MySQLdb import ProgrammingError

from poleom import __version__, ctl
from poleom.lib.sqlite import Connection, Cursor
from poleom.lib.user import User


class MysqlCursor(Cursor):
    """MySQL error of a missing table."""

    def execute(self, sql, parameters=()):
        try:
            return super().execute(sql, parameters)
        except sqlite3.OperationalError as err:
            raise ProgrammingError(ctl.NO_TABLE, str(err)) from err


class OldConnection(Connection):
    """Database of the version 0.1.0."""

    def cursor(self, factory=MysqlCursor):
        return super().cursor(factory)


@pytest.fixture
def migrations(tmp_path):
    (tmp_path / "0.2.0.sql").write_text(
        "-- first\nCREATE TABLE meta (name TEXT PRIMARY KEY, value TEXT);\n"
        "CREATE TABLE a (x INT);\nINSERT INTO a VALUES (1);\n")
    (tmp_path / "0.10.0.sql").write_text("CREATE TABLE b (x INT);\n")
    (tmp_path / "README").write_text("not a migration")
    return tmp_path


@pytest.fixture
def old_db(db):
    """Database without the version, like the one of 0.1.0."""
    db.execute("DROP TABLE meta")
    db.commit()
    db.close()
    return OldConnection(":memory:")


class Open:
    """Connection which the tests can ask after the command closed it."""

    closed = False

    def __init__(self, conn):
        self.conn = conn

    def __getattr__(self, name):
        return getattr(self.conn, name)

    def close(self):
        self.closed = True


@pytest.fixture
def ctl_db(db):
    with patch("poleom.ctl.connect", return_value=Open(db)) as mock:
        db.mock = mock
        yield db


def run(*argv):
    lines = []
    code = ctl.main(list(argv), lines.append)
    return code, lines


def test_init_has_the_version_of_the_last_migration(db):
    assert ctl.db_version(db) == ctl.code_schema_version()


def test_version_of_the_database_without_table(old_db):
    assert ctl.db_version(old_db) == "0.1.0"


def test_version_of_the_database_without_row(db):
    db.execute("DELETE FROM meta")
    with pytest.raises(ctl.CtlError, match="no schema_version"):
        ctl.db_version(db)


def test_other_database_errors_are_not_hidden():
    conn = OldConnection(":memory:")
    with patch.object(MysqlCursor, "execute",
                      side_effect=ProgrammingError(1064, "syntax")), \
            pytest.raises(ProgrammingError):
        ctl.db_version(conn)


def test_migrations_are_sorted_by_version(migrations):
    found = ctl.migrations(migrations)
    assert [version for version, _ in found] == ["0.2.0", "0.10.0"]
    assert ctl.code_schema_version(migrations) == "0.10.0"


def test_code_schema_version_without_migrations(tmp_path):
    assert ctl.code_schema_version(tmp_path) == "0.1.0"


def test_statements():
    sql = "-- comment\nCREATE TABLE a (\n  x INT\n);\n\nINSERT INTO a\n"
    assert ctl.statements(sql) == ["CREATE TABLE a (\n  x INT\n);",
                                   "INSERT INTO a"]


def test_upgrade_runs_pending_migrations_once(old_db, migrations):
    assert ctl.upgrade(old_db, migrations) == ["0.2.0", "0.10.0"]

    assert ctl.db_version(old_db) == "0.10.0"
    assert old_db.execute("SELECT x FROM a").fetchone()[0] == 1
    assert not ctl.upgrade(old_db, migrations)


def test_upgrade_skips_older_migrations(old_db, migrations):
    old_db.execute("CREATE TABLE meta (name TEXT PRIMARY KEY, value TEXT)")
    old_db.execute("INSERT INTO meta VALUES ('schema_version', '0.2.0')")

    assert ctl.upgrade(old_db, migrations) == ["0.10.0"]


def test_real_migration_is_not_pending_in_new_database(db):
    assert not ctl.pending(db)


def test_app_version():
    code, lines = run("app:version")
    assert code == 0
    assert lines == [
        f"{__version__} (database schema {ctl.code_schema_version()})"]


def test_db_version(ctl_db):
    assert run("--db", "mysql://u/d", "db:version") == (
        0, [ctl.code_schema_version()])


def test_connection_gets_arguments_and_is_closed(ctl_db):
    with patch("poleom.ctl.connect", return_value=Open(ctl_db)) as mock:
        args = ctl.parser().parse_args(["--db", "mysql://u:p@h:3307/d",
                                        "db:version"])
        with ctl.database(args) as conn:
            pass
    mock.assert_called_once_with(host="h", port=3307, database="d",
                                 charset="utf8mb4", user="u", password="p")
    assert conn.closed


def test_connection_is_closed_after_an_error(ctl_db):
    args = ctl.parser().parse_args(["--db", "mysql://u/d", "db:version"])
    link = Open(ctl_db)
    with patch("poleom.ctl.connect", return_value=link), \
            pytest.raises(RuntimeError), ctl.database(args):
        raise RuntimeError
    assert link.closed


def test_db_status_newer_database(ctl_db):
    ctl_db.execute("UPDATE meta SET value='9.0.0'")
    code, lines = run("--db", "mysql://u/d", "db:status")
    assert code == 1
    assert lines[-1] == "the database is newer than the code"


def test_failed_migration_says_to_restore(old_db, tmp_path):
    (tmp_path / "0.2.0.sql").write_text("CREATE TABLE a (x INT);\nBROKEN;\n")
    with pytest.raises(ctl.CtlError, match=r"statement 2.*backup"):
        ctl.upgrade(old_db, tmp_path)
    assert ctl.db_version(old_db) == "0.1.0"


def test_db_status_up_to_date(ctl_db):
    code, lines = run("--db", "mysql://u/d", "db:status")
    assert code == 0
    assert lines[-1] == "the database is up to date"


def test_db_status_pending(old_db):
    with patch("poleom.ctl.connect", return_value=Open(old_db)):
        code, lines = run("--db", "mysql://u/d", "db:status")
    assert code == 1
    assert "database: 0.1.0" in lines
    assert "pending migrations: 0.2.0" in lines


def test_db_upgrade_makes_backup_first(old_db, migrations, tmp_path):
    with patch("poleom.ctl.connect", return_value=Open(old_db)), \
            patch("poleom.ctl.MIGRATIONS", migrations), \
            patch("poleom.ctl.backup") as dump:
        code, lines = run("--db", "mysql://u/d", "db:upgrade",
                          "--backup-dir", str(tmp_path))
    assert code == 0
    dump.assert_called_once()
    assert dump.call_args.args[1].parent == tmp_path
    assert lines[0].startswith("backup: ")
    assert lines[1:] == ["upgraded to 0.2.0", "upgraded to 0.10.0"]


def test_db_upgrade_without_backup(old_db, migrations):
    with patch("poleom.ctl.connect", return_value=Open(old_db)), \
            patch("poleom.ctl.MIGRATIONS", migrations), \
            patch("poleom.ctl.backup") as dump:
        code, lines = run("--db", "mysql://u/d", "db:upgrade", "--no-backup")
    assert code == 0
    dump.assert_not_called()
    assert lines == ["upgraded to 0.2.0", "upgraded to 0.10.0"]


def test_db_upgrade_nothing_to_do(ctl_db):
    with patch("poleom.ctl.backup") as dump:
        code, lines = run("--db", "mysql://u/d", "db:upgrade")
    assert (code, lines) == (0, ["the database is up to date"])
    dump.assert_not_called()


def test_failed_backup_stops_the_upgrade(old_db):
    with patch("poleom.ctl.connect", return_value=Open(old_db)), \
            patch("poleom.ctl.backup", side_effect=ctl.CtlError("no dump")):
        code, lines = run("--db", "mysql://u/d", "db:upgrade")
    assert code == 2
    assert lines == ["poleomctl: no dump"]
    assert ctl.db_version(old_db) == "0.1.0"


def test_db_backup(tmp_path):
    target = tmp_path / "dump.sql"
    with patch("poleom.ctl.backup") as dump:
        code, lines = run("--db", "mysql://u:p@h/d", "db:backup", str(target))
    assert (code, lines) == (0, [f"backup: {target}"])
    assert dump.call_args.args[1] == target


def test_db_backup_default_name():
    with patch("poleom.ctl.backup") as dump:
        run("--db", "mysql://u:p@h/forum", "db:backup")
    name = dump.call_args.args[1].name
    assert name.startswith("forum-")
    assert name.endswith(".sql")


def test_set_password_of_root(ctl_db):
    with patch("poleom.ctl.getpass", return_value="Str0ngPassw0rd"):
        code, lines = run("--db", "mysql://u/d", "user:set-password",
                          "--new-email", "me@example.com", "--rounds", "4")

    assert (code, lines) == (0, ["the password of me@example.com is set"])
    assert User.find(ctl_db, "me@example.com", "Str0ngPassw0rd")


def test_set_password_of_unknown_user(ctl_db):
    with patch("poleom.ctl.getpass", return_value="x"):
        code, lines = run("--db", "mysql://u/d", "user:set-password",
                          "--email", "nobody@example.com", "--rounds", "4")
    assert code == 2
    assert lines == ["poleomctl: No user with the e-mail nobody@example.com."]


def test_set_password_to_used_email(ctl_db):
    ctl_db.execute(
        "INSERT INTO users (name, email, state, role, data) "
        "VALUES ('a', 'used@example.com', 'ACTIVE', 'MEMBER', '{}')")
    with patch("poleom.ctl.getpass", return_value="x"):
        code, lines = run("--db", "mysql://u/d", "user:set-password",
                          "--new-email", "used@example.com", "--rounds", "4")
    assert code == 2
    assert lines == [
        "poleomctl: The e-mail used@example.com is used already."]
