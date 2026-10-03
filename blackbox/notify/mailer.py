import smtplib
import time
from email.message import EmailMessage

from blackbox.config import Settings, get_settings
from blackbox.notify.templates import RenderedEmail


class Mailer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _connection(self) -> smtplib.SMTP:
        connection_type = smtplib.SMTP_SSL if self.settings.SMTP_SSL else smtplib.SMTP
        return connection_type(
            self.settings.SMTP_HOST,
            self.settings.SMTP_PORT,
            timeout=10,
        )

    def _message(self, recipients: list[str], rendered: RenderedEmail) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self.settings.SMTP_FROM
        message["To"] = ", ".join(recipients)
        message["Subject"] = rendered.subject
        message.set_content(rendered.text)
        message.add_alternative(rendered.html, subtype="html")
        return message

    def _authenticate(self, smtp: smtplib.SMTP) -> None:
        if self.settings.SMTP_STARTTLS and not self.settings.SMTP_SSL:
            smtp.starttls()
        if self.settings.SMTP_USER:
            smtp.login(self.settings.SMTP_USER, self.settings.SMTP_PASSWORD)

    def send(self, recipients: list[str], rendered: RenderedEmail) -> None:
        message = self._message(recipients, rendered)
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with self._connection() as smtp:
                    self._authenticate(smtp)
                    smtp.send_message(message)
                return
            except (OSError, smtplib.SMTPException) as error:
                last_error = error
                if attempt < 2:
                    time.sleep(0.25 * (2**attempt))
        assert last_error is not None
        raise last_error

    def check_connection(self) -> tuple[bool, str | None]:
        try:
            with self._connection() as smtp:
                self._authenticate(smtp)
                smtp.noop()
            return True, None
        except (OSError, smtplib.SMTPException) as error:
            return False, str(error)