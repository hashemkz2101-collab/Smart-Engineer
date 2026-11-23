"""Real email delivery over SMTP (DEC-010).

Provider neutral: it speaks plain SMTP with STARTTLS or implicit TLS, so any provider's
SMTP relay works with configuration only. Messages are sent from a background thread
so the request that triggered them takes the same time whether or not the address
exists (no account enumeration by timing). A delivery failure is logged without the
token or the address and never reaches the caller.
"""

import logging
import smtplib
import ssl
import threading
from email.message import EmailMessage
from urllib.parse import quote

from .auth_service import InvitationNotice
from .config import Settings
from .logging_config import LOGGER_NAME

logger = logging.getLogger(f"{LOGGER_NAME}.mail")
SMTP_TIMEOUT_SECONDS = 15

ROLE_LABELS = {
    "owner": "مالک / کارفرما",
    "architect": "معمار",
    "structural_engineer": "مهندس سازه",
    "mep_engineer": "مهندس تأسیسات",
    "quantity_surveyor": "متره‌گر / برآوردکننده",
    "org_admin": "مدیر سازمان",
    "member": "عضو",
}


def build_message(sender: str, recipient: str, subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body, charset="utf-8")
    return message


class SmtpMailer:
    def __init__(self, settings: Settings, *, background: bool = True) -> None:
        if not settings.mail_configured:
            raise ValueError("SMTP host, sender address and public URL are required")
        self.settings = settings
        self.background = background

    def _link(self, path: str, token: str) -> str:
        return f"{self.settings.public_url}{path}?token={quote(token, safe='')}"

    def send_password_reset(self, email: str, token: str) -> None:
        link = self._link("/reset-password", token)
        self._send(
            email,
            "بازیابی رمز عبور Smart Engineer",
            "برای تعیین رمز عبور تازه این پیوند را باز کنید (یک ساعت اعتبار دارد):\n"
            f"{link}\n\n"
            "اگر شما این درخواست را نداده‌اید، این ایمیل را نادیده بگیرید.\n",
        )

    def send_email_verification(self, email: str, token: str) -> None:
        link = self._link("/verify-email", token)
        self._send(
            email,
            "تأیید ایمیل Smart Engineer",
            "برای تأیید نشانی ایمیل خود این پیوند را باز کنید (۲۴ ساعت اعتبار دارد):\n"
            f"{link}\n\n"
            "اگر شما حساب نساخته‌اید، این ایمیل را نادیده بگیرید.\n",
        )

    def send_invitation(self, email: str, token: str, notice: InvitationNotice) -> None:
        link = self._link("/invitations/accept", token)
        role = ROLE_LABELS.get(notice.role, notice.role)
        where = (
            f"پروژهٔ «{notice.target_name}»"
            if notice.kind == "project"
            else f"سازمان «{notice.target_name}»"
        )
        self._send(
            email,
            f"دعوت به {where} در Smart Engineer",
            f"{notice.inviter_name} شما را به {where} با نقش «{role}» دعوت کرده است.\n\n"
            "برای پذیرش، با حسابی که با همین نشانی ایمیل ساخته‌اید وارد شوید و این پیوند را "
            "باز کنید (۷ روز اعتبار دارد):\n"
            f"{link}\n\n"
            "اگر این دعوت را انتظار نداشتید، آن را نادیده بگیرید؛ بدون پذیرش شما "
            "هیچ دسترسی‌ای ساخته نمی‌شود.\n",
        )

    def _send(self, recipient: str, subject: str, body: str) -> None:
        message = build_message(self.settings.mail_from, recipient, subject, body)
        if self.background:
            threading.Thread(target=self._deliver, args=(message,), daemon=True).start()
        else:
            self._deliver(message)

    def _deliver(self, message: EmailMessage) -> None:
        settings = self.settings
        try:
            if settings.smtp_security == "ssl":
                client = smtplib.SMTP_SSL(
                    settings.smtp_host,
                    settings.smtp_port,
                    timeout=SMTP_TIMEOUT_SECONDS,
                    context=ssl.create_default_context(),
                )
            else:
                client = smtplib.SMTP(
                    settings.smtp_host, settings.smtp_port, timeout=SMTP_TIMEOUT_SECONDS
                )
            with client:
                if settings.smtp_security == "starttls":
                    client.starttls(context=ssl.create_default_context())
                if settings.smtp_username:
                    client.login(settings.smtp_username, settings.smtp_password or "")
                client.send_message(message)
        except Exception as error:  # noqa: BLE001 - delivery must never break a request
            # Only the error type: messages can contain the address or server details.
            logger.error("email delivery failed", extra={"error_type": type(error).__name__})
