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
the environment (see ``README.rst`` for the list):

.. code-block:: sh

    python -m poleom

The forum is then available at http://localhost:8000/. To log in as
the default administrator ``root@localhost``, set its password with
``poleom-passwd``, see "First administrator" in ``README.rst``.

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
how to upgrade an existing database.

Configuration and documentation
-------------------------------

A new or changed ``app_*`` option, installation step or command updates
``README.rst`` in the same commit. The documentation is written in
reStructuredText and checked by the ``rst-linter`` pre-commit hook.

Tests
=====

.. code-block:: sh

    make test                                          # all tests
    .venv/bin/python -m pytest tests/integrity/test_login.py   # one file

Pytest is configured in ``pyproject.toml``. Every run prints the coverage
report with missing lines and writes ``coverage.xml``; doctests of
the modules are run as well.

Rules for tests:

* every new feature and every bug fix comes with a test,
* the coverage of the new or changed code should be at least 80 %,
* the overall coverage must not go down: ``fail_under`` in the
  ``[tool.coverage.report]`` section of ``pyproject.toml`` fails the tests
  below it. The coverage is still low, raise the number whenever it grows,
  never lower it,
* the production code must not import anything from ``tests``.

Database in tests
-----------------

Tests need no running MySQL. The ``db`` fixture
(``tests/integrity/conftest.py``) creates an in-memory SQLite database from
``poleom/sqlite/init.sql``. ``poleom/lib/sqlite.py`` makes it usable with the
models: the cursor translates MySQL ``%(name)s`` placeholders and supports
the ``with`` statement. A test of a model which uses ``DictCursor`` patches
it with the SQLite one:

.. code-block:: python

    @patch("poleom.lib.user.DictCursor", DictCursor)
    class TestLogin:
        ...

SQL which SQLite cannot execute (e.g. ``NOW()``) can not be tested this way,
test such code against a real MySQL by hand.

ChangeLog
=========

``ChangeLog.rst`` is written for the people who run and use the forum, not
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

#. Rename ``Unreleased`` in ``ChangeLog.rst`` to the version and the date
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
* ``tests`` - ``pytest`` with the coverage threshold on Python 3.11, 3.12,
  3.13 and 3.14,
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
* Run ``make test`` before committing; ``pre-commit`` runs the other checks
  on every commit.
* A commit with a change visible to users or administrators contains its
  ``ChangeLog.rst`` entry.
