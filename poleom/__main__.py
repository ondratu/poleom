"""WSGI server"""
from gevent.pywsgi import WSGIServer  # type: ignore[import]

from .lib.core import app

app.debug = True

if __name__ == "__main__":
    print("Serving on 8000...")  # noqa: T201
    WSGIServer(("127.0.0.1", 8000), app).serve_forever()
