"""Integrity tests of the languages."""
from poleom.lib.settings import Language


def test_languages_map(db):
    languages = Language.map(db)

    assert list(languages) == ["cs", "en"]
    assert languages["en"].language == "English"


def test_languages_map_only_active(db):
    db.execute("UPDATE languages SET active = 0 WHERE lang = 'cs'")

    assert list(Language.map(db, only_active=True)) == ["en"]
