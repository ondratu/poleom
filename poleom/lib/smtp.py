"""Library contains some end-user classes for mailing.

Typical use of library could be check, if input email is correct, and send
email by Smtp class.

>>> from polem.lib.smtp import Smtp, Email
>>> smtp = Smtp('smtp://localhost/no-replay@domain.xy')
>>> recipient = get_recipient()     # as get_recipient is your function
>>> if Email.check(recipient):
>>>     try:
>>>         smtp.send_email('Subject', recipient, 'Mail body')
>>>     except SMTPException as e:
>>>         print('Something wrong: %s' % e)
"""

import logging
import re
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP, SMTP_SSL, SMTPException
from time import localtime, strftime

# Data Source Name regular expression for smtp server
re_dsn = re.compile(
    r"""(?P<protocol>(smtp|smtps))://          # driver
                                ((?P<user>[\w\.@\-]+)?
                                (:(?P<passwd>[\w\.\@\!\?\#]+))?@)?
                                (?P<host>[\w\.]+)?
                                (:(?P<port>[0-9]+))?
                                /(?P<sender>[\w\.\-]+@[\w\.\-]+)?
                                (::(?P<charset>\w+))?
                    """, re.X)
# smtp://localhost/mcbig@localhost

logger = logging.getLogger(__name__)


class Smtp:
    """Class for smtp 'connection'.

    In fact, class parse Data Source Name for smtp and not do connection at
    initialization process. But send_* methods do that.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, dsn):
        """Raise RuntimeError when dsn is not valid.

        Data Source Name for smtp looks like: smtp://localhost/user@localhost
        """
        match = re_dsn.match(dsn)
        if not match:
            msg = "Not valid Data Source Name for SMTP in `app_smtp`!"
            raise ValueError(msg)

        self.protocol = match.group("protocol")
        self.host = match.group("host") or "localhost"
        self.port = int(match.group("port") or 25)
        self.sender = match.group("sender") or ""
        self.charset = match.group("charset") or "utf-8"
        self.user = match.group("user") or None
        self.passwd = match.group("passwd") or None

        self.xmailer = "Poleom (https://poleom.zeropage.cz)"
        self.timeout = socket._GLOBAL_DEFAULT_TIMEOUT
        self._class = SMTP_SSL if self.protocol == "smtps" else SMTP

    def __str__(self):
        """Return Data Source Name of set values."""
        return f"{self.protocol}://%s%s%s%s:%d/%s::%s" % \
            (self.protocol, self.user or "", self.passwd or "",
             "@" if self.user or self.passwd else "",
             self.host, self.port,
             self.sender, self.charset)

    def send_email_txt(self, subject, recipient, body, **kwargs):
        """Send email as text/plain content type.

        Keyword arguments:
            - `sender` default sender is set by Data Source Name
            - `reply` Reply-To header
            - `xmailer` X-Mailer header, default is Falias
        """
        msg = MIMEText(body)
        msg.set_charset(self.charset)
        msg["Subject"] = subject
        msg["From"] = kwargs.get("sender", self.sender)
        msg["To"] = recipient
        msg["Date"] = strftime("%a, %d %b %Y %X %z", localtime())

        # headers
        if "reply" in kwargs:
            msg["Reply-To"] = kwargs["reply"]

        msg["X-Mailer"] = kwargs.get("xmailer", self.xmailer)

        logger.info("SMTP: Sub:%s, From:%s, To:%s", msg["Subject"],
                    msg["From"], msg["To"])

        try:
            smtp = self._class(self.host, self.port, timeout=self.timeout)

            if self.user:
                smtp.login(self.user, self.passwd)
            smtp.sendmail(msg["From"], msg["To"], msg.as_string())
        except SMTPException:
            logger.exception("SMTP: Sending email failed")
            raise
        finally:
            smtp.close()

    def send_email_alternative(self, subject, recipient, txt_body, html_body,
                               **kwargs):
        """Send email as text/html with alternative plain/text content.

        Keyword arguments:
            - `sender` default sender is set by Data Source Name
            - `reply` Reply-To header
            - `xmailer` X-Mailer header, default is Falias
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = kwargs.get("sender", self.sender)
        msg["To"] = recipient
        msg["Date"] = strftime("%a, %d %b %Y %X %z", localtime())

        # headers
        if "reply" in kwargs:
            msg["Reply-To"] = kwargs["reply"]
        msg["X-Mailer"] = kwargs.get("xmailer", self.xmailer)

        # body
        part1 = MIMEText(txt_body, "plain")
        part1.set_charset(self.charset)
        part2 = MIMEText(html_body, "html")
        part2.set_charset(self.charset)

        msg.attach(part1)
        msg.attach(part2)

        logger.info("SMTP: Sub:%s, From:%s, To:%s", msg["Subject"],
                    msg["From"], msg["To"])

        try:
            smtp = self._class(self.host, self.port, timeout=self.timeout)

            if self.user:
                smtp.login(self.user, self.passwd)
            smtp.sendmail(msg["From"], msg["To"], msg.as_string())
        except SMTPException:
            logger.exception("SMTP: Sendig email failed")
            raise
        finally:
            smtp.close()


# Regular expression for check valid email address
re_email = re.compile(r"^[\w\.\-]+@[\w\.\-]+$")


class Email:
    """Class for automatic checking email address."""

    def __init__(self, value):
        if not Email.check(value):
            msg = f"{value} not match as email"
            raise RuntimeError(msg)
        self.value = value

    def __str__(self):
        return self.value

    @staticmethod
    def check(value):
        """Return True if value could be valid email address."""
        return bool(re_email.match(value))
