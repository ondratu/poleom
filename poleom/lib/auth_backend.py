"""Authentication backends, see docs/auth-backends.rst."""
from dataclasses import dataclass


@dataclass
class Identity:
    """Who is the user of the request according to the auth backend."""

    subject: str  # stable id at the provider, never changes
    name: str
    email: str
    lang: str | None = None
    active: bool = True
