"""Tests of the poleomctl commands which do not need the database."""
import re
import subprocess
import sys
from hashlib import sha3_512
from io import StringIO
from unittest.mock import patch

import bcrypt
import pytest

from poleom import ctl

PASSWORD = "Str0ngPassw0rd"


def run(*argv):
    lines = []
    code = ctl.main(list(argv), lines.append)
    return code, lines


def test_release_ignores_suffix_and_compares_numbers():
    assert ctl.release("0.2.0.dev0") == (0, 2, 0)
    assert ctl.release("0.9.0") < ctl.release("0.10.0")


def test_release_of_nonsense():
    with pytest.raises(ctl.CtlError):
        ctl.release("dev")


def test_password_hash_matches_application_format():
    hashed = ctl.password_hash(PASSWORD, 4)
    assert bcrypt.checkpw(
        sha3_512(PASSWORD.encode("utf-8")).digest(), hashed.encode("utf-8"))


def test_read_ini(tmp_path):
    ini = tmp_path / "uwsgi.ini"
    ini.write_text("[uwsgi]\nenv = app_db=mysql://u:p@h/d\n"
                   "# env = app_db=commented\nenv = app_title=My forum \n"
                   "processes = 2\n")
    assert ctl.read_ini(str(ini)) == {"app_db": "mysql://u:p@h/d",
                                      "app_title": "My forum"}


def test_read_missing_ini(tmp_path):
    code, lines = run("--ini", str(tmp_path / "missing.ini"), "db:version")
    assert code == 2
    assert "Can not read" in lines[0]


def test_db_conf_sources(tmp_path, monkeypatch):
    ini = tmp_path / "uwsgi.ini"
    ini.write_text("env = app_db=mysql://ini@h/ini\n")
    monkeypatch.setenv("app_db", "mysql://env@h/env")

    assert ctl.db_conf("mysql://arg@h/arg", str(ini))["user"] == "arg"
    assert ctl.db_conf(None, str(ini))["user"] == "ini"
    assert ctl.db_conf(None, None)["user"] == "env"


def test_db_conf_without_source(monkeypatch):
    monkeypatch.delenv("app_db", raising=False)
    with pytest.raises(ctl.CtlError, match="No database"):
        ctl.db_conf(None, None)


def test_db_conf_invalid_dsn():
    code, lines = run("--db", "nonsense", "db:version")
    assert code == 2
    assert "app_db" in lines[0]


def test_backup_uses_mysqldump_without_password_in_arguments(tmp_path):
    conf = {"host": "h", "port": 3306, "user": "u", "password": "secret",
            "charset": "utf8mb4", "database": "forum"}
    with patch("subprocess.run") as process:
        ctl.backup(conf, tmp_path / "dump.sql")

    command = process.call_args.args[0]
    assert command[0] == "mysqldump"
    assert command[-1] == "forum"
    assert not any("secret" in item for item in command)
    assert process.call_args.kwargs["env"]["MYSQL_PWD"] == "secret"


@pytest.mark.parametrize("error", [
    FileNotFoundError("mysqldump"),
    subprocess.CalledProcessError(2, "mysqldump")])
def test_failed_backup_removes_the_file(tmp_path, error):
    target = tmp_path / "dump.sql"
    target.write_text("partial")
    with patch("subprocess.run", side_effect=error), \
            pytest.raises(ctl.CtlError, match="backup failed"):
        ctl.backup({"host": "h", "port": 1, "user": "u", "charset": "c",
                    "database": "d"}, target)
    assert not target.exists()


def test_password_sql(monkeypatch):
    monkeypatch.setattr(sys, "stdin", StringIO(PASSWORD + "\n"))
    code, lines = run("user:password-sql", "--password-stdin",
                      "--rounds", "4")

    assert code == 0
    assert re.fullmatch(r"UPDATE users SET password='\$2b\$04\$[^']+', "
                        r"email='your@login' WHERE email='root@localhost';",
                        lines[1])
    assert lines[2] == "-- Password reset"


def test_password_is_asked_twice():
    with patch("poleom.ctl.getpass", side_effect=["a", "b"]):
        code, lines = run("user:password-sql")
    assert (code, lines) == (2, ["poleomctl: The passwords differ."])


def test_empty_password():
    with patch("poleom.ctl.getpass", return_value=""):
        code, lines = run("user:password-sql")
    assert (code, lines) == (2, ["poleomctl: The password is empty."])


def test_run_exits_with_the_code():
    with patch("sys.argv", ["poleomctl", "app:version"]), \
            pytest.raises(SystemExit) as exit_info:
        ctl.run()
    assert exit_info.value.code == 0


@pytest.mark.parametrize("value", ["0", "3", "32", "many"])
def test_wrong_rounds(value, capsys):
    with pytest.raises(SystemExit):
        ctl.parser().parse_args(["user:set-password", "--rounds", value])
    assert "from 4 to 31" in capsys.readouterr().err


def test_backup_file_is_private(tmp_path):
    target = tmp_path / "dump.sql"
    conf = {"host": "h", "port": 1, "user": "u", "charset": "c",
            "database": "d"}
    with patch("subprocess.run"):
        ctl.backup(conf, target)
    assert target.stat().st_mode & 0o777 == 0o600


def test_statements_ignore_comment_after_statement():
    sql = "ALTER TABLE t ADD c INT; -- note\nDROP TABLE x;\n"
    assert ctl.statements(sql) == ["ALTER TABLE t ADD c INT;",
                                   "DROP TABLE x;"]


def test_statements_keep_lines_with_strings():
    sql = "INSERT INTO t VALUES ('a; -- b');\n"
    assert ctl.statements(sql) == ["INSERT INTO t VALUES ('a; -- b');"]


def test_read_ini_removes_quotes(tmp_path):
    ini = tmp_path / "uwsgi.ini"
    ini.write_text("env = app_db='mysql://u:p@h/d'\n")
    assert ctl.read_ini(str(ini)) == {"app_db": "mysql://u:p@h/d"}
