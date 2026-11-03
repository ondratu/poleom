"""Integrity tests of the Post model with SQLite database."""
from poleom.lib.pager import Pager
from poleom.lib.post import Post
from poleom.lib.section import Section
from poleom.lib.topic import Topic


def make_topic(db):
    section = Section.find(db, "en", "general")
    assert section is not None
    return Topic.create(db, section.id, "Topic")


def test_create_get_find(db, make_user):
    user = make_user()
    topic = make_topic(db)
    post = Post.create(db, topic.id, user.id, "Hello")

    assert post.id > 0
    for stored in (Post.get(db, post.id), Post.find(db, post.hexdigest)):
        assert stored is not None
        assert stored.body == "Hello"
        assert stored.parent is None
    assert Post.get(db, 9999) is None
    assert Post.find(db, "missing") is None


def test_reply_keeps_parent(db, make_user):
    user = make_user()
    topic = make_topic(db)
    post = Post.create(db, topic.id, user.id, "Hello")
    reply = Post.create(db, topic.id, user.id, "Answer", post.hexdigest)

    stored = Post.get(db, reply.id)
    assert stored is not None
    assert stored.parent == post.hexdigest


def test_update_sets_modified(db, make_user):
    user = make_user()
    topic = make_topic(db)
    post = Post.create(db, topic.id, user.id, "Hello")
    post.body = "Edited"
    post.update(db)

    stored = Post.get(db, post.id)
    assert stored is not None
    assert stored.body == "Edited"
    assert stored.modified is not None


def test_delete_and_count(db, make_user):
    user = make_user()
    topic = make_topic(db)
    post = Post.create(db, topic.id, user.id, "Hello")
    assert Post.count(db, topic.id) == 1

    Post.delete(db, post.id)
    assert Post.get(db, post.id) is None
    assert Post.count(db, topic.id) == 0


def test_list_sets_pager_total(db, make_user):
    user = make_user()
    topic = make_topic(db)
    for number in range(3):
        Post.create(db, topic.id, user.id, f"Post {number}")

    pager = Pager()
    posts = list(Post.list(db, pager, topic.id))

    assert [post.body for post in posts] == ["Post 0", "Post 1", "Post 2"]
    assert pager.total == 3
