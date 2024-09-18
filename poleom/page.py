"""Core page output."""
from operator import itemgetter

from poorwsgi import redirect, state
from poorwsgi.response import JSONResponse, TextResponse

from .lib.auth import auth_user
from .lib.core import Request, app
from .lib.settings import Language
from .lib.view import md2rst, parse_system_messages, rst2html

TABLE_DOESNT_EXIST_ERR = 1146


@app.route("/")
def root(req: Request):
    """Root / page - redirect to lang list of sections."""
    language = app.default_lang
    languages = Language.map(req.db)

    if "Accept-Language" in req.headers:
        accept_language = sorted(req.accept_language, key=itemgetter(1),
                                 reverse=True)
        for lang, _ in accept_language:
            if lang in languages:
                language = lang
                break

    redirect(f"/{language}/")


@app.route("/<lang:lang>")
def lang_redirect(_, lang: str):
    """Redirect lang to right url"""
    redirect(f"/{lang}/")


@app.route("/terms")
def terms(req):
    """Redirect to terms url defined in settings."""
    lang = req.args.get("lang", app.default_lang)
    redirect(app.terms.get(lang, app.terms.get(app.default_lang)))


@app.route("/preview", method=state.METHOD_POST)
@auth_user()
def preview(req):
    """Check markdown and return preview."""
    source = req.form.getfirst("source", "").strip()
    if not source:
        return JSONResponse(errors=[], html="")

    html, errors = rst2html(md2rst(source))
    return JSONResponse(status_code=200 if not errors else 202,
                        html=html,
                        errors=parse_system_messages(errors))


@app.http_state(state.HTTP_CONFLICT)
def http_conflict(_):
    """Simple http conflict"""
    # TODO: better smarter error result
    return TextResponse("Entity exist yet", status_code=state.HTTP_CONFLICT)
