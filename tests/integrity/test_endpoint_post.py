"""Integrity tests of the endpoints in post.py."""
import os

import pytest

from poleom.lib.attachment import Attachment
from poleom.lib.pager import Pager
from poleom.lib.post import Post
from poleom.lib.section import Section
from poleom.lib.topic import Topic

TOPIC_URL = "/en/general/hello-topic"


@pytest.fixture
def author(make_user):
    return make_user("author")


@pytest.fixture
def topic(db):
    general = Section.find(db, "en", "general")
    return Topic.create(db, general.id, "Hello topic")


@pytest.fixture
def post(db, topic, author):
    return Post.create(db, topic.id, author.id, "First post")


class TestCreatePost:
    def test_requires_login(self, client, topic):
        result = client.post(TOPIC_URL, form={"body": "x"}, files=[])

        assert result.status == 401

    def test_create(self, client, db, topic, author):
        result = client.login(author).post(
            TOPIC_URL, form={"body": "Answer"}, files=[])

        assert result.status == 302
        assert Post.count(db, topic.id) == 1
        created = next(Post.list(db, Pager(), topic.id))
        assert created.body == "Answer"
        assert result.headers["Location"].endswith("#" + created.hexdigest)

    def test_create_with_parent(self, client, db, post, author):
        client.login(author).post(
            TOPIC_URL, form={"body": "Reply", "parent": post.hexdigest},
            files=[])

        reply = Post.get(db, post.id + 1)
        assert reply.parent == post.hexdigest

    def test_create_with_attachment(self, client, db, topic, author):
        result = client.login(author).post(
            TOPIC_URL, form={"body": "See file"},
            files=[("note.txt", b"content", "text/plain")])

        assert result.status == 302
        stored = list(Attachment.list(db, 1))
        assert [item.file_name for item in stored] == ["note.txt"]

    def test_empty_body_shows_form_again(self, client, db, post, author):
        result = client.login(author).post(
            TOPIC_URL, form={"body": " "}, files=[])

        assert result.status == 200
        assert 'class="error"' in result.text
        assert Post.count(db, post.topic_id) == 1

    def test_missing_topic(self, client, author):
        result = client.login(author).post(
            "/en/general/missing", form={"body": "x"}, files=[])

        assert result.status == 404


class TestFormPost:
    URL = TOPIC_URL + "/{}"

    def test_form(self, client, post, author):
        result = client.login(author).get(self.URL.format(post.hexdigest))

        assert result.status == 200
        assert "First post" in result.text

    def test_requires_login(self, client, post):
        assert client.get(self.URL.format(post.hexdigest)).status == 401

    def test_missing_post(self, client, topic, author):
        assert client.login(author).get(
            self.URL.format("0" * 16)).status == 404

    def test_only_author_can_edit(self, client, post, make_user):
        other = make_user("other")

        assert client.login(other).get(
            self.URL.format(post.hexdigest)).status == 403


class TestUpdatePost:
    URL = TOPIC_URL + "/{}"

    def test_update(self, client, db, post, author):
        result = client.login(author).post(
            self.URL.format(post.hexdigest),
            form={"body": "Edited"}, files=[])

        assert result.status == 302
        assert result.headers["Location"].endswith("#" + post.hexdigest)
        stored = Post.get(db, post.id)
        assert stored.body == "Edited"
        assert stored.modified is not None

    def test_update_keeps_offset(self, client, post, author):
        result = client.login(author).post(
            self.URL.format(post.hexdigest), query={"offset": 10},
            form={"body": "Edited"}, files=[])

        assert "?offset=10#" in result.headers["Location"]

    def test_update_with_attachment(self, client, db, post, author):
        client.login(author).post(
            self.URL.format(post.hexdigest), form={"body": "Edited"},
            files=[("note.txt", b"content", "text/plain")])

        assert len(list(Attachment.list(db, post.id))) == 1

    def test_empty_body_shows_form_again(self, client, db, post, author):
        result = client.login(author).post(
            self.URL.format(post.hexdigest), form={"body": ""}, files=[])

        assert result.status == 200
        assert 'class="error"' in result.text
        assert Post.get(db, post.id).body == "First post"

    def test_missing_post(self, client, topic, author):
        result = client.login(author).post(
            self.URL.format("0" * 16), form={"body": "x"}, files=[])

        assert result.status == 404

    def test_only_author_can_update(self, client, post, make_user):
        other = make_user("other")

        result = client.login(other).post(
            self.URL.format(post.hexdigest), form={"body": "x"}, files=[])

        assert result.status == 403


