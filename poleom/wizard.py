"""Wizard setup endpoins."""

from .lib.core import app
from .lib.view import generate_page


@app.route("/wizard")
def wizard(_):
    """Wizard setup page."""
    return generate_page("wizard.html")
