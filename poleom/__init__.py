"""Poleom"""

from .lib.core import app as application

__import__("main", globals=globals(), level=1)
__import__("sections", globals=globals(), level=1)
__import__("topics", globals=globals(), level=1)
__import__("posts", globals=globals(), level=1)

__all__ = ["application"]
