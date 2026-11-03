"""Unit tests of the installation wizard class."""
from unittest.mock import MagicMock, patch

from poleom.lib import wizard
from poleom.lib.wizard import Wizard


def test_db_install_runs_init_sql(tmp_path):
    (tmp_path / "init.sql").write_text("CREATE TABLE x (y INT);")
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value

    with patch.object(Wizard, "SQL_PATH", str(tmp_path)):
        Wizard().db_install(conn)

    cursor.execute.assert_called_once_with("CREATE TABLE x (y INT);")


def test_insert_admin():
    with patch.object(wizard.User, "create") as create:
        Wizard().insert_admin("conn", "Admin", "a@example.com", "secret")

    create.assert_called_once_with("conn", "Admin", "a@example.com", "secret")
