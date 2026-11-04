"""The ``poleomctl`` command, the administration of an installation.

Commands are grouped like in ``occ`` of Nextcloud: ``app:*`` about the code,
``db:*`` about the database and ``user:*`` about the accounts.
"""
import os
import re
import subprocess
import sys
from argparse import ArgumentParser, ArgumentTypeError
from contextlib import contextmanager
from datetime import datetime
from getpass import getpass
from hashlib import sha3_512
from importlib.resources import files
from importlib.resources.abc import Traversable
from os import environ
from pathlib import Path

from bcrypt import gensalt, hashpw
from MySQLdb import IntegrityError, ProgrammingError, connect

from . import __version__
from .lib.dsn import parse_dsn

MIGRATIONS = files("poleom").joinpath("mysql", "migrations")
BASE_VERSION = "0.1.0"  # the release without the version in the database
ROOT = "root@localhost"
NO_TABLE = 1146  # MySQL error: the table does not exist
# a comment after a statement, a line with a string is left as it is
COMMENT = re.compile(r"^([^'\"]*?);\s+--.*$")
ENV_LINE = re.compile(r"^\s*env\s*=\s*(\w+)=(.*?)\s*$")


class CtlError(Exception):
    """An error which is printed to the user without the traceback."""


def release(version: str) -> tuple[int, ...]:
    """Return the numbers of the release, a suffix like ``dev0`` is ignored.

    >>> release("0.2.0.dev0") < release("0.10.0")
    True
    """
    match = re.match(r"\d+(\.\d+)*", version)
    if not match:
        msg = f"Not a version: {version}"
        raise CtlError(msg)
    return tuple(int(part) for part in match.group().split("."))


def password_hash(password: str, rounds: int = 12) -> str:
    """Return password hash in the format used by the application."""
    return hashpw(
        sha3_512(password.encode("utf-8")).digest(),
        gensalt(rounds)).decode("utf-8")


# configuration

