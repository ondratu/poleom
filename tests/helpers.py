"""Shared WSGI test utilities (not pytest fixtures)."""
import json
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from time import time
from urllib.parse import urlencode

from poleom.lib.auth import create_login_cookie
from poleom.lib.mysql import as_utc
from poleom.lib.section import Section
from poleom.lib.sqlite import DictCursor
from poleom.lib.topic import Topic


@dataclass
class Result:
    """Result of the WSGI call."""
    status: int
    headers: dict[str, str]
    body: bytes

    @property
    def text(self) -> str:
        """Body as text."""
        return self.body.decode("utf-8")

    def json(self):
        """Body parsed as JSON."""
        return json.loads(self.body)


def login_cookie(user) -> str:
    """Return ``Cookie`` header value of the logged in user."""
    session = create_login_cookie(user.id)
    session.write()
    return session.cookie.output(header="").strip()


BOUNDARY = "----poleomtestboundary"


def multipart(form: dict, files: list) -> bytes:
    """Return body of the multipart form, with the `attachments` field."""
    lines: list[bytes] = []
    for name, value in form.items():
        lines += [f"--{BOUNDARY}".encode(),
                  f'Content-Disposition: form-data; name="{name}"'.encode(),
                  b"", str(value).encode()]
    for filename, content, mime_type in files or [("", b"", "text/plain")]:
        lines += [f"--{BOUNDARY}".encode(),
                  ('Content-Disposition: form-data; name="attachments"; '
                   f'filename="{filename}"').encode(),
                  f"Content-Type: {mime_type}".encode(), b"", content]
    lines += [f"--{BOUNDARY}--".encode(), b""]
    return b"\r\n".join(lines)


class Client:
    """Call the WSGI application with a minimal environ."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app
        self.cookie = ""

    def login(self, user):
        """All next requests are made by the user."""
        self.cookie = login_cookie(user)
        return self

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def request(self, method, path, query=None, form=None, data=None,
                headers=None, files=None):
        """Make the request and return the `Result`.

        ``files`` is a list of ``(filename, content, mime_type)``, which makes
        the form multipart. An empty list is the browser's empty file field.
        """
        body = b""
        content_type = "application/x-www-form-urlencoded"
        if files is not None:
            content_type = f"multipart/form-data; boundary={BOUNDARY}"
            body = multipart(form or {}, files)
        elif form is not None:
            body = urlencode(form, doseq=True).encode()
        elif data is not None:
            body = json.dumps(data).encode()
            content_type = "application/json"
        env = {
            "PATH_INFO": path,
            "QUERY_STRING": urlencode(query or {}),
            "REQUEST_METHOD": method,
            "SERVER_NAME": "forum.example.com",
            "SERVER_PORT": "80",
            "HTTP_HOST": "forum.example.com",
            "wsgi.url_scheme": "http",
            "wsgi.input": BytesIO(body),
            "wsgi.errors": BytesIO(),
            "REQUEST_STARTTIME": time(),
        }
        if body:
            env["CONTENT_TYPE"] = content_type
            env["CONTENT_LENGTH"] = str(len(body))
        if self.cookie:
            env["HTTP_COOKIE"] = self.cookie
        for name, value in (headers or {}).items():
            env["HTTP_" + name.upper().replace("-", "_")] = value

        captured = {}

        def start_response(status, response_headers, _exc_info=None):
            captured["status"] = int(status.split()[0])
            captured["headers"] = dict(response_headers)

        chunks = b"".join(self.wsgi_app(env, start_response))
        return Result(captured["status"], captured["headers"], chunks)

    def get(self, path, **kwargs):
        """GET request."""
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        """POST request."""
        return self.request("POST", path, **kwargs)

    def patch(self, path, **kwargs):
        """PATCH request."""
        return self.request("PATCH", path, **kwargs)

    def delete(self, path, **kwargs):
        """DELETE request."""
        return self.request("DELETE", path, **kwargs)


def sqlite_section_list(conn, lang, user_id=0):
    """Replacement of `Section.list`, SQLite cannot run the MySQL query.

    ``user_id`` None is the administrator who sees all sections.
    """
    access = ("S.private = 0 OR S.section_id IN ("
              "SELECT section_id FROM sections_users "
              "WHERE user_id = %(user_id)s)")
    if user_id is None:
        access = "1 = 1"
    with conn.cursor(DictCursor) as cur:
        cur.execute(f"""
            SELECT S.*, (SELECT COUNT(*) FROM topics AS T
                         WHERE T.section_id = S.section_id) AS count
            FROM sections AS S
            WHERE S.lang = %(lang)s AND ({access})
            ORDER BY weight
            """, {"lang": lang, "user_id": user_id})
        for row in cur:
            section = Section.from_row(row)
            section.count = row["count"]
            yield section


def sqlite_topic_list(conn, pager, section_id):
    """Replacement of `Topic.list`, SQLite cannot run the MySQL query."""
    with conn.cursor(DictCursor) as cur:
        cur.execute("""
            SELECT T.*, COUNT(P.post_id) AS count, MAX(P.created) AS last,
                   MAX(U.name) AS user_name
            FROM topics AS T
                LEFT JOIN posts AS P ON (P.topic_id = T.topic_id)
                LEFT JOIN users AS U ON (U.user_id = P.user_id)
            WHERE T.section_id = %(section_id)s
            GROUP BY T.topic_id
            ORDER BY last DESC
            LIMIT %(OFFSET)s, %(LIMIT)s
            """, dict(pager.sql_dict(), section_id=section_id))
        topics = []
        for row in cur:
            topic = Topic.from_row(row)
            topic.count = row["count"]
            topic.last = as_utc(datetime.fromisoformat(row["last"])
                                if row["last"] else None)
            topic.user_name = row["user_name"]
            topics.append(topic)
        cur.execute(
            "SELECT COUNT(*) AS count FROM topics WHERE section_id = %(id)s",
            {"id": section_id})
        pager.total = cur.fetchone()["count"]
    yield from topics
