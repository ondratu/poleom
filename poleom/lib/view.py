"""Response generate module."""
import re
from gettext import NullTranslations
from importlib.resources import files
from io import StringIO
from os.path import join

# docutils_tinyhtml
from docutils.core import publish_parts  # type: ignore[import]
from docutils_tinyhtml import Writer
from jinja2 import Environment, FileSystemLoader
from jinja2_template_info import TemplateInfoExtension
from m2r2 import convert  # type: ignore[import]
from markupsafe import Markup

from .core import app

RE_MESSAGE = re.compile(r"[<>\w]+:(\d+): \((\w+)/(\d+)\) (.*)", re.U)

TEMPL_PATH = (str(files("jinja2_template_info")),
              join(str(files("poleom")), "templates"))

environment = Environment(
    loader=FileSystemLoader(TEMPL_PATH),
    autoescape=True,
    extensions=["jinja2.ext.i18n", "jinja2.ext.do", "jinja2.ext.loopcontrols"])

environment.install_gettext_translations(  # pylint: disable=no-member
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


def rst2html(src):
    """Check RestructuredText source."""
    err_stream = StringIO()
    parts = publish_parts(source=src,
                          writer=writer,
                          writer_name="htm",
                          settings_overrides={
                              "warning_stream": err_stream,
                              "no_system_messages": True,
                              "initial_header_level": 3,
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


environment.globals["title"] = app.title
environment.filters["md2rst"] = md2rst
environment.filters["rst2html"] = jinja_rst2html


def generate_page(template, **kwargs):
    """Return generated ouptut fromjinja template."""
    if app.debug:
        env = environment.overlay()
        env.add_extension(TemplateInfoExtension)
        env.globals["template_info"].data = kwargs.copy()
        env.globals["template_info"].template = template
    else:
        env = environment

    tmpl = env.get_template(template)
    return tmpl.render(kwargs)