def read_ini(path: str) -> dict[str, str]:
    """Return the ``env =`` variables of the uWSGI ini file."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as err:
        msg = f"Can not read {path}: {err.strerror}"
        raise CtlError(msg) from err
    variables = {}
    for line in text.splitlines():
        match = ENV_LINE.match(line)
        if match:
            variables[match.group(1)] = match.group(2).strip("'\"")
    return variables


def db_conf(dsn: str | None, ini: str | None) -> dict:
    """Return the database connection arguments.

    The source is the first of ``--db``, ``--ini`` and the ``app_db``
    environment variable.
    """
    dsn = dsn or (read_ini(ini) if ini else environ).get("app_db")
    if not dsn:
        msg = "No database, use --db, --ini or the app_db variable."
        raise CtlError(msg)
    try:
        return parse_dsn(dsn)
    except ValueError as err:
        raise CtlError(str(err)) from err


@contextmanager
def database(args):
    """Connect to the database given by the arguments, close it at the end."""
    conn = connect(**db_conf(args.db, args.ini))
    try:
        yield conn
    finally:
        conn.close()


# schema version

def db_version(conn) -> str:
    """Return the version of the database schema."""
    with conn.cursor() as cur:
        try:
            cur.execute("SELECT value FROM meta WHERE name='schema_version'")
        except ProgrammingError as err:
            if err.args[0] != NO_TABLE:
                raise
            return BASE_VERSION  # databases of 0.1.0 have no table
        row = cur.fetchone()
    if not row:
        msg = "The table meta has no schema_version, restore the database."
        raise CtlError(msg)
    return row[0]


def migrations(
        path: Traversable | None = None) -> list[tuple[str, Traversable]]:
    """Return migrations ``(version, file)`` in the order of versions."""
    found = [(item.name[:-4], item)
             for item in (path or MIGRATIONS).iterdir()
             if item.name.endswith(".sql")]
    return sorted(found, key=lambda item: release(item[0]))


def code_schema_version(path: Traversable | None = None) -> str:
    """Return the schema version which the code needs."""
    found = migrations(path)
    return found[-1][0] if found else BASE_VERSION


def pending(conn, path: Traversable | None = None):
    """Return migrations newer than the database."""
    current = release(db_version(conn))
    return [item for item in migrations(path) if release(item[0]) > current]


def statements(sql: str) -> list[str]:
    """Split a migration to statements, they end with ``;`` at a line end."""
    lines = (COMMENT.sub(r"\1;", line) for line in sql.splitlines()
             if line.strip() and not line.lstrip().startswith("--"))
    result: list[str] = []
    current: list[str] = []
    for line in lines:
        current.append(line)
        if line.rstrip().endswith(";"):
            result.append("\n".join(current))
            current = []
    if current:
        result.append("\n".join(current))
    return result


def upgrade(conn, path: Traversable | None = None) -> list[str]:
    """Run the pending migrations, return their versions."""
    done = []
    for version, item in pending(conn, path):
        with conn.cursor() as cur:
            for number, statement in enumerate(
                    statements(item.read_text(encoding="utf-8")), 1):
                try:
                    cur.execute(statement)
                except Exception as err:
                    # DDL is committed by MySQL, the migration is not atomic
                    msg = (f"The migration {version} failed in the statement "
                           f"{number}: {err}. The database may be changed "
                           "partly, restore it from the backup.")
                    raise CtlError(msg) from err
            cur.execute("REPLACE INTO meta (name, value) "
                        "VALUES ('schema_version', %(version)s)",
                        {"version": version})
        conn.commit()
        done.append(version)
    return done


def backup(conf: dict, target: Path) -> None:
    """Dump the database to the file with ``mysqldump``."""
    command = ["mysqldump", "--single-transaction", "--routines",
               f"--host={conf['host']}", f"--port={conf['port']}",
               f"--user={conf['user']}",
               f"--default-character-set={conf['charset']}",
               f"--result-file={target}", conf["database"]]
    # the password is not in the list of processes
    env = {**environ, "MYSQL_PWD": conf.get("password", "")}
    try:
        # the dump has the hashes of passwords, only the owner reads it
        os.close(os.open(target, os.O_WRONLY | os.O_CREAT, 0o600))
        subprocess.run(command, env=env, check=True)  # noqa: S603
    except (OSError, subprocess.CalledProcessError) as err:
        target.unlink(missing_ok=True)
        msg = f"The backup failed: {err}"
        raise CtlError(msg) from err


def backup_name(conf: dict, directory: str) -> Path:
    """Return the name of the backup file."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(directory) / f"{conf['database']}-{stamp}.sql"


# commands

def read_password(args) -> str:
    """Return the password from the terminal or the standard input."""
    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass("Password: ")
        if password != getpass("Again: "):
            msg = "The passwords differ."
            raise CtlError(msg)
    if not password:
        msg = "The password is empty."
        raise CtlError(msg)
    return password


def cmd_app_version(args, out) -> int:
    """Print the version of the code and of the schema it needs."""
    del args
    out(f"{__version__} (database schema {code_schema_version()})")
    return 0


def cmd_db_version(args, out) -> int:
    """Print the version of the database schema."""
    with database(args) as conn:
        out(db_version(conn))
    return 0


def cmd_db_status(args, out) -> int:
    """Compare the database schema with the code, exit 1 if they differ."""
    with database(args) as conn:
        current = db_version(conn)
        waiting = [version for version, _ in pending(conn)]
    out(f"code: {__version__}")
    out(f"database: {current}")
    if release(current) > release(code_schema_version()):
        out("the database is newer than the code")
        return 1
    if waiting:
        out("pending migrations: " + ", ".join(waiting))
        out("run: poleomctl db:upgrade")
        return 1
    out("the database is up to date")
    return 0


def cmd_db_backup(args, out) -> int:
    """Dump the database to a file."""
    conf = db_conf(args.db, args.ini)
    target = Path(args.file) if args.file else backup_name(conf, ".")
    backup(conf, target)
    out(f"backup: {target}")
    return 0


def cmd_db_upgrade(args, out) -> int:
    """Back up the database and run the pending migrations."""
    conf = db_conf(args.db, args.ini)
    with database(args) as conn:
        if not pending(conn):
            out("the database is up to date")
            return 0
        # no open transaction, it would hold a lock against the dump
        conn.rollback()
        if not args.no_backup:
            target = backup_name(conf, args.backup_dir)
            backup(conf, target)
            out(f"backup: {target}")
        for version in upgrade(conn):
            out(f"upgraded to {version}")
    return 0


