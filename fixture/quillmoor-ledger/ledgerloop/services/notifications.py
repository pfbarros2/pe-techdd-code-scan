"""Email notifications (stubbed transport)."""
import logging

log = logging.getLogger(__name__)

_outbox = []


def send_email(to: str, subject: str, body: str) -> None:
    _outbox.append({"to": to, "subject": subject, "body": body})
    log.info("queued email subject=%r", subject)


def outbox_size() -> int:
    return len(_outbox)
