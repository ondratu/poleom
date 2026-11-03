"""Tests for the reStructuredText rendering of user input."""
from poleom.lib.view import md2rst, rst2html


def test_paragraph():
    body, _ = rst2html("Hello *world*")
    assert "<em>world</em>" in body


def test_raw_html_is_disabled():
    body, _ = rst2html(".. raw:: html\n\n   <script>alert(1)</script>\n")
    assert "<script>" not in body


def test_file_include_is_disabled(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET")
    body, _ = rst2html(f".. include:: {secret}\n")
    assert "TOP-SECRET" not in body


def test_markdown_html_is_inert():
    """Posts are Markdown, which converts inline HTML to the raw role."""
    body, _ = rst2html(md2rst("Hi <script>alert(1)</script>"))
    assert "<script>" not in body
