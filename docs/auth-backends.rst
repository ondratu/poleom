=====================
Authentication plugin
=====================

By default Poleom keeps its own accounts and passwords. An *authentication
backend* is a small plugin which lets an external service (a single sign-on
server, Google, ...) log the users in instead. Only one backend is active.

How it works
============

The backend does not know the forum database. It only answers the question
"who is the user of this request?" with an ``Identity``. The core then finds
or creates the local row in ``users`` (the posts, sections and other tables
point to it), so everything else in the forum works the same as before.

.. code-block:: text

    request -> backend.identity(req) -> Identity -> users row -> req.user

* The local row is found by ``users.auth_sub`` (the ``Identity.subject``). It
  is created at the first login with the state ``ACTIVE`` and the role
  ``MEMBER``.
* The name, the e-mail and the language are copied from the ``Identity`` to
  the local row on every login, the external service is the master of them.
* The **role and the ban stay local**. An inactive ``Identity`` (the user is
  deactivated in the external service) is not logged in.
* A user without a password (``users.password`` is ``NULL``) can not use
  the local login.

The default ``LocalAuthBackend`` is the original behaviour: the session
cookie of the forum and the login by the e-mail and the password.

Interface
=========

The module ``poleom/lib/auth_backend.py`` defines:

.. code-block:: python

    @dataclass
    class Identity:
        subject: str            # stable id at the provider, never changes
        name: str
        email: str
        lang: str | None = None
        active: bool = True

    class AuthBackend:
        allows_local_login = False   # True only for LocalAuthBackend

        def init_app(self, app) -> None:
            """Called once at the start, register own routes here."""

        def identity(self, req) -> Identity | None:
            """Return the identity of the request or None."""

        def login_url(self, req, next_url: str) -> str:
            """Where to send the user to log in, then back to next_url."""

        def signup_url(self, req, next_url: str) -> str | None:
            """Where to register, None hides the link."""

        def profile_url(self, req) -> str | None:
            """Where the user changes the password, None hides the link."""

        def logout(self, req) -> Response:
            """Destroy the session and return the response (a redirect)."""

``identity()``, ``login_url()`` and ``logout()`` are abstract, the others
have defaults (``init_app`` does nothing, ``signup_url`` and ``profile_url``
return ``None``). The backend which keeps the users itself (only
``LocalAuthBackend``) overrides ``load_user(req)``, which returns the local
``User`` and by default maps the ``Identity`` as described above.

``identity()`` is called on every request which needs the user, so it has to
be fast. Reading a cookie is fine; a call of a remote service should be cached
by the backend (for example for a few minutes). It must never raise, a failure
means ``None``.

``next_url`` is a path on the forum (``/topic/42``). The backend makes the
absolute address from it, when the provider needs one.

Writing a backend
=================

A backend is a class in any importable module, with no arguments in the
constructor. It reads its own configuration from the ``app_*`` variables
(``app.get_options()``), so the options of the plugins do not mix with the
forum ones. A minimal backend with a cookie of an external single sign-on:

.. code-block:: python

    from poleom.lib.auth_backend import AuthBackend, Identity


    class SsoBackend(AuthBackend):
        def init_app(self, app):
            self.sso = app.get_options()["sso_url"]

        def identity(self, req):
            user = decode_cookie(req.cookies)     # your code
            if not user:
                return None
            return Identity(str(user["id"]), user["name"], user["email"])

        def login_url(self, req, next_url):
            back = req.construct_url(next_url)
            return f"{self.sso}/login?redirect_uri={back}"

        def signup_url(self, req, next_url):
            return f"{self.sso}/signup"

        def profile_url(self, req):
            return f"{self.sso}/me"

        def logout(self, req):
            return RedirectResponse("/")           # and destroy the cookie

A backend which needs a callback (OAuth) registers it in ``init_app`` with
``app.route``; the callback stores the session and redirects back.

Configuration
=============

``app_auth_backend``
    ``module:Class``, for example ``mypackage.sso:SsoBackend``. When it is not
    set, ``LocalAuthBackend`` is used. A value which can not be imported
    stops the application at the start with an error which names it.

Turning a plugin on:

* the local login, signup, logout and the reset of the password are turned
  off, the routes redirect to the backend. The account form hides the
  password and the e-mail, they are changed in the external service,
* the existing local users are connected to the provider by filling
  ``users.auth_sub``. The backend documents what to put there.

Database
========

The schema has ``users.auth_sub VARCHAR(255) NULL UNIQUE`` and
``users.password`` may be ``NULL``. There is no migration tool, the upgrade
of an existing database is the SQL in the ``ChangeLog.rst``.

Tests
=====

Test a backend without the network.
``tests/integrity/test_endpoint_external_auth.py`` shows a fake backend;
the ``client`` fixture runs the whole application with it.
