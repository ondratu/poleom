"""Integrity tests for root functionality in page.py."""

from time import time
from unittest.mock import patch

import pytest
from poorwsgi import state
from poorwsgi.request import Request
from poorwsgi.response import HTTPException

from poleom import page
from poleom.lib.sqlite import DictCursor
from poleom.main import application as app


@patch("poleom.lib.settings.DictCursor", DictCursor)
class TestPage:
    """Tests for handlers in page.py."""

    def test_root(self, db):
        env = {"REQUEST_STARTTIME": time(), "PATH_INFO": "/"}

        req = Request(env, app)
        req.db = db
        with pytest.raises(HTTPException) as err:
            page.root(req)
        assert err.value.status_code == state.HTTP_MOVED_TEMPORARILY
        assert err.value.response.headers["Location"] == "/en/"

    def test_lang_redirect(self):
        env = {"REQUEST_STARTTIME": time(), "PATH_INFO": "/"}
        req = Request(env, app)
        with pytest.raises(HTTPException) as err:
            page.lang_redirect(req, "pl")
        assert err.value.response.headers["Location"] == "/pl/"
