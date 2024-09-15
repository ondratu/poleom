"""Poleom"""

from .lib.core import app as application

__import__("attachment", globals=globals(), level=1)
__import__("section", globals=globals(), level=1)
__import__("topic", globals=globals(), level=1)
__import__("page", globals=globals(), level=1)
__import__("post", globals=globals(), level=1)
__import__("user", globals=globals(), level=1)

__all__ = ["application"]
