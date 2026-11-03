======
Poleom
======

Poleom is a simple multilingual web forum written in Python. It is a WSGI
application built on top of `PoorWSGI <https://poorwsgi.readthedocs.io/>`_
with a MySQL/MariaDB database.

Features
--------

* sections, topics and posts, each section belongs to one language
* posts written in reStructuredText (with live preview) and attachments
* registration with e-mail confirmation, password reset, user profiles
* roles ``MEMBER``, ``MODERATOR`` and ``ADMIN``, banning of users
* per-section user permissions
* RSS feeds for topics, sections and languages

Requirements
------------

* Python 3.11 or newer
* MySQL or MariaDB
* an SMTP server for sending e-mails (registration, password reset)
* `uWSGI <https://uwsgi-docs.readthedocs.io/>`_ with the Python and gevent
  support, it runs the application
* ``git`` on the machine where dependencies are installed, two of them
  (``gevent_mysqldb``, ``falias``) are installed from GitHub

Installation
------------

Poleom is an ordinary Python package. It contains the templates, static
files (``assets``) and the SQL schemas, so it is enough to install it into
a virtual environment on the server. There are two ways how to get it there.

**Built package.** Build a wheel on your machine, copy it to the server and
install it:

.. code-block:: sh

    uv build --wheel                        # or: python -m build --wheel
    scp dist/poleom-*.whl server:/srv/poleom/

    # on the server
    cd /srv/poleom
    python3 -m venv venv
    venv/bin/pip install poleom-*.whl uwsgi

**Source tree.** Copy the sources (for example by ``rsync``) and install them
on the server:

.. code-block:: sh

    rsync -rvz --exclude=.venv --exclude=__pycache__ \
        poleom pyproject.toml README.rst LICENSE server:/srv/poleom/src/

    # on the server
    cd /srv/poleom
    python3 -m venv venv
    venv/bin/pip install ./src uwsgi

The upgrade is the same command with ``pip install -U``, followed by
a reload of uWSGI.

Suggested layout on the server::

    /srv/poleom/
        venv/            virtual environment with Poleom and uWSGI
        etc/uwsgi.ini    configuration, see below
        attachments/     uploaded files, writable by the uWSGI user

Database
~~~~~~~~

Create a database with the ``utf8mb4`` charset and load the schema, which is
a part of the installed package:

.. code-block:: sh

    mysql -e "CREATE DATABASE poleom CHARACTER SET utf8mb4"
    mysql poleom < venv/lib/python3.*/site-packages/poleom/mysql/init.sql

First administrator
~~~~~~~~~~~~~~~~~~~

The schema contains the default administrator ``root@localhost`` with an empty
password, so nobody can log in until you set one. Passwords are stored as
bcrypt hashes (of the SHA3-512 digest of the password), so they can not be
written to the database directly. The ``poleom-passwd`` command, which is
installed with the package into the virtual environment, generates the SQL
for you:

.. code-block:: sh

    venv/bin/poleom-passwd 'my secret password'

The optional second argument is the number of hashing rounds (default 12).
The output has two statements:

.. code-block:: sql

    -- First setup
    UPDATE users SET password='$2b$12$...', email='your@login'
        WHERE email='root@localhost';
    -- Password reset --
    UPDATE users SET password='$2b$12$...'
        WHERE email='your@login';

For the **first setup** replace ``your@login`` with the e-mail address of the
administrator, then run the first statement in the database, for example
``mysql poleom -e "UPDATE ..."``. The administrator then logs in with that
e-mail and the password. The second statement resets a forgotten password of
an existing user; use it only when the user can not use the password reset
by e-mail.

The password is visible in the process list and in the shell history. Run
the command with a space in front of it (when ``HISTCONTROL=ignorespace`` is
set) or remove it from the history afterwards, and use a temporary password
which is changed after the first login in the account settings.

Configuration
~~~~~~~~~~~~~

The application is configured by environment variables with the ``app_``
prefix. When uWSGI is used, they are set with ``env =`` in the ini file.

``app_db`` (required)
    ``mysql://user:password@host:port/database``
``app_secret_key`` (required)
    key used for signing session cookies
``app_smtp``
    ``smtp[s]://user:password@host:port/sender``
``app_attachments`` (``./attachments``)
    writable directory for uploaded files
``app_title`` (``Poleom``)
    forum title
``app_default_lang`` (``en``)
    language used for ``/``
``app_theme`` (``./poleom``)
    directory with templates
``app_terms_en``, ``app_terms_cs`` (``/not-found?lang=...``)
    URLs of the terms of use
``app_change_request_ttl`` (``86400``)
    validity of e-mail links in seconds
``app_auth_backend`` (the accounts of the forum)
    ``module:Class`` of an authentication plugin, see
    ``docs/auth-backends.rst``
``app_debug`` (``False``)
    ``True`` turns on debug mode

Upgrade
~~~~~~~

Install the new version (see above) and stop uWSGI. The changes of the
database schema are SQL files in ``poleom/mysql/migrations/`` of the installed
package, named by the version which needs them (``0.2.0.sql``).
``ChangeLog.rst`` says which release has a migration. Run the files of all
versions **newer than the one you upgrade from**, up to the new one, in the
version order, each only once:

.. code-block:: sh

    cd venv/lib/python3.*/site-packages/poleom/mysql/migrations
    mysql poleom < 0.2.0.sql

For example, an upgrade from 0.1.0 to 0.3.0 runs ``0.2.0.sql`` and then
``0.3.0.sql``. A new installation loads only ``init.sql``. Back up the
database before the upgrade.

External authentication
~~~~~~~~~~~~~~~~~~~~~~~

By default the forum has its own accounts. The users can be logged in by
an external service instead, with a plugin set by ``app_auth_backend``.
How the plugin works and how to configure it is described in
``docs/auth-backends.rst``; how to write one is in ``CONTRIBUTING.rst``.

Running
-------

Copy ``example/etc/uwsgi.ini`` to ``/srv/poleom/etc/uwsgi.ini`` and adjust it
for production:

* set ``app_db``, ``app_smtp``, ``app_attachments`` (absolute path) and
  a new random ``app_secret_key``; remove ``app_debug`` and the example
  values,
* remove ``python-path``, ``python-autoreload`` and ``chdir``; the package
  is imported from the virtual environment, add
  ``virtualenv = /srv/poleom/venv``,
* run the processes under an unprivileged user (``uid``, ``gid``) and
  put a reverse proxy (nginx, Apache) with HTTPS in front of the ``http``
  socket.

.. code-block:: sh

    /srv/poleom/venv/bin/uwsgi --ini /srv/poleom/etc/uwsgi.ini

Run it from the init system of the server (for example a systemd unit), so it
starts at boot and restarts after a failure. The application writes logs to
the standard error output of uWSGI.

License
-------

Poleom is released under the BSD 3-Clause License, see ``LICENSE``.
