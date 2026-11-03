=========
ChangeLog
=========

Changes of Poleom by release, the newest is on top. Every release has two
parts: what **users** of the forum can see and what **administrators** have
to know or do when they install or upgrade it (new or changed options,
database migrations, new requirements, removed features). See
`CONTRIBUTING.rst`_ for the rules of writing it.

Unreleased
==========

For users
---------

- A forum can use an external service to log the users in (see the
  administrators part). Members then change their name, e-mail and password
  there, only the signature stays in the account settings.
- Fixed: HTML written in a post, a signature or a section description is no
  longer rendered as a part of the page, it is shown as text. The
  reStructuredText directives ``raw`` and ``include`` do not work any more.
- Fixed: a post with exactly one attached file was saved without it.
- Fixed: a wrong new password on the reset password page showed the form for
  the e-mail again, now it shows the password form with the error.
- Fixed: a section form sent with an unknown language ended with an error
  page.
- Fixed: attempts to unban a user who is not banned or to change a deleted
  user were answered with "501 Not Implemented", now they get the right
  status code.
- Fixed: the time of the validity of the e-mail links (registration, password
  reset) and the times of posts were wrong on servers which do not run in
  the UTC time zone.
- Fixed typos in the e-mail about the enabled account, in the e-mail about
  the password reset and in the section form.

For administrators
------------------

- Security: posts, signatures and descriptions could contain HTML scripts
  and read files of the server by the ``include`` directive. Upgrade as soon
  as possible; no database change is needed, already stored texts are
  rendered safely.
- The package can be installed into a virtual environment now (``pip install
  poleom-*.whl``): it contains the templates, static files and SQL schemas.
  See "Installation" in `README.rst`_.
- New command ``poleom-passwd`` generates the SQL to set the password of
  the first administrator.
- The default of ``app_theme`` is the directory of the installed package, it
  was ``./poleom`` in the current directory. Set ``app_theme`` explicitly if
  you run a modified copy of the templates.
- New option ``app_auth_backend`` selects an authentication plugin, see
  `docs/auth-backends.rst`_. Without it nothing changes. With a plugin the
  registration, the login by the password, the reset of the password and
  the change of the e-mail of the forum are turned off.
- Database migration: the table ``users`` gets the column ``auth_sub`` for
  the users of an external authentication plugin and the password may be
  ``NULL``. Run ``poleom/mysql/migrations/0.2.0.sql`` once, see "Upgrade" in
  `README.rst`_. The forum works the same as before.

0.1.0 - 2026-09-04
==================

The first release.

For users
---------

- Sections and topics in several languages; the interface language follows
  the language of the section. Topics are sorted by the last post.
- Posts written in Markdown or reStructuredText with a preview, editing of
  posts by their author and attachments.
- Registration with an e-mail confirmation, password reset, user profiles.
- Roles member, moderator and administrator, banning of users, administration
  of sections, private sections with a list of allowed users.
- Open Graph tags for sharing links to topics.
- RSS feeds of topics, sections and languages.

For administrators
------------------

- Requires Python 3.11+, MySQL or MariaDB, an SMTP server and uWSGI.
- The database schema is ``poleom/mysql/init.sql``; the default administrator
  ``root@localhost`` has no password, set it directly in the database.
- Configured by the ``app_*`` environment variables (``app_db``,
  ``app_secret_key``, ``app_smtp``, ``app_attachments``, ``app_theme``,
  ``app_default_lang``, ...), see `README.rst`_. Uploaded files are stored in
  the ``app_attachments`` directory, which must be writable.


.. _CONTRIBUTING.rst: CONTRIBUTING.rst
.. _README.rst: README.rst
.. _docs/auth-backends.rst: docs/auth-backends.rst
