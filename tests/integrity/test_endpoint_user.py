"""Integrity tests of the endpoints in user.py."""
import re
from datetime import UTC, datetime, timedelta

import pytest

from poleom.lib.change_request import ChangeRequest
from poleom.lib.user import User

PASSWORD = "Str0ngPassw0rd"
NEW_PASSWORD = "N3wPassw0rd"


@pytest.fixture
def member(make_user):
    return make_user("member")


@pytest.fixture
def moderator(make_user):
    return make_user("moderator", User.Role.MODERATOR)


@pytest.fixture
def admin(make_user):
    return make_user("boss", User.Role.ADMIN)


def signup_form(**overrides):
    form = {
        "name": "Alice", "email": "alice@example.com", "password": PASSWORD,
        "password_again": PASSWORD, "accept_terms": "on",
    }
    return form | overrides


def token(outbox):
    """Return hexdigest of the change request from the last email."""
    return re.search(r"/c/(\w+)", outbox[-1][2]).group(1)


class TestLogin:
    def test_page(self, client):
        result = client.get("/login")

        assert result.status == 200
        assert 'name="password"' in result.text

    def test_page_for_logged_in_user_redirects(self, client, member):
        result = client.login(member).get("/login")

        assert result.status == 302

    def test_login(self, client, member):
        result = client.post("/login", form={
            "email": member.email, "password": PASSWORD,
            "redirect_url": "/en/general"})

        assert result.status == 302
        assert result.headers["Location"] == "/en/general"
        assert "SID=" in result.headers["Set-Cookie"]

    def test_login_removes_host_from_redirect(self, client, member):
        result = client.post("/login", form={
            "email": member.email, "password": PASSWORD,
            "redirect_url": "https://evil.example.com/path"})

        assert result.headers["Location"] == "/path"

    def test_wrong_password(self, client, member):
        result = client.post("/login", form={
            "email": member.email, "password": "wrong",
            "redirect_url": "/"})

        assert result.status == 200
        assert "Set-Cookie" not in result.headers

    def test_logout(self, client, member):
        result = client.login(member).get("/logout")

        assert result.status == 302
        assert result.headers["Location"] == "/"

    def test_logged_in_user_has_access(self, client, member):
        assert client.login(member).get("/user/profile").status == 200


class TestSignup:
    def test_page(self, client):
        assert client.get("/signup").status == 200

    def test_check_page(self, client):
        assert client.get("/signup-check").status == 200

    def test_signup_sends_confirmation(self, client, db, outbox):
        result = client.post("/signup", form=signup_form())

        assert result.status == 200
        user = User.find(db, "alice@example.com")
        assert user.state is User.State.REGISTERED
        assert outbox[-1][1] == "alice@example.com"

    def test_confirmation_activates_and_logs_in(self, client, db, outbox):
        client.post("/signup", form=signup_form())

        result = client.get(f"/c/{token(outbox)}")

        assert result.status == 302
        assert result.headers["Location"].startswith("/user/profile")
        assert "SID=" in result.headers["Set-Cookie"]
        user = User.find(db, "alice@example.com")
        assert user.state is User.State.ACTIVE

    def test_confirmation_is_one_time(self, client, outbox):
        client.post("/signup", form=signup_form())
        client.get(f"/c/{token(outbox)}")

        assert client.get(f"/c/{token(outbox)}").status == 410

    @pytest.mark.parametrize("overrides", [
        {"name": ""},
        {"email": ""},
        {"email": "not-an-email"},
        {"password": "short", "password_again": "short"},
        {"password_again": "Different1Passw0rd"},
        {"accept_terms": ""},
    ])
    def test_invalid_form(self, client, db, outbox, overrides):
        result = client.post("/signup", form=signup_form(**overrides))

        assert result.status == 200
        assert 'class="error"' in result.text
        assert not outbox
        assert User.count(db) == 1


class TestChangeRequest:
    def test_unknown(self, client):
        assert client.get("/c/" + "a" * 64).status == 404
        assert client.post("/c/" + "a" * 64).status == 404

    def test_expired(self, client, db, member):
        request = ChangeRequest.create(
            db, member.id, ChangeRequest.State.PASSWORD, {})
        db.execute("UPDATE change_request SET created = ?",
                   ((datetime.now(UTC) - timedelta(days=2))
                    .replace(tzinfo=None).isoformat(" "),))

        assert client.get(f"/c/{request.hexdigest}").status == 410
        assert client.post(f"/c/{request.hexdigest}").status == 410

    def test_other_states_are_bad_request(self, client, db, member):
        request = ChangeRequest.create(
            db, member.id, ChangeRequest.State.INFO_CHANGED, {})

        assert client.get(f"/c/{request.hexdigest}").status == 400
        assert client.post(f"/c/{request.hexdigest}").status == 400


class TestResetPassword:
    def test_form(self, client):
        assert client.get("/user/reset-password").status == 200

    def test_whole_process(self, client, db, member, outbox):
        result = client.post("/user/reset-password",
                             form={"email": member.email})
        assert result.status == 200
        assert outbox[-1][1] == member.email

        form = client.get(f"/c/{token(outbox)}")
        assert form.status == 200

        done = client.post(f"/c/{token(outbox)}", form={
            "password": NEW_PASSWORD, "password_again": NEW_PASSWORD})
        assert done.status == 302
        assert "SID=" in done.headers["Set-Cookie"]
        assert User.find(db, member.email, NEW_PASSWORD) is not None
        assert User.find(db, member.email, PASSWORD) is None

    @pytest.mark.parametrize("email", ["", "invalid", "nobody@example.com"])
    def test_invalid_email(self, client, outbox, email):
        result = client.post("/user/reset-password", form={"email": email})

        assert result.status == 200
        assert 'class="error"' in result.text
        assert not outbox

    @pytest.mark.parametrize("form", [
        {"password": "short", "password_again": "short"},
        {"password": NEW_PASSWORD, "password_again": "Different1Passw0rd"},
    ])
    def test_invalid_new_password(self, client, db, member, outbox, form):
        client.post("/user/reset-password", form={"email": member.email})

        result = client.post(f"/c/{token(outbox)}", form=form)

        assert result.status == 200
        assert 'class="error"' in result.text
        assert User.find(db, member.email, PASSWORD) is not None


