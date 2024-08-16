"""Poleom Errors and Exceptions."""
from enum import Enum

MYSQL_DUPLICITY = 1062


class FormError(Enum):
    """Form errors."""
    MISSING = "missing"
    MISMATCH = "mismatch"
    SHORT = "short"
    FORMAT = "format"
    INVALID = "invalid"
    DUPLICITY = "duplicity"


class DuplicityError(RuntimeError):
    """Ruplicity Record Error"""
