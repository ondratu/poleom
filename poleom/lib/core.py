"""Application and configuration init."""
import logging
import re
from importlib.resources import files
from os import W_OK, access, path

from dateutil.tz import gettz  # type: ignore[import-untyped]
from MySQLdb import connect
from MySQLdb.connections import Connection
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
    __lang: str

    @property
    def db(self):
        """MySQL Connection per request."""
        return self.__db

    @db.setter
    def db(self, value):
        self.__db = value

    @property
    def lang(self):
        """Selected language"""
        return self.__lang

    @lang.setter
    def lang(self, value: str):
        self.__lang = value


class App(Application):
    """Own Application class"""
    # pylint: disable=too-many-instance-attributes
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

        self.theme = path.abspath(options.get("theme", "./poleom"))
        self.title = options.get("title", "Poleom")
        self.default_lang = options.get("default_lang", "en")
        self.terms = {}  # TODO move to DB settings
        self.terms["en"] = options.get("terms_en", "/not-found?lang=en")
        self.terms["cs"] = options.get("terms_cs", "/not-found?lang=cs")

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

        match = re_dsn.match(options.get("db", ""))
        if not match:
            msg = "Not valid data source name for MySQL in `app_db`!"
            raise ValueError(msg)
        self.db_conf = {
            "host": match.group("host") or "localhost",
            "port": int(match.group("port") or 3306),
            "database": match.group("db"),
            "charset": match.group("charset") or "utf8mb4",
            "user": match.group("user"),
        }
        password = match.group("password")
        if password:
            self.db_conf["password"] = password

        self.secret_key = options.get("secret_key")
        if not self.secret_key:
            error = "Not secret_key set!"
            raise ValueError(error)

        self.smtp = Smtp(options.get("smtp", ""))
        self.smtp.timeout = 10

        self.change_request_ttl = int(
            options.get("change_request_ttl", "86400"))

        self.attachments = options.get("attachments", "./attachments")
        if not path.isdir(self.attachments):
            msg = f"Attachments `{self.attachments}` is not directory."
            raise ValueError(msg)
        if not access(self.attachments, W_OK):
            msg = f"Attachments `{self.attachments}` is not writable."
            raise ValueError(msg)


app = App()
app.set_filter("lang", r"[a-z]{2,3}", str)
app.document_root = path.join(str(files("poleom")), "assets")


@app.before_response()
def db_connect(req: Request):
    """Create DB connection."""
    req.db = connect(conv=DB_CONV, cursorclass=Cursor, **app.db_conf)
    req.lang = app.default_lang