class TestAccount:
    def test_pages_require_login(self, client):
        assert client.get("/user/profile").status == 401
        assert client.get("/user/account").status == 401
        assert client.post("/user/account", form={}).status == 401

    def test_pages(self, client, member):
        client.login(member)

        assert client.get("/user/profile").status == 200
        assert client.get("/user/account").status == 200

    def test_change_name_and_signature(self, client, db, member, outbox):
        result = client.login(member).post("/user/account", form={
            "name": "New Name", "email": member.email,
            "signature": "Cheers"})

        assert result.status == 302
        assert result.headers["Location"].endswith("#save-done")
        stored = User.get(db, member.id)
        assert (stored.name, stored.signature) == ("New Name", "Cheers")
        assert not outbox  # no credentials were changed

    def test_change_email_and_password_notifies(self, client, db, member,
                                                outbox):
        result = client.login(member).post("/user/account", form={
            "name": "member", "email": "new@example.com",
            "password": NEW_PASSWORD, "password_again": NEW_PASSWORD})

        assert result.status == 302
        assert User.find(db, "new@example.com", NEW_PASSWORD) is not None
        assert outbox[-1][1] == "new@example.com"

    @pytest.mark.parametrize("form", [
        {"name": "", "email": "member@example.com"},
        {"name": "member", "email": ""},
        {"name": "member", "email": "invalid"},
        {"name": "member", "email": "member@example.com",
         "password": "short", "password_again": "short"},
        {"name": "member", "email": "member@example.com",
         "password": NEW_PASSWORD},
    ])
    def test_invalid_form(self, client, db, member, outbox, form):
        result = client.login(member).post("/user/account", form=form)

        assert result.status == 200
        assert 'class="error"' in result.text
        assert not outbox
        assert User.get(db, member.id).name == "member"


class TestUsersAdministration:
    def test_list_requires_admin(self, client, moderator):
        assert client.get("/users").status == 401
        assert client.login(moderator).get("/users").status == 403

    def test_list(self, client, admin):
        result = client.login(admin).get("/users")

        assert result.status == 200
        assert "boss" in result.text

    def test_search(self, client, moderator, member):
        client.login(moderator)

        assert client.get("/users/search", query={"q": "memb"}).json() == {
            "users": [{"user_id": member.id, "name": "member"}]}
        assert client.get("/users/search").json() == {"users": []}

    def test_search_requires_moderator(self, client, member):
        assert client.login(member).get("/users/search").status == 403

    def test_public_profile(self, client, member):
        result = client.get(f"/users/{member.id}")

        assert result.status == 200
        assert "member" in result.text
        assert client.get("/users/9999").status == 404

    def test_ban_and_unban(self, client, db, moderator, member, outbox):
        client.login(moderator)

        assert client.post(f"/users/{member.id}/ban").status == 204
        assert User.get(db, member.id).state is User.State.BANNED
        assert "banned" in outbox[-1][0]

        assert client.delete(f"/users/{member.id}/ban").status == 204
        assert User.get(db, member.id).state is User.State.ACTIVE
        assert "enabled" in outbox[-1][0]

    def test_banned_user_cannot_use_session(self, client, moderator, member,
                                            outbox):
        client.login(moderator).post(f"/users/{member.id}/ban")

        assert client.login(member).get("/user/profile").status == 401

    def test_ban_errors(self, client, db, moderator, member):
        client.login(moderator)
        member.delete(db)

        assert client.post("/users/9999/ban").status == 404
        assert client.post(f"/users/{member.id}/ban").status == 410

    def test_unban_errors(self, client, moderator, member):
        client.login(moderator)

        assert client.delete("/users/9999/ban").status == 404
        # not banned user
        assert client.delete(f"/users/{member.id}/ban").status == 428

    def test_ban_requires_moderator(self, client, member, make_user):
        other = make_user("other")

        assert client.login(other).post(
            f"/users/{member.id}/ban").status == 403

    def test_update_role(self, client, db, admin, member):
        result = client.login(admin).request(
            "PUT", f"/users/{member.id}", data={"role": "moderator"})

        assert result.status == 204
        assert User.get(db, member.id).role is User.Role.MODERATOR

    def test_update_errors(self, client, db, admin, member):
        client.login(admin)

        assert client.request("PUT", f"/users/{member.id}",
                              data={"role": "king"}).status == 400
        assert client.request("PUT", "/users/9999",
                              data={"role": "admin"}).status == 404
        member.delete(db)
        assert client.request("PUT", f"/users/{member.id}",
                              data={"role": "admin"}).status == 410

    def test_update_requires_admin(self, client, moderator, member):
        result = client.login(moderator).request(
            "PUT", f"/users/{member.id}", data={"role": "admin"})

        assert result.status == 403

    def test_delete(self, client, db, admin, member, outbox):
        result = client.login(admin).delete(f"/users/{member.id}")

        assert result.status == 204
        assert User.get(db, member.id).state is User.State.DELETED
        assert "deleted" in outbox[-1][0]

    def test_delete_errors(self, client, db, admin, member):
        client.login(admin)

        assert client.delete("/users/9999").status == 404
        member.delete(db)
        assert client.delete(f"/users/{member.id}").status == 410
