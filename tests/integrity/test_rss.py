"""Integrity tests for RSS feed rendering in poleom/lib/rss.py.

These tests exercise the real rendering pipeline (rss_response() and the
poleom/templates/rss/*.xml templates) with model instances built directly in
memory. They intentionally do not go through the route handlers in
section.py/topic.py, because those query the database with MySQL style
``%(name)s`` placeholders, which the sqlite `db` fixture used elsewhere in
this test suite cannot execute.
"""
# ruff: noqa: S318 -- parsing our own generated, trusted XML
from datetime import UTC, datetime
from time import time
from xml.dom.minidom import parseString

from poorwsgi.request import Request

from poleom.lib.post import Post
from poleom.lib.rss import CONTENT_TYPE, rss_response
from poleom.lib.section import Section
from poleom.lib.settings import Language
from poleom.lib.topic import Topic
from poleom.lib.user import User
from poleom.main import application as app


def make_req(path: str) -> Request:
    """Build a minimal poorwsgi Request usable by req.construct_url()."""
    env = {
        "REQUEST_STARTTIME": time(),
        "PATH_INFO": path,
        "wsgi.url_scheme": "http",
        "HTTP_HOST": "forum.example",
    }
    return Request(env, app)


class TestTopicRss:
    """RSS feed for a topic's posts (poleom/templates/rss/topic.xml)."""

    def test_render(self):
        """Feed must be well-formed XML with escaped post body."""
        section = Section(1, "General", "en", "Chat", path="general")
        topic = Topic(1, section.id, "Hello world", "hello-world")
        user = User(1, "Alice", "alice@example.com", None, User.State.ACTIVE)
        post = Post(1, topic.id, None, datetime(2026, 1, 1, tzinfo=UTC), None,
                    user.id, "abc123", "Body with <script>alert(1)</script>")
        post.user = user

        req = make_req("/en/general/hello-world/rss")
        response = rss_response(
            "rss/topic.xml", req,
            section=section, topic=topic, posts=[post],
            topic_url="http://forum.example/en/general/hello-world",
            lang="en")

        assert response.content_type == CONTENT_TYPE
        xml = response.data.decode("utf-8")

        dom = parseString(xml)  # raises ExpatError if not well-formed XML
        assert len(dom.getElementsByTagName("item")) == 1
        # post body must be HTML-escaped, so the script tag stays inert
        assert "<script>" not in xml
        assert "&lt;script&gt;" in xml
        assert "abc123" in xml


class TestSectionRss:
    """RSS feed for a section's topics (poleom/templates/rss/section.xml)."""

    def test_render(self):
        """Feed must be well-formed XML and list the topic as an item."""
        section = Section(1, "General", "en", "Chat", path="general")
        topic = Topic(1, section.id, "Hello world", "hello-world")
        topic.count = 3
        topic.last = datetime(2026, 1, 1, tzinfo=UTC)
        topic.user_name = "Alice"

        req = make_req("/en/general/rss")
        response = rss_response(
            "rss/section.xml", req,
            section=section, topics=[topic],
            section_url="http://forum.example/en/general", lang="en")

        xml = response.data.decode("utf-8")
        dom = parseString(xml)
        assert len(dom.getElementsByTagName("item")) == 1
        assert "Hello world" in xml
        assert "Alice" in xml


class TestLangRss:
    """RSS feed for a language (poleom/templates/rss/lang.xml)."""

    def test_render(self):
        """Feed must be well-formed XML and list section+topic as an item."""
        section = Section(1, "General", "en", "Chat", path="general")
        topic = Topic(1, section.id, "Hello world", "hello-world")
        topic.count = 1
        topic.last = datetime(2026, 1, 1, tzinfo=UTC)
        topic.user_name = "Alice"

        req = make_req("/en/rss")
        response = rss_response(
            "rss/lang.xml", req,
            items=[(section, topic)], lang="en",
            languages={"en": Language("en", "en_US", "English", True)},
            lang_url="http://forum.example/en")

        xml = response.data.decode("utf-8")
        dom = parseString(xml)
        assert len(dom.getElementsByTagName("item")) == 1
        assert "General" in xml
        assert "Hello world" in xml
