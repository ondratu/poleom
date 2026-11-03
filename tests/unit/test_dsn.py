"""Tests of the Data Source Name parser."""
import pytest

from poleom.lib.dsn import parse_dsn


def test_full_dsn():
    assert parse_dsn("mysql://u:p@db.local:3307/forum::latin1") == {
        "host": "db.local", "port": 3307, "database": "forum",
        "charset": "latin1", "user": "u", "password": "p"}


def test_defaults():
    assert parse_dsn("mysql://u/forum") == {
        "host": "localhost", "port": 3306, "database": "forum",
        "charset": "utf8mb4", "user": "u"}


def test_invalid_dsn():
    with pytest.raises(ValueError, match="app_db"):
        parse_dsn("nonsense")
