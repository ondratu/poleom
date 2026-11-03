"""Data Source Name of the MySQL connection."""
import re

# Data Source Name regular expression for mysql connection
RE_DSN = re.compile(
    r"""\w+://            # driver
                          (?P<user>\w+)
                          (:(?P<password>\w+))?
                          (@(?P<host>[\w\.]+))?
                          (:(?P<port>[0-9]+))?
                          /(?P<db>\w+)
                          (::(?P<charset>\w+))?
                       """, re.X)


def parse_dsn(dsn: str) -> dict:
    """Return arguments of the MySQL connection from `app_db` value.

    >>> parse_dsn("mysql://user:pwd@db.local:3307/forum")["port"]
    3307
    """
    match = RE_DSN.match(dsn)
    if not match:
        msg = "Not valid data source name for MySQL in `app_db`!"
        raise ValueError(msg)
    conf = {
        "host": match.group("host") or "localhost",
        "port": int(match.group("port") or 3306),
        "database": match.group("db"),
        "charset": match.group("charset") or "utf8mb4",
        "user": match.group("user"),
    }
    password = match.group("password")
    if password:
        conf["password"] = password
    return conf
