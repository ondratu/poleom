"""Integrity tests of the ChangeRequest model with SQLite database."""
from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from poleom.lib.change_request import ChangeRequest


@pytest.fixture
def user(make_user):
    return make_user()


def test_create_and_get(db, user):
    request = ChangeRequest.create(
        db, user.id, ChangeRequest.State.PASSWORD, {"request_ip": "::1"})

    stored = ChangeRequest.get(db, request.hexdigest)
    assert stored is not None
    assert stored.user_id == user.id
    assert stored.state is ChangeRequest.State.PASSWORD
    assert stored.data == {"request_ip": "::1"}
    assert stored.accepted is None
    assert ChangeRequest.get(db, "missing") is None


def test_accept(db, user):
    request = ChangeRequest.create(
        db, user.id, ChangeRequest.State.REGISTER, {})
    request.accept(db)

    stored = ChangeRequest.get(db, request.hexdigest)
    assert stored is not None
    assert stored.accepted is not None


@pytest.mark.parametrize(("state", "subject"), [
    (ChangeRequest.State.REGISTER, "Sign up to"),
    (ChangeRequest.State.PASSWORD, "Reset password request"),
    (ChangeRequest.State.INFO_CHANGED, "Credentials for"),
    (ChangeRequest.State.INFO_BANNED, "was banned"),
    (ChangeRequest.State.INFO_ACTIVATED, "is enabled"),
    (ChangeRequest.State.INFO_DELETED, "was deleted"),
])
def test_send_email(db, user, state, subject):
    request = ChangeRequest.create(
        db, user.id, state, {"request_ip": "::1", "request_browser": "x"})
    smtp = MagicMock()

    request.send_email(smtp, user, "https://forum.example.com")

    smtp.send_email_txt.assert_called_once()
    mail_subject, recipient, body = smtp.send_email_txt.call_args.args
    assert subject in mail_subject
    assert recipient == user.email
    assert body.strip()


def test_send_email_with_unknown_state(db, user):
    request = ChangeRequest.create(
        db, user.id, ChangeRequest.State.REGISTER, {})
    request.state = None  # type: ignore[assignment]

    with pytest.raises(RuntimeError):
        request.send_email(MagicMock(), user)


def test_times_are_utc(db, user):
    request = ChangeRequest.create(
        db, user.id, ChangeRequest.State.PASSWORD, {})
    request.accept(db)

    stored = ChangeRequest.get(db, request.hexdigest)
    assert stored.created.utcoffset() == timedelta(0)
    assert stored.accepted.utcoffset() == timedelta(0)
    assert not stored.expired(60)
