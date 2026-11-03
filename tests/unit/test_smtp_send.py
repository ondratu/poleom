"""Unit tests of sending emails with mocked SMTP connection."""
from email import message_from_string
from smtplib import SMTPException
from unittest.mock import MagicMock

import pytest

from poleom.lib.smtp import Smtp


@pytest.fixture
def smtp():
    smtp = Smtp("smtp://user:secret@mail.example.com:25/forum@example.com")
    smtp._class = MagicMock()
    return smtp


def sent(smtp):
    """Return connection mock and parsed message which was sent."""
    conn = smtp._class.return_value
    sender, recipient, raw = conn.sendmail.call_args.args
    return conn, sender, recipient, message_from_string(raw)


def test_send_txt(smtp):
    smtp.send_email_txt("Subject", "to@example.com", "Body")

    conn, sender, recipient, msg = sent(smtp)
    assert sender == "forum@example.com"
    assert recipient == "to@example.com"
    assert msg["Subject"] == "Subject"
    assert msg["X-Mailer"] == smtp.xmailer
    assert "Reply-To" not in msg
    conn.login.assert_called_once_with("user", "secret")
    conn.close.assert_called_once_with()


def test_send_txt_options(smtp):
    smtp.send_email_txt("Subject", "to@example.com", "Body",
                        sender="other@example.com",
                        reply="reply@example.com", xmailer="Mailer")

    _, sender, _, msg = sent(smtp)
    assert sender == "other@example.com"
    assert msg["Reply-To"] == "reply@example.com"
    assert msg["X-Mailer"] == "Mailer"


def test_send_without_login():
    smtp = Smtp("smtp://mail.example.com/forum@example.com")
    smtp._class = MagicMock()

    smtp.send_email_txt("Subject", "to@example.com", "Body")

    smtp._class.return_value.login.assert_not_called()


def test_send_txt_failure_closes_connection(smtp):
    conn = smtp._class.return_value
    conn.sendmail.side_effect = SMTPException

    with pytest.raises(SMTPException):
        smtp.send_email_txt("Subject", "to@example.com", "Body")
    conn.close.assert_called_once_with()


def test_send_alternative(smtp):
    smtp.send_email_alternative("Subject", "to@example.com", "Text",
                                "<p>Html</p>", reply="reply@example.com")

    conn, _, _, msg = sent(smtp)
    assert msg.get_content_type() == "multipart/alternative"
    assert [part.get_content_type() for part in msg.get_payload()] == [
        "text/plain", "text/html"]
    assert msg["Reply-To"] == "reply@example.com"
    conn.close.assert_called_once_with()


def test_send_alternative_failure_closes_connection(smtp):
    conn = smtp._class.return_value
    conn.sendmail.side_effect = SMTPException

    with pytest.raises(SMTPException):
        smtp.send_email_alternative("S", "to@example.com", "T", "<p>H</p>")
    conn.close.assert_called_once_with()


def test_connection_failure_is_raised(smtp):
    smtp._class.side_effect = SMTPException

    with pytest.raises(SMTPException):
        smtp.send_email_txt("Subject", "to@example.com", "Body")


def test_send_alternative_without_login():
    smtp = Smtp("smtp://mail.example.com/forum@example.com")
    smtp._class = MagicMock()

    smtp.send_email_alternative("S", "to@example.com", "T", "<p>H</p>")

    smtp._class.return_value.login.assert_not_called()
