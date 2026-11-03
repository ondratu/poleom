"""Integrity tests of the Attachment model with SQLite database."""
import os
from io import BytesIO

import pytest

from poleom.lib.attachment import Attachment, File


@pytest.fixture
def attachment(db):
    file = File(BytesIO(b"content"), "note.txt", "text/plain")
    return Attachment.create(db, 1, file)


def test_create_stores_file(attachment):
    assert attachment.data == {"length": 7}
    path = os.path.join(attachment.path, attachment.hexdigest)
    with open(path, "rb") as stored:
        assert stored.read() == b"content"


def test_get(db, attachment):
    stored = Attachment.get(db, attachment.hexdigest)

    assert stored is not None
    assert stored.file_name == "note.txt"
    assert stored.mime_type == "text/plain"
    assert stored.data == {"length": 7}
    assert Attachment.get(db, "missing") is None


def test_list(db, attachment):
    other = Attachment.create(
        db, 2, File(BytesIO(b"x"), "other.txt", "text/plain"))

    assert [item.hexdigest for item in Attachment.list(db, 1)] == [
        attachment.hexdigest]
    assert [item.hexdigest for item in Attachment.list(db, 2)] == [
        other.hexdigest]


def test_delete_removes_file_and_record(db, attachment):
    path = os.path.join(attachment.path, attachment.hexdigest)
    Attachment.delete(db, attachment.hexdigest)

    assert not os.path.exists(path)
    assert Attachment.get(db, attachment.hexdigest) is None
