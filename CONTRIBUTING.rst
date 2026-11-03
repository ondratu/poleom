============
Contributing
============

Development environment
=======================

You need Python 3.11+, `uv <https://docs.astral.sh/uv/>`_, ``git`` and
Docker (or Podman) for the development database.

.. code-block:: sh

    python -m venv .venv
    source .venv/bin/activate
    make install        # package in editable mode and all dev tools
    pre-commit install  # run the checks before every commit

``make help`` lists all targets:

* ``make test`` - run tests with coverage report
* ``make lint`` - run ruff and pylint
* ``make typecheck`` - run mypy
* ``make check`` - run all pre-commit hooks on all files, like CI does
* ``make wheel`` - build and check the wheel
* ``make dev`` - run the uWSGI development server
* ``make clean`` - remove caches, coverage data and built packages

Development server
------------------

Start a throw-away MariaDB container (``docker-mysql.sh``) and create
the schema:

.. code-block:: sh

    ./docker-mysql.sh
    mysql -u root -proot -h 127.0.0.1 --skip-ssl -e "CREATE DATABASE poleom"
    mysql -u root -proot -h 127.0.0.1 --skip-ssl poleom < poleom/mysql/init.sql
    mkdir -p attachments

Run the uWSGI development server:

.. code-block:: sh

    make dev

It uses ``example/etc/uwsgi.ini`` with debug mode and autoreload on, and
the database from ``docker-mysql.sh``. To change the settings (``app_smtp``
for example), copy the file and run ``uwsgi --ini`` with your copy.

Or run the simple gevent server, with the ``app_*`` variables exported in
the environment (see `README.rst`_ for the list):

.. code-block:: sh

    python -m poleom

The forum is then available at http://localhost:8000/. To log in as
the default administrator ``root@localhost``, set its password with
``poleomctl user:set-password``, see "First administrator" in `README.rst`_.

Code changes
============

* Follow the existing code style and the Zen of Python.
* Follow PEP 8 and PEP 257, comments should say *why*, not the obvious.
* Use type annotations.
* The line length is 79 characters (``.editorconfig``, ruff).
* Code, comments and commit messages are in English.
* Suppressing a linter warning (``noqa``, ``type: ignore``,
  ``pylint: disable``) needs a reason. Think before silencing it, the
  warning is often legitimate.
* Think twice before adding a dependency. Look for the functionality in
  the already used libraries first.
* Do not make the code worse than you found it.

The checks are strict, CI runs them on every push and pull request and
a change which does not pass them is not merged. ``make check`` runs all
of them: whitespace and file checks, ``editorconfig-checker``, ``yamllint``,
``codespell``, ``ruff``, ``flake8``, ``rst-linter``, ``pylint`` and ``mypy``.
The unfinished ``poleom/wizard.py`` is excluded from ``pylint``, ``mypy`` and
the tests until it is done.

Database schema
---------------

A change of the schema updates both ``poleom/mysql/init.sql`` and
``poleom/sqlite/init.sql`` (the latter is used by the tests) and describes
how to upgrade an existing database. There is no migration tool, a migration
is a plain SQL file, run by ``poleomctl db:upgrade`` (``poleom/ctl.py``):

* ``poleom/mysql/migrations/<version>.sql`` - the SQL which upgrades a database
  of the previous release to this ``<version>`` (the one in ``Unreleased`` of
  the `ChangeLog.rst`_, for example ``0.2.0.sql``). Start the file with a
  comment of what it does. When the version already has a file, add the new
  statements to it, so one version is one file,
* a statement ends with ``;`` at the end of a line (a ``-- comment`` after
  it is allowed) and the file has no ``;`` inside strings, the command splits
  the file by that. Comments start with ``--``. MySQL commits DDL at once, so
  a failed migration leaves the database changed partly and the administrator
  restores the backup; keep a file small and its statements few,
* the database stores the version of its schema in the table ``meta``
  (``schema_version``). The command runs the files newer than that, in the
  order of versions, each once, and writes the version after each file. So
  a migration never edits an older file and does not depend on data created
  by a later one,
