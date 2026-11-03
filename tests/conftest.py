"""Configuration of the application for tests.

The application reads its configuration from the environment when it is
imported, so it has to be set before the first test module is collected.
Values already set (for example from ``.env``) are kept.
"""
import atexit
import os
import shutil
import tempfile

ATTACHMENTS = tempfile.mkdtemp(prefix="poleom-attachments-")
atexit.register(shutil.rmtree, ATTACHMENTS, ignore_errors=True)

os.environ.setdefault("app_db", "mysql://user:password@localhost/poleom")
os.environ.setdefault("app_secret_key", "test")
os.environ.setdefault("app_smtp", "smtp://localhost/root@localhost")
os.environ.setdefault("app_attachments", ATTACHMENTS)
