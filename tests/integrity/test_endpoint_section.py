"""Integrity tests of the endpoints in section.py."""
import pytest

from poleom.lib.post import Post
from poleom.lib.section import Section, SectionUser
from poleom.lib.topic import Topic
from poleom.lib.user import User


@pytest.fixture
def moderator(make_user):
    return make_user("moderator", User.Role.MODERATOR)


@pytest.fixture
def admin(make_user):
    return make_user("boss", User.Role.ADMIN)


@pytest.fixture
def general(db):
    return Section.find(db, "en", "general")


@pytest.fixture
def private(db):
    section = Section(0, "Secret", "en", "Private", private=True)
    section.create(db)
    return section


def add_topic(db, section, user, title="Hello"):
    topic = Topic.create(db, section.id, title)
    Post.create(db, topic.id, user.id, "First post")
    return topic


class TestSectionsRoot:
    def test_lists_sections(self, client):
        result = client.get("/en/")

        assert result.status == 200
        assert "General" in result.text
        assert "Všeobecné" not in result.text

    def test_unknown_language(self, client):
        assert client.get("/pl/").status == 404

    @pytest.mark.usefixtures("private")
    def test_private_section_is_hidden(self, client):
        assert "Secret" not in client.get("/en/").text

    def test_private_section_for_member(self, client, db, make_user,
                                        private):
        member = make_user()
        SectionUser.add(db, private.id, member.id)

        assert "Secret" in client.login(member).get("/en/").text

    @pytest.mark.usefixtures("private")
    def test_admin_sees_all(self, client, admin):
        assert "Secret" in client.login(admin).get("/en/").text


class TestSectionDetail:
    def test_detail(self, client, db, general, make_user):
        add_topic(db, general, make_user(), "Hello topic")

        result = client.get("/en/general")

        assert result.status == 200
        assert "Hello topic" in result.text
        assert "ETag" in result.headers

    def test_etag_not_modified(self, client, db, general, make_user):
        add_topic(db, general, make_user())
        etag = client.get("/en/general").headers["ETag"]

        result = client.get("/en/general", headers={"If-None-Match": etag})

        assert result.status == 304

    def test_not_found(self, client):
        assert client.get("/en/missing").status == 404

    @pytest.mark.usefixtures("private")
    def test_private_is_not_found_for_anonymous(self, client):
        assert client.get("/en/secret").status == 404

    def test_private_for_member_of_section(self, client, db, private,
                                           make_user):
        member = make_user()
        SectionUser.add(db, private.id, member.id)

        assert client.login(member).get("/en/secret").status == 200


class TestSectionRss:
    def test_section_rss(self, client, db, general, make_user):
        add_topic(db, general, make_user(), "Hello topic")

        result = client.get("/en/general/rss")

        assert result.status == 200
        assert "Hello topic" in result.text

    def test_not_found(self, client):
        assert client.get("/en/missing/rss").status == 404

    def test_lang_rss(self, client, db, general, make_user):
        add_topic(db, general, make_user(), "Hello topic")

        result = client.get("/en/rss")

        assert result.status == 200
        assert "Hello topic" in result.text

    def test_lang_rss_unknown_language(self, client):
        assert client.get("/pl/rss").status == 404

    def test_lang_rss_for_logged_in_user(self, client, admin, db, private):
        add_topic(db, private, admin, "Secret topic")

        assert "Secret topic" not in client.get("/en/rss").text
        assert "Secret topic" in client.login(admin).get("/en/rss").text


