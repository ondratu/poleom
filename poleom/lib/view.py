"""Response generate module."""
from gettext import NullTranslations
from importlib.resources import files
from os.path import join

from jinja2 import Environment, FileSystemLoader
from jinja2_template_info import TemplateInfoExtension

from .core import app

TEMPL_PATH = (str(files("jinja2_template_info")),
              join(str(files("poleom")), "templates"))

environment = Environment(
    loader=FileSystemLoader(TEMPL_PATH),
    autoescape=True,
    extensions=["jinja2.ext.i18n", "jinja2.ext.do", "jinja2.ext.loopcontrols"])

environment.install_gettext_translations(  # pylint: disable=no-member
        NullTranslations())


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
