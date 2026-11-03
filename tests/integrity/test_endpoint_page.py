"""Integrity tests of the endpoints in page.py."""
from poleom import page


def test_root_redirects_to_default_language(client):
    result = client.get("/")

    assert result.status == 302
    assert result.headers["Location"].endswith("/en/")


def test_root_uses_accept_language(client):
    result = client.get("/", headers={"Accept-Language": "cs,en;q=0.5"})

    assert result.headers["Location"].endswith("/cs/")


def test_root_ignores_unknown_accept_language(client):
    result = client.get("/", headers={"Accept-Language": "pl"})

    assert result.headers["Location"].endswith("/en/")


def test_language_redirect(client):
    result = client.get("/cs")

    assert result.status == 302
    assert result.headers["Location"].endswith("/cs/")


def test_terms_redirect(client):
    result = client.get("/terms", query={"lang": "cs"})

    assert result.status == 302
    assert result.headers["Location"] == "/not-found?lang=cs"


def test_terms_unknown_language_falls_back(client):
    result = client.get("/terms", query={"lang": "pl"})

    assert result.headers["Location"] == "/not-found?lang=en"


def test_conflict_page():
    response = page.http_conflict(None)

    assert response.status_code == 409
    assert b"Entity exist yet" in response.data


def test_preview_requires_login(client):
    assert client.post("/preview", form={"source": "x"}).status == 401


def test_preview_empty_source(client, make_user):
    result = client.login(make_user()).post("/preview", form={"source": " "})

    assert result.status == 200
    assert result.json() == {"errors": [], "html": ""}


def test_preview_renders_markdown(client, make_user):
    result = client.login(make_user()).post(
        "/preview", form={"source": "Hello *world*"})

    assert result.status == 200
    assert "<em>world</em>" in result.json()["html"]


def test_preview_does_not_pass_html(client, make_user):
    result = client.login(make_user()).post(
        "/preview", form={"source": "<script>alert(1)</script>"})

    assert "<script>" not in result.json()["html"]
