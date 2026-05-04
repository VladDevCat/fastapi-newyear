import smtplib
from email.message import EmailMessage
from html import escape

from app.common.config import settings


class EmailService:
    def validate_config(self) -> None:
        settings.validate_smtp_config()

    def send_welcome_email(
        self,
        *,
        to: str,
        display_name: str | None,
        user_id: str,
    ) -> None:
        name = display_name or to.split("@", 1)[0]
        message = EmailMessage()
        message["Subject"] = "Welcome to Holiday Prep"
        message["From"] = settings.SMTP_FROM
        message["To"] = to
        login_url = settings.SMTP_LOGIN_URL
        message.set_content(self._plain_template(name=name, user_id=user_id, login_url=login_url))
        message.add_alternative(self._html_template(name=name, user_id=user_id, login_url=login_url), subtype="html")

        if settings.SMTP_SECURE:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
                self._login_if_configured(smtp)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
                self._login_if_configured(smtp)
                smtp.send_message(message)

    def _login_if_configured(self, smtp) -> None:
        if settings.SMTP_USER and settings.SMTP_PASS:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASS)

    def _plain_template(self, *, name: str, user_id: str, login_url: str) -> str:
        return "\n".join(
            [
                f"Hello, {name}!",
                "",
                "Your Holiday Prep account has been created.",
                f"Account id: {user_id}",
                "",
                f"Sign in here: {login_url}",
                "",
                "You can now plan your New Year preparation list.",
            ]
        )

    def _html_template(self, *, name: str, user_id: str, login_url: str) -> str:
        safe_name = escape(name)
        safe_user_id = escape(user_id)
        safe_login_url = escape(login_url, quote=True)
        return f"""<!doctype html>
<html>
  <body>
    <p>Hello, {safe_name}!</p>
    <p>Your Holiday Prep account has been created.</p>
    <p>Account id: <strong>{safe_user_id}</strong></p>
    <p><a href="{safe_login_url}">Sign in to your account</a></p>
    <p>You can now plan your New Year preparation list.</p>
  </body>
</html>"""
