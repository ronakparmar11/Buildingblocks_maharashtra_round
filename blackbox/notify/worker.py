from __future__ import annotations

import smtplib
from datetime import UTC, datetime
from queue import Queue
from threading import Event, Lock, Thread

from blackbox.config import Settings, get_settings
from blackbox.notify.mailer import Mailer
from blackbox.notify.templates import RenderedEmail
from blackbox.store.db import get_session
from blackbox.store.models import IncidentEvent, NotificationLog


class NotificationWorker:
    def __init__(
        self, settings: Settings | None = None, mailer: Mailer | None = None
    ) -> None:
        self.settings = settings or get_settings()
        self.mailer = mailer or Mailer(self.settings)
        self._queue: Queue[str | None] = Queue()
        self._stop = Event()
        self._thread: Thread | None = None
        self._lock = Lock()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = Thread(
                target=self._run, name="blackbox-notify", daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=2)

    def enqueue(
        self,
        workspace: str,
        rule_kind: str,
        recipients: list[str],
        rendered: RenderedEmail,
        incident_id: str | None = None,
    ) -> NotificationLog:
        with get_session() as session:
            row = NotificationLog(
                workspace=workspace,
                rule_kind=rule_kind,
                incident_id=incident_id,
                recipients=recipients,
                subject=rendered.subject,
                html=rendered.html,
                text=rendered.text,
                status="queued",
            )
            session.add(row)
            session.commit()
            session.refresh(row)
        self.start()
        self._queue.put(row.notification_id)
        return row

    def wait(self) -> None:
        self._queue.join()

    def _run(self) -> None:
        while not self._stop.is_set():
            notification_id = self._queue.get()
            try:
                if notification_id is None:
                    return
                self._deliver(notification_id)
            finally:
                self._queue.task_done()

    def _deliver(self, notification_id: str) -> None:
        with get_session() as session:
            row = session.get(NotificationLog, notification_id)
            if row is None:
                return
            if (
                self.settings.BLACKBOX_DEMO_MODE
                and self.settings.SMTP_HOST not in {"localhost", "127.0.0.1", "::1"}
            ):
                return
            rendered = RenderedEmail(
                subject=row.subject, text=row.text, html=row.html
            )
            try:
                self.mailer.send(row.recipients, rendered)
            except (OSError, smtplib.SMTPException) as error:
                message = str(error)
                if self.settings.SMTP_PASSWORD:
                    message = message.replace(self.settings.SMTP_PASSWORD, "***")
                row.status = "failed"
                row.error = message
            else:
                row.status = "sent"
                row.sent_at = datetime.now(UTC)
                row.error = None
                if row.incident_id is not None:
                    session.add(
                        IncidentEvent(
                            incident_id=row.incident_id,
                            kind="notified",
                            text=f"Notification sent: {row.subject}",
                            meta={"notification_id": row.notification_id},
                        )
                    )
            session.add(row)
            session.commit()


worker = NotificationWorker()