"""Application and configuration init."""
import logging
import re
from importlib.resources import files
from os.path import join

from dateutil.tz import gettz  # type: ignore[import-untyped]
from MySQLdb import connect  # type: ignore[import-untyped]
from MySQLdb.connections import Connection  # type: ignore[import-untyped]
from poorwsgi import Application, request

from .. import __name__ as appname
from .mysql import DB_CONV, Cursor
from .smtp import Smtp

HANDLER = logging.StreamHandler()
logging.root.addHandler(HANDLER)
logging.getLogger("poorwsgi").setLevel("WARNING")
logging.getLogger(appname).setLevel("WARNING")

LOG_FORMAT = ("%(asctime)s %(levelname)s: %(name)s: %(message)s "
              "{%(filename)s.%(funcName)s():%(lineno)d}")
HANDLER.setFormatter(logging.Formatter(LOG_FORMAT))


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
    TIME_ZONE = gettz("Europe/Prague")

    def __init__(self):
        super().__init__(appname)

        options = self.get_options()
        log_level = "WARNING"
        if options.get("debug", "False") == "True":
            self.debug = True
            log_level = "DEBUG"

        logging.root.setLevel(log_level)
        logging.getLogger(appname).setLevel(log_level)

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
    req.db = connect(conv=DB_CONV, cursorclass=Cursor, **app.db_conf)