def cmd_user_password_sql(args, out) -> int:
    """Print SQL statements which set a password."""
    # ruff: noqa: S608
    hashed = password_hash(read_password(args), args.rounds)
    out("-- First setup")
    out(f"UPDATE users SET password='{hashed}', email='your@login' "
        f"WHERE email='{ROOT}';")
    out("-- Password reset")
    out(f"UPDATE users SET password='{hashed}' WHERE email='your@login';")
    return 0


def cmd_user_set_password(args, out) -> int:
    """Set the password of a user, ``root@localhost`` by default."""
    hashed = password_hash(read_password(args), args.rounds)
    with database(args) as conn, conn.cursor() as cur:
        try:
            cur.execute("UPDATE users SET password=%(password)s, "
                        "email=%(new)s WHERE email=%(email)s",
                        {"password": hashed, "email": args.email,
                         "new": args.new_email or args.email})
        except IntegrityError as err:
            msg = f"The e-mail {args.new_email} is used already."
            raise CtlError(msg) from err
        changed = cur.rowcount
        conn.commit()
    if not changed:
        msg = f"No user with the e-mail {args.email}."
        raise CtlError(msg)
    out(f"the password of {args.new_email or args.email} is set")
    return 0


def bcrypt_rounds(value: str) -> int:
    """Return the number of rounds of bcrypt, 4 to 31."""
    try:
        number = int(value)
    except ValueError:
        number = 0
    if not 4 <= number <= 31:  # noqa: PLR2004
        msg = "must be a number from 4 to 31"
        raise ArgumentTypeError(msg)
    return number


def parser() -> ArgumentParser:
    """Return the parser of the command line."""
    root = ArgumentParser(
        prog="poleomctl", description=__doc__.split("\n\n", maxsplit=1)[0])
    root.add_argument("--db", metavar="DSN",
                      help="mysql://user:password@host:port/database")
    root.add_argument("--ini", metavar="FILE",
                      help="uWSGI ini file with env = app_db=... "
                      "(default: the app_db variable)")
    sub = root.add_subparsers(dest="command", metavar="COMMAND", required=True)

    def add(name, func):
        item = sub.add_parser(name, help=func.__doc__,
                              description=func.__doc__)
        item.set_defaults(func=func)
        return item

    add("app:version", cmd_app_version)
    add("db:version", cmd_db_version)
    add("db:status", cmd_db_status)
    item = add("db:backup", cmd_db_backup)
    item.add_argument("file", nargs="?",
                      help="default: ./<database>-<time>.sql")
    item = add("db:upgrade", cmd_db_upgrade)
    item.add_argument("--no-backup", action="store_true",
                      help="do not dump the database before the upgrade")
    item.add_argument("--backup-dir", default=".", metavar="DIR",
                      help="where to write the dump (default: .)")
    item = add("user:password-sql", cmd_user_password_sql)
    item = add("user:set-password", cmd_user_set_password)
    item.add_argument("--email", default=ROOT,
                      help=f"user to change (default: {ROOT})")
    item.add_argument("--new-email", metavar="EMAIL",
                      help="change the e-mail as well (the first setup)")
    for item in (sub.choices["user:password-sql"],
                 sub.choices["user:set-password"]):
        item.add_argument("--password-stdin", action="store_true",
                          help="read the password from the standard input")
        item.add_argument("--rounds", type=bcrypt_rounds, default=12,
                          help="rounds of the hashing (default: 12)")
    return root


def main(argv: list[str] | None = None, out=print) -> int:
    """Run the command, return the exit code."""
    args = parser().parse_args(argv)
    try:
        return args.func(args, out)
    except CtlError as err:
        out(f"poleomctl: {err}")
        return 2


def run() -> None:  # pragma: no cover
    """Entry point of the script."""
    raise SystemExit(main())


if __name__ == "__main__":  # pragma: no cover - python -m poleom.ctl
    run()
