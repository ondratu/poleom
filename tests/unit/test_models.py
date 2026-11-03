"""Unit tests for the Section, Topic, Post, Language and ChangeRequest."""
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import ClassVar

from poleom.lib.attachment import Attachment, File
from poleom.lib.change_request import ChangeRequest
from poleom.lib.post import Post
from poleom.lib.section import Section
from poleom.lib.settings import Language
from poleom.lib.topic import Topic

NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


class TestSection:
    """Section model."""

    def test_path_from_title(self):
        section = Section(1, "General Chat & Fun!", "en", "")
        assert section.path == "general-chat-fun"

    def test_path_is_kept(self):
        section = Section(1, "General", "en", "", path="custom")
        assert section.path == "custom"

    def test_from_row(self):
        section = Section.from_row({
            "section_id": 3, "title": "Chat", "lang": "en",
            "description": "Talk", "state": "LOCKED", "private": 1,
            "path": "chat", "weight": 5})
        assert section.id == 3
        assert section.state is Section.State.LOCKED
        assert section.private
        assert section.weight == 5

    def test_to_dict(self):
        values = Section(3, "Chat", "en", "Talk").to_dict()
        assert values == {
            "id": 3, "title": "Chat", "lang": "en", "path": "chat",
            "description": "Talk", "state": Section.State.OPEN, "weight": 0,
            "private": False}


class TestTopic:
    """Topic model."""

    def test_from_row(self):
        topic = Topic.from_row({
            "topic_id": 4, "section_id": 3, "title": "Hello",
            "path": "hello", "state": "ARCHIVED", "pinned": 1})
        assert topic.id == 4
        assert topic.state is Topic.State.ARCHIVED
        assert topic.pinned
        assert topic.count == 0

    def test_to_dict(self):
        values = Topic(4, 3, "Hello", "hello").to_dict()
        assert values == {
            "id": 4, "section_id": 3, "title": "Hello", "path": "hello",
            "state": Topic.State.OPEN, "pinned": False}


class TestPost:
    """Post model."""

    ROW: ClassVar[dict] = {
        "post_id": 9, "topic_id": 4, "parent": None, "created": NOW,
        "modified": None, "user_id": 1, "hexdigest": "abc123", "body": "Hi"}

    def test_from_row_and_to_dict(self):
        post = Post.from_row(self.ROW)
        assert post.id == 9
        assert post.to_dict() == {
            "id": 9, "topic_id": 4, "parent": None, "created": NOW,
            "modified": None, "user_id": 1, "hexdigest": "abc123",
            "body": "Hi"}


class TestLanguage:
    """Language model."""

    ROW: ClassVar[dict] = {
        "lang": "cs", "locale": "cs_CZ", "language": "Česky", "active": 1}

    def test_from_row(self):
        language = Language.from_row(self.ROW)
        assert language.lang == "cs"
        assert language.locale == "cs_CZ"
        assert language.language == "Česky"
        assert language.active

    def test_to_dict(self):
        assert Language.from_row(self.ROW).to_dict() == {
            "lang": "cs", "locale": "cs_CZ", "language": "Česky",
            "active": 1}


class TestChangeRequest:
    """ChangeRequest model."""

    def test_from_row_and_to_dict(self):
        request = ChangeRequest.from_row({
            "user_id": 1, "created": NOW, "accepted": None,
            "hexdigest": "abc", "state": "PASSWORD",
            "data": '{"email": "a@b.cz"}'})
        assert request.state is ChangeRequest.State.PASSWORD
        assert request.data == {"email": "a@b.cz"}
        assert request.to_dict()["accepted"] is None


class TestFile:
    """File helper."""

    def test_length(self):
        assert File(BytesIO(b"abcdef"), "a.txt", "text/plain").length == 6

    def test_length_keeps_position(self):
        stream = BytesIO(b"abcdef")
        stream.read(4)
        assert File(stream, "a.txt", "text/plain").length == 6
        assert stream.tell() == 4


class TestAttachment:
    """Attachment model."""

    ROW: ClassVar[dict] = {
        "post_id": 9, "uploaded": NOW, "mime_type": "image/png",
        "file_name": "a.png", "hexdigest": "0123456789ab", "data": "{}"}

    def test_from_row(self):
        attachment = Attachment.from_row(self.ROW)
        assert attachment.file_name == "a.png"
        assert not attachment.data
        assert attachment.to_dict()["hexdigest"] == "0123456789ab"

    def test_path_is_sharded_by_hexdigest(self, monkeypatch):
        monkeypatch.setattr("poleom.lib.attachment.app.attachments", "/data")
        assert Attachment.from_row(self.ROW).path == "/data/012/345"


class TestChangeRequestExpiration:
    """Time in the database is UTC, the expiration must not depend on TZ."""

    @staticmethod
    def make(age):
        return ChangeRequest(1, datetime.now(UTC) - age, None, "x",
                             ChangeRequest.State.PASSWORD, {})

    def test_not_expired(self):
        assert not self.make(timedelta(hours=1)).expired(7200)

    def test_expired(self):
        assert self.make(timedelta(hours=1)).expired(1800)

    def test_row_time_is_utc(self):
        row = {"user_id": 1, "created": datetime(2026, 1, 1),
               "accepted": None, "hexdigest": "x", "state": "PASSWORD",
               "data": "{}"}

        assert ChangeRequest.from_row(row).created.tzinfo is UTC
