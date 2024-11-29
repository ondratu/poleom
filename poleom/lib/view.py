"""Response generate module."""
import hashlib
import re
from datetime import datetime
from gettext import NullTranslations
from importlib.resources import files
from io import StringIO
from os.path import join

from dateutil.tz.tz import tzfile
from docutils.core import publish_parts
from docutils_tinyhtml import Writer
from jinja2 import Environment, FileSystemLoader
from jinja2_template_info import TemplateInfoExtension
from m2r2 import convert  # type: ignore[import]
from markupsafe import Markup

from .core import app

RE_MESSAGE = re.compile(r"[<>\w]+:(\d+): \((\w+)/(\d+)\) (.*)", re.U)
THOUSAND = 1000.0

TEMPL_PATH = (join(app.theme, "templates"),
              str(files("jinja2_template_info")),
              join(str(files("poleom")), "templates"))

environment = Environment(
    loader=FileSystemLoader(TEMPL_PATH),
    autoescape=True,
    extensions=["jinja2.ext.i18n", "jinja2.ext.do", "jinja2.ext.loopcontrols"])

# pylint: disable=no-member
environment.install_gettext_translations(  # type: ignore[attr-defined]
    NullTranslations())

writer = Writer()


def md2rst(src):
    """Convert MarkDown to RestructuredText."""
    return convert(src)


def parse_system_messages(out):
    """Parse error output from rst2html function."""
    if not isinstance(out, str):
        out = out.decode()
    retval = set()
    for line in out.split("\n"):
        match = RE_MESSAGE.search(line)
        if match:
            retval.add(match.groups())
    return tuple(retval)


def rst2html(src, system_messages=False):
    """Check RestructuredText source."""
    err_stream = StringIO()
    parts = publish_parts(source=src,
                          writer=writer,
                          writer_name="htm",
                          settings_overrides={
                              "warning_stream": err_stream,
                              "no_system_messages": not system_messages,
                              "initial_header_level": 3,
                              "halt_level": 100,
                          })
    body = parts["body"]
    if parts["title"]:
        body = "<h3>" + parts["title"] + "</h3>\n" + body
    if parts["html_footnotes"] or parts["html_citations"]:
        body += parts["html_line"] + \
            parts["html_footnotes"] + parts["html_citations"]
    err_stream.seek(0)
    return Markup(body), err_stream.read()


def jinja_rst2html(src):
    """Convert RestructuredText to HTML."""
    return rst2html(src)[0]


def sha256(txt: str):
    """Return sha256 hexdigest."""
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()


def local(value: datetime, time_zone: tzfile):
    """Transfer UTC datetime to local timezone."""
    return value.astimezone(time_zone)


def hbytes(val: float):
    """Return value with unit."""
    unit = ("B", "kB", "MB", "GB", "TB", "PB")
    u = 0
    while val > THOUSAND and u < len(unit):
        u += 1
        val = val / THOUSAND
    return f"{val:.1f}{unit[u]}"


environment.globals["title"] = app.title
environment.globals["theme"] = app.theme
environment.filters["md2rst"] = md2rst
environment.filters["rst2html"] = jinja_rst2html
environment.filters["sha256"] = sha256
environment.filters["local"] = local
environment.filters["hbytes"] = hbytes


def render_template(template: str, **kwargs):
    """Return generated ouptut fromjinja template."""
    if app.debug:
        env = environment.overlay()
        env.add_extension(TemplateInfoExtension)
        template_info = env.globals["template_info"]
        template_info.data = kwargs.copy()  # type: ignore[attr-defined]
        template_info.template = template  # type: ignore[attr-defined]
    else:
        env = environment

    env.globals["time_zone"] = app.TIME_ZONE  # TODO: user.time_zone or ...

    tmpl = env.get_template(template)
    return tmpl.render(kwargs)