class TestGetPost:
    def test_get(self, client, post, author):
        result = client.login(author).get(f"/p/{post.hexdigest}")

        assert result.status == 200
        data = result.json()["post"]
        assert data["body"] == "First post"
        assert isinstance(data["created"], int)
        assert "modified" not in data or data["modified"] is None

    def test_get_modified(self, client, db, post, author):
        post.update(db)

        data = client.login(author).get(f"/p/{post.hexdigest}").json()["post"]

        assert isinstance(data["modified"], int)

    def test_requires_login(self, client, post):
        assert client.get(f"/p/{post.hexdigest}").status == 401

    def test_missing(self, client, author):
        assert client.login(author).get("/p/" + "a" * 16).status == 404


class TestAttachments:
    @pytest.fixture
    def attachment(self, client, db, post, author):
        client.login(author).post(
            TOPIC_URL + "/" + post.hexdigest, form={"body": "Edited"},
            files=[("note.txt", b"0123456789", "text/plain")])
        client.cookie = ""
        return next(Attachment.list(db, post.id))

    def test_download(self, client, attachment):
        result = client.get(f"/a/{attachment.hexdigest}")

        assert result.status == 200
        assert result.body == b"0123456789"
        assert result.headers["Content-Type"].startswith("text/plain")

    def test_download_with_file_name(self, client, attachment):
        result = client.get(f"/a/{attachment.hexdigest}/note.txt")

        assert result.body == b"0123456789"

    def test_wrong_file_name(self, client, attachment):
        result = client.get(f"/a/{attachment.hexdigest}/other.txt")

        assert result.status == 404

    def test_missing(self, client):
        assert client.get("/a/" + "a" * 16).status == 404

    def test_not_modified_by_etag(self, client, attachment):
        etag = client.get(f"/a/{attachment.hexdigest}").headers["E-Tag"]

        result = client.get(f"/a/{attachment.hexdigest}",
                            headers={"If-None-Match": etag})

        assert result.status == 304

    def test_not_modified_by_date(self, client, attachment):
        modified = client.get(
            f"/a/{attachment.hexdigest}").headers["Last-Modified"]

        result = client.get(f"/a/{attachment.hexdigest}",
                            headers={"If-Modified-Since": modified})

        assert result.status == 304

    def test_range(self, client, attachment):
        result = client.get(f"/a/{attachment.hexdigest}",
                            headers={"Range": "bytes=2-4"})

        assert result.status == 206
        assert result.body == b"234"

    def test_delete(self, client, db, attachment, author):
        path = os.path.join(attachment.path, attachment.hexdigest)

        result = client.login(author).delete(f"/a/{attachment.hexdigest}")

        assert result.status == 204
        assert Attachment.get(db, attachment.hexdigest) is None
        assert not os.path.exists(path)

    def test_delete_requires_login(self, client, attachment):
        assert client.delete(f"/a/{attachment.hexdigest}").status == 401

    def test_delete_only_author(self, client, attachment, make_user):
        other = make_user("other")

        result = client.login(other).delete(f"/a/{attachment.hexdigest}")

        assert result.status == 403

    def test_delete_missing(self, client, author):
        assert client.login(author).delete("/a/" + "a" * 16).status == 404
