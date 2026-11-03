"""Unit tests for the SMTP data source name and the Email class."""
from smtplib import SMTP, SMTP_SSL

import pytest

from poleom.lib.smtp import Email, Smtp


def test_dsn_defaults():
    smtp = Smtp("smtp:///root@localhost")
    assert smtp.protocol == "smtp"
    assert smtp.host == "localhost"
    assert smtp.port == 25
    assert smtp.sender == "root@localhost"
    assert smtp.charset == "utf-8"
    assert smtp.user is None
    assert smtp.passwd is None
    assert smtp._class is SMTP


def test_dsn_full():
    smtp = Smtp("smtps://me:pa55word@mail.example.org:465/"
                "forum@example.org::latin2")
    assert smtp.protocol == "smtps"
    assert smtp.user == "me"
    assert smtp.passwd == "pa55word"
    assert smtp.host == "mail.example.org"
    assert smtp.port == 465
    assert smtp.sender == "forum@example.org"
    assert smtp.charset == "latin2"
    assert smtp._class is SMTP_SSL


@pytest.mark.parametrize("dsn", [
    "",
    "localhost",
    "http://localhost/root@localhost",
    "smtp:/root@localhost",
])
def test_dsn_invalid(dsn):
    with pytest.raises(ValueError, match="app_smtp"):
        Smtp(dsn)


def test_str_does_not_show_password():
    smtp = Smtp("smtps://me:pa55word@mail.example.org:465/forum@example.org")
    text = str(smtp)
    assert "pa55word" not in text
    assert text.startswith("smtps://me:")
    assert text.endswith("@mail.example.org:465/forum@example.org::utf-8")


def test_str_without_credentials():
    smtp = Smtp("smtp://localhost/root@localhost")
    assert str(smtp) == "smtp://localhost:25/root@localhost::utf-8"


@pytest.mark.parametrize("value", [
    "user@example.org",
    "first.last@sub.example.org",
    "a-b_c@example-site.cz",
])
def test_email_valid(value):
    assert Email.check(value)
    assert str(Email(value)) == value


@pytest.mark.parametrize("value", [
    "",
    "user",
    "user@",
    "@example.org",
    "us er@example.org",
    "user@example.org\nBcc: x@example.org",
])
def test_email_invalid(value):
    assert not Email.check(value)
    with pytest.raises(RuntimeError, match="not match as email"):
        Email(value)