* a new schema version also changes the version inserted at the end of
  the ``meta`` table definition in both ``init.sql`` files, to the version
  of the newest migration. A test checks it. A release without a change of
  the schema has no migration and no new version,
* the `ChangeLog.rst`_ item for administrators names the file instead of
  repeating the SQL,
* test the file against a real MySQL (``docker-mysql.sh``): load ``init.sql``
  of the previous release, run ``poleomctl db:upgrade`` and compare the
  schema with the new ``init.sql``.

New commands of ``poleomctl`` are functions ``cmd_<group>_<name>`` registered
in ``parser()``. They print through ``out`` and return the exit code, so the
tests call ``main()`` without a terminal.

Authentication plugins
----------------------

A new authentication backend (SSO, Google, ...) is a class derived from
``AuthBackend`` in ``poleom/lib/auth_backend.py``. The interface, the mapping
of the user and an example are in `docs/auth-backends.rst`_; read it first.
Test it as ``tests/integrity/test_endpoint_external_auth.py`` does, without
the network, and document the options of the plugin (``app_*``) in
`README.rst`_.

Configuration and documentation
-------------------------------

A new or changed ``app_*`` option, installation step or command updates
`README.rst`_ in the same commit. The documentation is written in
reStructuredText and checked by the ``rst-linter`` pre-commit hook.

Tests
=====

.. code-block:: sh

    make test                                          # all tests
    .venv/bin/python -m pytest tests/integrity/test_login.py   # one file

Pytest is configured in ``pyproject.toml``. Every run prints the coverage
report (percentages only) and writes ``coverage.xml``; doctests of
the modules are run as well.

Test strategy
-------------

The tests are a pyramid, the same as in the other projects:

* simple functions are covered by doctests in the module,
* ``tests/unit/`` - unit tests of the code without the database or the
  network: models (``from_row``, ``to_dict``, roles), the pager, the SMTP
  data source name, the HTTP cache helpers, the converters. They are the
  most numerous. One file tests one module of ``poleom/lib``,
* ``tests/integrity/`` - tests of the models with the in-memory SQLite
  database (see below) and ``test_endpoint_*.py`` - tests of the endpoints:
  the ``client`` fixture (``tests/helpers.py``) makes a whole WSGI request,
  the routing, the authorization, the models and the templates are real, only
  the database is SQLite and the emails are collected by the ``outbox``
  fixture. A logged in user is made by ``client.login(user)``,
* every endpoint should have an integrity test.

Rules for tests:

* every new feature and every bug fix comes with a test, in the same pull
  request. A bug is fixed by a test which fails without the fix,
* the coverage is measured with branches. The total coverage and the coverage
  of **every file** must be at least **95 %**, the ideal is 100 %. The total
  is checked by ``fail_under`` in ``[tool.coverage.report]`` of
  ``pyproject.toml``, the files by ``tools/check-coverage.py``, which
  ``make test`` and CI run after ``pytest``. Do not lower the limits, add
  tests,
* unfinished code and code which the tests cannot import is omitted in
  ``[tool.coverage.run]``, never leave such a file in the measured code just
  to lower the average. Do not hide code with ``# pragma: no cover`` when it
  can be tested,
* a test must not depend on the order of the tests, on the time zone of the
  machine, on the network or on a running database,
* a test of an endpoint goes through the whole application (``client``), see
  above. A model is tested with the SQLite database, only what SQLite cannot
  do is mocked,
* time is UTC everywhere: the database stores UTC and the models return
  aware ``datetime`` objects (``as_utc()``); use ``datetime.now(UTC)``, never
  ``datetime.now()``,
* the production code must not import anything from ``tests``.

Database in tests
-----------------

Tests need no running MySQL. The ``db`` fixture
(``tests/integrity/conftest.py``) creates an in-memory SQLite database from
``poleom/sqlite/init.sql``. ``poleom/lib/sqlite.py`` makes it usable with the
models: the cursor translates MySQL ``%(name)s`` placeholders, supports
the ``with`` statement, raises the MySQL duplicate entry error for
a violated unique constraint, and ignores ``SET sql_mode``. A test of
a model which uses ``DictCursor`` patches
it with the SQLite one:

