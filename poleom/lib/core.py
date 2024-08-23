"""Application and configuration init."""
import re
from importlib.resources import files
from os.path import join

from MySQLdb import connect  # type: ignore[import-untyped]
from MySQLdb.connections import Connection  # type: ignore[import-untyped]
from poorwsgi import Application, request

from .smtp import Smtp


class Request(request.Request):
    """Own Request for typechecking."""
    __db: Connection

    @property
    def db(self):
        """MySQL Connection per request."""
        return self.__db

    @db.setter
    def db(self, value):
        self.__db = value


class App(Application):
    """Own Application class"""

    def __init__(self):
        super().__init__("Poleom")

        options = self.get_options()
        if options.get("debug", "False") == "True":
            self.debug = True

        self.title = options.get("title", "Poleom")

        # Data Source Name regular expression for mysql connection
        re_dsn = re.compile(
            r"""\w+://            # driver
                                  (?P<user>\w+)
                                  (:(?P<password>\w+))?
                                  (@(?P<host>[\w\.]+))?
                                  (:(?P<port>[0-9]+))?
                                  /(?P<db>\w+)
                                  (::(?P<charset>\w+))?
                               """, re.X)

        match = re_dsn.match(options.get("db"))
        self.db_conf = {
            "host": match.group("host") or "localhost",
            "port": int(match.group("port") or 3306),
            "database": match.group("db"),
            "charset": match.group("charset") or "utf8",
            "user": match.group("user"),
        }
        password = match.group("password")
        if password:
            self.db_conf["password"] = password

        self.secret_key = options.get("secret_key")
        if not self.secret_key:
            error = "Not secret_key set!"
            raise RuntimeWarning(error)

        self.smtp = Smtp(options.get("smtp", ""))
        self.smtp.timeout = 10

        self.change_request_ttl = int(
            options.get("change_request_ttl", "86400"))


app = App()
app.document_root = join(str(files("poleom")), "assets")


@app.before_response()
def db_connect(req: Request):
    """Create DB connection."""
    req.db = connect(**app.db_conf)
