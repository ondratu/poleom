"""Unit tests of render_response."""
from types import SimpleNamespace
from unittest.mock import patch

from poleom.lib import response
from poleom.lib.response import render_response


def test_render_response_uses_request_values():
    req = SimpleNamespace(user="me", lang="cs", db=None)
    with patch.object(response, "render_template") as render:
        render_response("t.html", req, languages={"en": 1}, other=1)

    render.assert_called_once_with(
        "t.html", me="me", lang="cs", languages={"en": 1}, other=1)


def test_render_response_prefers_section_lang():
    req = SimpleNamespace(user=None, lang="cs", db=None)
    section = SimpleNamespace(lang="en")
    with patch.object(response, "render_template") as render:
        render_response("t.html", req, section=section, languages={})

    assert render.call_args.kwargs["lang"] == "en"


def test_render_response_loads_languages():
    req = SimpleNamespace(user=None, lang="en", db="db")
    with patch.object(response, "render_template") as render, \
            patch.object(response.Language, "map",
                         return_value={"en": 1}) as language_map:
        render_response("t.html", req)

    language_map.assert_called_once_with("db")
    assert render.call_args.kwargs["languages"] == {"en": 1}
