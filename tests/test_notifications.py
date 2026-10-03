from collections.abc import Iterator
from contextlib import contextmanager
from email.message import EmailMessage
from pathlib import Path
from typing import Any, ClassVar, Self

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from blackbox.config import Settings
from blackbox.notify import rules as rules_module
from blackbox.notify import worker as worker_module
from blackbox.notify.mailer import Mailer
from blackbox.notify.rules import evaluate_rules
from blackbox.notify.templates import format_inr, render_email
from blackbox.notify.worker import NotificationWorker
from blackbox.store.models import NotificationLog


class SMTPRecorder:
    instances: ClassVar[list["SMTPRecorder"]] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.login_args: tuple[str, str] | None = None
        self.message: EmailMessage | None = None
        self.instances.append(self)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, user: str, password: str) -> None:
        self.login_args = (user, password)

    def send_message(self, message: EmailMessage) -> None:
        self.message = message

    def noop(self) -> None:
        return None


def test_mailer_sends_multipart_plain_and_html(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SMTPRecorder.instances.clear()
    monkeypatch.setattr("smtplib.SMTP", SMTPRecorder)
    settings = Settings(
        SMTP_HOST="mail.local",
        SMTP_PORT=2525,
        SMTP_USER="mailer",
        SMTP_PASSWORD="super-secret",
        SMTP_STARTTLS=1,
    )
    rendered = render_email("test", {"workspace_name": "Nimbu Living support"})

    Mailer(settings).send(["team@example.com"], rendered)

    smtp = SMTPRecorder.instances[0]
    assert smtp.timeout == 10
    assert smtp.started_tls
    assert smtp.login_args == ("mailer", "super-secret")
    assert smtp.message is not None and smtp.message.is_multipart()
    assert smtp.message["Subject"] == "Test email from Black Box"
    content_types = {part.get_content_type() for part in smtp.message.walk()}
    assert {"text/plain", "text/html"} <= content_types
    assert "super-secret" not in smtp.message.as_string()


def test_subjects_and_indian_currency_format_are_exact() -> None:
    opened = render_email(
        "incident_opened",
        {"category": "refund", "n_runs": 14, "workspace_name": "Nimbu Living support"},
    )
    digest = render_email(
        "daily_digest",
        {
            "open_incidents": 3,
            "estimated_cost": 6300,
            "workspace_name": "Nimbu Living support",
        },
    )

    assert opened.subject == (
        "New incident: refund questions answered wrong (14 conversations)"
    )
    assert digest.subject == (
        "Daily summary for Nimbu Living support: 3 open incidents, "
        "₹6,300 estimated cost"
    )
    assert format_inr(1_234_567) == "₹12,34,567"


def _sessions(engine: Any) -> Any:
    @contextmanager
    def sessions() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    return sessions


def test_failed_delivery_is_logged_without_password(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'notify.db'}")
    SQLModel.metadata.create_all(engine)
    sessions = _sessions(engine)
    monkeypatch.setattr(worker_module, "get_session", sessions)
    settings = Settings(SMTP_PASSWORD="do-not-store")

    class FailingMailer:
        def send(self, *_args: object) -> None:
            raise OSError("connection failed with do-not-store")

    with Session(engine) as session:
        row = NotificationLog(
            workspace="nimbu",
            rule_kind="test",
            recipients=["team@example.com"],
            subject="Test email from Black Box",
            html="<p>Test</p>",
            text="Test",
            status="queued",
        )
        session.add(row)
        session.commit()
        notification_id = row.notification_id

    notification_worker = NotificationWorker(
        settings=settings, mailer=FailingMailer()  # type: ignore[arg-type]
    )
    notification_worker._deliver(notification_id)

    with Session(engine) as session:
        stored = session.get(NotificationLog, notification_id)
        assert stored is not None
        assert stored.status == "failed"
        assert stored.error == "connection failed with ***"
        assert "do-not-store" not in str(stored.model_dump())


def test_rule_throttling_logs_second_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'rules.db'}")
    SQLModel.metadata.create_all(engine)
    sessions = _sessions(engine)
    monkeypatch.setattr(rules_module, "get_session", sessions)
    monkeypatch.setattr(
        rules_module,
        "get_settings",
        lambda: Settings(NOTIFY_DEFAULT_EMAIL="team@example.com"),
    )

    class RecordingWorker:
        def enqueue(
            self,
            workspace: str,
            rule_kind: str,
            recipients: list[str],
            rendered: Any,
            incident_id: str | None = None,
        ) -> NotificationLog:
            with Session(engine) as session:
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
                return row

    recorder = RecordingWorker()
    first = evaluate_rules(
        "daily_digest", "nimbu", notification_worker=recorder  # type: ignore[arg-type]
    )
    second = evaluate_rules(
        "daily_digest", "nimbu", notification_worker=recorder  # type: ignore[arg-type]
    )

    assert first is not None
    assert second is None
    with Session(engine) as session:
        statuses = list(
            session.exec(
                select(NotificationLog.status).order_by(NotificationLog.created_at)
            ).all()
        )
    assert statuses == ["queued", "throttled"]