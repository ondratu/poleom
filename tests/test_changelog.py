"""The ChangeLog must be kept in step with the version."""
from itertools import pairwise
from pathlib import Path

from poleom import __version__

CHANGELOG = Path(__file__).parent.parent / "ChangeLog.rst"


def headings():
    """Return versions of the release sections ("1.0.0 - date")."""
    lines = CHANGELOG.read_text(encoding="utf-8").splitlines()
    return [
        title.split(" - ")[0] for title, line in pairwise(lines)
        if title and line and set(line) == {"="} and len(line) == len(title)
    ][1:]  # the first one is the title of the file


def test_newest_release_is_on_top():
    expected = "Unreleased" if "dev" in __version__ else __version__
    assert headings()[0] == expected


def test_release_has_both_parts():
    text = CHANGELOG.read_text(encoding="utf-8")
    assert text.count("For users\n") == len(headings())
    assert text.count("For administrators\n") == len(headings())