class TestSectionAdministration:
    def test_list_requires_moderator(self, client, make_user):
        assert client.get("/sections").status == 401
        assert client.login(make_user()).get("/sections").status == 403

    def test_list(self, client, moderator):
        result = client.login(moderator).get("/sections")

        assert result.status == 200
        assert "General" in result.text

    def test_list_other_language(self, client, admin):
        result = client.login(admin).get("/sections", query={"lang": "cs"})

        assert "Všeobecné" in result.text

    def test_new_form(self, client, moderator):
        result = client.login(moderator).get("/sections/new")

        assert result.status == 200
        assert "New Section" in result.text

    def test_edit_form(self, client, moderator, general):
        result = client.login(moderator).get(f"/sections/{general.id}")

        assert result.status == 200
        assert "Edit Section" in result.text

    def test_edit_missing(self, client, moderator):
        assert client.login(moderator).get("/sections/9999").status == 404

    def test_create(self, client, db, moderator):
        result = client.login(moderator).post("/sections", form={
            "title": "News", "lang": "en", "description": "Fresh",
            "state": "OPEN"})

        assert result.status == 200
        created = Section.find(db, "en", "news")
        assert created is not None
        assert created.description == "Fresh"

    def test_create_duplicity(self, client, moderator, general):
        result = client.login(moderator).post("/sections", form={
            "title": "General", "lang": "en", "description": "Same",
            "state": "OPEN"})

        assert result.status == 200
        assert result.text.count('class="error"') >= 2

    def test_create_without_state(self, client, db, moderator):
        result = client.login(moderator).post("/sections", form={
            "title": "News", "lang": "en", "description": "Fresh"})

        assert result.status == 200
        assert Section.find(db, "en", "news") is None

    def test_create_with_errors(self, client, db, moderator):
        result = client.login(moderator).post("/sections", form={
            "title": "", "lang": "xx", "description": "", "state": "bad"})

        assert result.status == 200
        assert result.text.count('class="error"') >= 3
        assert Section.total(db) == 10

    def test_update(self, client, db, moderator, general):
        result = client.login(moderator).post(
            f"/sections/{general.id}", form={
                "title": "General", "lang": "en", "description": "Changed",
                "state": "LOCKED", "private": "on"})

        assert result.status == 200
        stored = Section.get(db, general.id)
        assert stored.description == "Changed"
        assert stored.state is Section.State.LOCKED
        assert stored.private

    def test_update_missing(self, client, moderator):
        result = client.login(moderator).post("/sections/9999", form={})

        assert result.status == 404

    def test_patch_state_and_private(self, client, db, moderator, general):
        result = client.login(moderator).patch(
            f"/sections/{general.id}",
            data={"state": "archived", "private": True})

        assert result.status == 200
        assert result.json()["section"]["state"] == "ARCHIVED"
        stored = Section.get(db, general.id)
        assert stored.state is Section.State.ARCHIVED
        assert stored.private

    def test_patch_weight_swaps_sections(self, client, db, moderator,
                                         general):
        ideas = Section.find(db, "en", "ideas")

        result = client.login(moderator).patch(
            f"/sections/{general.id}", data={"weight": 5})

        assert result.status == 200
        assert Section.get(db, general.id).weight == ideas.weight

    def test_patch_invalid_state(self, client, moderator, general):
        result = client.login(moderator).patch(
            f"/sections/{general.id}", data={"state": "bad"})

        assert result.status == 400

    def test_patch_invalid_weight(self, client, moderator, general):
        result = client.login(moderator).patch(
            f"/sections/{general.id}", data={"weight": "heavy"})

        assert result.status == 400

    def test_patch_missing(self, client, moderator):
        result = client.login(moderator).patch("/sections/9999", data={})

        assert result.status == 404


class TestSectionUsers:
    def test_users_requires_moderator(self, client, general, make_user):
        url = f"/sections/{general.id}/users"
        assert client.get(url).status == 401
        assert client.login(make_user()).get(url).status == 403

    def test_list_add_delete(self, client, db, moderator, general,
                             make_user):
        member = make_user("member")
        url = f"/sections/{general.id}/users"
        client.login(moderator)

        assert client.get(url).json() == {"users": []}
        assert client.post(f"{url}/{member.id}").status == 204
        assert client.get(url).json() == {
            "users": [{"user_id": member.id, "name": "member"}]}
        assert client.delete(f"{url}/{member.id}").status == 204
        assert not SectionUser.user_in(db, general.id, member.id)

    def test_add_twice_is_conflict(self, client, moderator, general,
                                   make_user):
        member = make_user("member")
        url = f"/sections/{general.id}/users/{member.id}"
        client.login(moderator)

        assert client.post(url).status == 204
        assert client.post(url).status == 409

    def test_missing_section(self, client, moderator):
        client.login(moderator)

        assert client.get("/sections/9999/users").status == 404
        assert client.post("/sections/9999/users/1").status == 404
        assert client.delete("/sections/9999/users/1").status == 404

    def test_missing_user(self, client, moderator, general):
        client.login(moderator)
        url = f"/sections/{general.id}/users/9999"

        assert client.post(url).status == 404
        assert client.delete(url).status == 404