.. code-block:: python

    @patch("poleom.lib.user.DictCursor", DictCursor)
    class TestLogin:
        ...

SQL which SQLite cannot execute (the ``UNION`` in ``Section.list``, the
``Topic.list`` query) can not be tested this way. The endpoints use
replacements of these two methods from ``tests/helpers.py`` and the unit
tests check the processing of their rows with a mocked cursor. Test such SQL
against a real MySQL by hand.

``conftest.py`` in the root of the repository sets the ``app_*`` variables and
imports the application, so the routes are registered in the same order as
in ``poleom/main.py`` whatever the order of the collected tests is.

ChangeLog
=========

`ChangeLog.rst`_ is written for the people who run and use the forum, not
for developers. A change gets an entry in the same commit when somebody
outside the code can notice it. Refactoring, tests, CI and comments do not.
Write it in plain English, one short item, without file or function names.
Every release has two parts, add the item to the right one under the
``Unreleased`` heading at the top (create it if the newest release is
already there):

``For users``
    What members and moderators see: new features, changed or fixed
    behaviour, changed texts.

``For administrators``
    What the person who installs and runs the forum has to know, or do:

    * a database migration (write the SQL, or say "No database migration"),
    * a new, changed or removed ``app_*`` option,
    * a new requirement (Python, library, MySQL version), a changed
      command or a changed way of the installation,
    * a security fix (so they know to upgrade),
    * a change of the behaviour they may rely on.

A change can belong to both parts, for example a fix that users see and
administrators have to upgrade for. A schema change also updates both
``init.sql`` files. ``tests/test_changelog.py`` checks the structure.

Releasing
=========

#. Rename ``Unreleased`` in `ChangeLog.rst`_ to the version and the date
   (``0.2.0 - 2026-11-20``) and make sure it says "No database migration"
   or describes the migration.
#. Set ``__version__`` in ``poleom/__init__.py`` to the version
   (``0.2.0``, without ``.dev0``) and commit it.
#. Tag the commit ``v0.2.0`` and publish a GitHub release with that tag.
#. The ``Release`` workflow runs all checks and tests, checks that the tag,
   the version and the ChangeLog match, builds the wheel and the source
   package and attaches them to the release. Packages are not uploaded to
   PyPI, because the dependencies ``gevent_mysqldb`` and ``falias`` are
   installed from Git.
#. Set the next version, for example ``0.2.1.dev0``, and add the
   ``Unreleased`` section to the ChangeLog.

Continuous integration
======================

GitHub Actions (``.github/workflows/ci.yml``) runs on every push to
``master`` and on every pull request:

* ``pre-commit`` - all hooks on all files, including ``pylint`` and
  ``mypy`` with the installed project (the same as ``make check``),
* ``tests`` - ``pytest`` with the coverage limits (the total and every file,
  see "Rules for tests") on Python 3.11, 3.12, 3.13 and 3.14; the coverage
  table is in the summary of the run and, for
  a pull request from this repository, in a comment which the workflow
  updates on every push,
* ``package`` - build of the wheel and the source package, ``twine check``,
  ``tools/check-wheel.sh`` (all templates, static files and SQL schemas are
  in it, no editor backups) and an install into a clean virtual environment.

The workflow does not need a database. Run the same locally with
``make check``, ``make test`` and ``make wheel`` before you push.

Git commits
===========

* Commits should be small and atomic: one logical change, not necessarily
  a complete feature. A pull request, on the other hand, must be complete.
* The subject is a short English sentence in the imperative mood
  (``Fix invalid same_site value for login session cookies``).
* Describe what changes in behaviour (new, fixed, changed), not how it is
  implemented. Bullet points are enough for details.
* Run ``make test`` (tests and the coverage limits) before committing;
  ``pre-commit`` runs the other checks
  on every commit.
* A commit with a change visible to users or administrators contains its
  `ChangeLog.rst`_ entry.


.. _README.rst: README.rst
.. _ChangeLog.rst: ChangeLog.rst
.. _docs/auth-backends.rst: docs/auth-backends.rst
