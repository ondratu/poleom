"""Check the SQL migrations of the database."""
import re
from importlib.resources import files
from pathlib import Path

import poleom

MIGRATIONS = files("poleom").joinpath("mysql", "migrations")
NAME = re.compile(r"(\d+)\.(\d+)\.(\d+)\.sql")


def version(text):
    return tuple(int(part) for part in re.match(r"\d+\.\d+\.\d+", text)
                 .group().split("."))


def test_migrations_are_named_by_released_version():
    names = [item.name for item in MIGRATIONS.iterdir()]

    assert names
    for name in names:
        assert NAME.fullmatch(name), name
        assert version(name) <= version(poleom.__version__), name


def test_migrations_are_documented_in_changelog():
    text = (Path(__file__).parent.parent / "ChangeLog.rst").read_text(
        encoding="utf-8")

    for item in MIGRATIONS.iterdir():
        assert item.name in text


def test_init_sql_has_the_version_of_the_last_migration():
    last = max((item.name[:-4] for item in MIGRATIONS.iterdir()),
               key=version)

    for database in ("mysql", "sqlite"):
        text = files("poleom").joinpath(database, "init.sql").read_text(
            encoding="utf-8")
        assert re.search(rf"schema_version[\"'], [\"']{last}[\"']", text)
