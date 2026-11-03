"""Tests for the poleom-passwd command."""
import re
import runpy
import sys
from hashlib import sha3_512

import bcrypt

from poleom.passwd_bcrypt import main, password_hash

PASSWORD = "Str0ngPassw0rd"


def test_hash_matches_application_format():
    hashed = password_hash(PASSWORD, 4)
    assert bcrypt.checkpw(
        sha3_512(PASSWORD.encode("utf-8")).digest(), hashed.encode("utf-8"))


def test_main_prints_sql(capsys):
    main([PASSWORD, "4"])
    out = capsys.readouterr().out
    assert re.search(r"UPDATE users SET password='\$2b\$04\$[^']+', "
                     r"email='your@login' WHERE email='root@localhost';",
                     out)
    assert "-- Password reset --" in out


def test_run_as_script(monkeypatch, capsys):
    # run_module warns when the module is imported already
    monkeypatch.delitem(sys.modules, "poleom.passwd_bcrypt")
    monkeypatch.setattr("sys.argv", ["poleom-passwd", PASSWORD, "4"])

    runpy.run_module("poleom.passwd_bcrypt", run_name="__main__")

    assert "UPDATE users SET password=" in capsys.readouterr().out
