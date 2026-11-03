"""Integrity tests of the endpoints in topic.py."""
import pytest

from poleom.lib.post import Post
from poleom.lib.section import Section
from poleom.lib.topic import Topic
from poleom.lib.user import User

REFERER = {"Referer": "http://forum.example.com/en/general"}


@pytest.fixture
def general(db):
    return Section.find(db, "en", "general")


@pytest.fixture
def topic(db, general, make_user):
    author = make_user("author")
    created = Topic.create(db, general.id, "Hello topic")
    Post.create(db, created.id, author.id, "First post")
    return created


class TestCreateTopic:
    def test_requires_login(self, client):
        result = client.post("/en/general", form={"title": "T", "body": "B"})

        assert result.status == 401

    def test_create(self, client, db, general, make_user):
        member = make_user()

        result = client.login(member).post(
            "/en/general", form={"title": "New topic", "body": "Text"})

        assert result.status == 302
        assert result.headers["Location"] == "/en/general/new-topic"
        created = Topic.find(db, general.id, "new-topic")
        assert created is not None
        assert Post.count(db, created.id) == 1

    def test_missing_section(self, client, make_user):
        result = client.login(make_user()).post("/en/missing", form={})

        assert result.status == 404

    def test_archived_section(self, client, db, general, make_user):
        general.state = Section.State.ARCHIVED
        general.update(db)

        result = client.login(make_user()).post(
            "/en/general", form={"title": "T", "body": "B"})

        assert result.status == 410
        assert "Archived" in result.text

    def test_locked_section_only_for_moderator(self, client, db, general,
                                               make_user):
        general.state = Section.State.LOCKED
        general.update(db)
        form = {"title": "T", "body": "B"}

        assert client.login(make_user()).post(
            "/en/general", form=form).status == 403
        moderator = make_user("moderator", User.Role.MODERATOR)
        assert client.login(moderator).post(
            "/en/general", form=form).status == 302

    @pytest.mark.parametrize(("form", "fragment"), [
        ({"title": "", "body": "B"}, "empty_topic_title"),
        ({"title": "T", "body": ""}, "empty_topic_body"),
    ])
    def test_empty_values(self, client, make_user, form, fragment):
        result = client.login(make_user()).post(
            "/en/general", form=form, headers=REFERER)

        assert result.status == 302
        assert result.headers["Location"].endswith("#" + fragment)


class TestTopicDetail:
    def test_detail(self, client, topic):
        result = client.get("/en/general/hello-topic")

        assert result.status == 200
        assert "First post" in result.text
        assert "ETag" in result.headers

    def test_etag_not_modified(self, client, topic):
        etag = client.get("/en/general/hello-topic").headers["ETag"]

        result = client.get("/en/general/hello-topic",
                            headers={"If-None-Match": etag})

        assert result.status == 304

    def test_etag_depends_on_user(self, client, topic, make_user):
        etag = client.get("/en/general/hello-topic").headers["ETag"]

        result = client.login(make_user()).get(
            "/en/general/hello-topic", headers={"If-None-Match": etag})

        assert result.status == 200

    @pytest.mark.parametrize("path", [
        "/en/missing/hello-topic",
        "/en/general/missing",
        "/en/missing/hello-topic/rss",
        "/en/general/missing/rss",
    ])
    def test_not_found(self, client, topic, path):
        assert client.get(path).status == 404

    def test_private_section_is_not_found(self, client, db, make_user):
        private = Section(0, "Secret", "en", "Private", private=True)
        private.create(db)
        Topic.create(db, private.id, "Hidden")

        assert client.get("/en/secret/hidden").status == 404

    def test_rss(self, client, topic):
        result = client.get("/en/general/hello-topic/rss")

        assert result.status == 200
        assert "First post" in result.text
