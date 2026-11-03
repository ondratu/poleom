"""Unit tests of the view helpers and Jinja filters."""
from datetime import UTC, datetime, timedelta, timezone

import pytest
from dateutil.tz import gettz

from poleom.lib import view
from poleom.lib.settings import Language
from poleom.lib.view import (
    hbytes,
    jinja_rst2html,
    local,
    md2rst,
    parse_system_messages,
    render_template,
    rfc822,
    rst2html,
    sha256,
)


def test_md2rst():
    assert "**bold**" in md2rst("**bold**")


def test_jinja_rst2html():
    assert "<em>x</em>" in jinja_rst2html("*x*")


def test_rst2html_title_is_h3():
    body, _ = rst2html("Title\n=====\n\ntext\n")
    assert body.startswith("<h3>Title</h3>")


def test_rst2html_footnotes():
    body, _ = rst2html("Text [1]_\n\n.. [1] Note\n")
    assert "Note" in body


def test_rst2html_system_messages():
    body, messages = rst2html("*broken", system_messages=True)
    assert "Inline emphasis" in messages
    assert "System message" in body


@pytest.mark.parametrize("out", [
    "<string>:1: (WARNING/2) Inline emphasis start-string",
    b"<string>:1: (WARNING/2) Inline emphasis start-string",
])
def test_parse_system_messages(out):
    assert parse_system_messages(out) == (
        ("1", "WARNING", "2", "Inline emphasis start-string"),)


def test_parse_system_messages_ignores_other_lines():
    assert not parse_system_messages("nothing\nto see")


def test_sha256():
    assert sha256("") == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")


def test_local():
    value = datetime(2026, 1, 1, 12, tzinfo=UTC)
    assert local(value, gettz("Europe/Prague")).hour == 13


def test_rfc822():
    value = datetime(2026, 1, 1, 12, tzinfo=UTC)
    assert rfc822(value) == "Thu, 01 Jan 2026 12:00:00 +0000"
    # naive datetime is expected in UTC
    assert rfc822(value.replace(tzinfo=None)) == rfc822(value)
    other = value.astimezone(timezone(timedelta(hours=2)))
    assert rfc822(other) == "Thu, 01 Jan 2026 14:00:00 +0200"


@pytest.mark.parametrize(("value", "result"), [
    (0, "0.0B"),
    (1000, "1000.0B"),
    (1500, "1.5kB"),
    (2_500_000, "2.5MB"),
    (3_000_000_000, "3.0GB"),
])
def test_hbytes(value, result):
    assert hbytes(value) == result


CONTEXT = {
    "me": None,
    "auth": {"local": True, "login_url": "/login", "signup_url": None,
             "profile_url": None},
    "lang": "en",
    "languages": {"en": Language("en", "en_US", "English", True)},
}


def test_render_template():
    assert render_template("not-found.html", **CONTEXT)


def test_render_template_debug():
    view.app.debug = True
    try:
        assert render_template("not-found.html", **CONTEXT)
    finally:
        view.app.debug = False
