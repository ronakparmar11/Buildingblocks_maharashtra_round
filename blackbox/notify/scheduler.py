from datetime import date, datetime
from threading import Event, Thread

from blackbox.config import get_settings
from blackbox.notify.rules import evaluate_rules


class DigestScheduler:
    def __init__(self, workspace: str = "nimbu") -> None:
        self.workspace = workspace
        self._stop = Event()
        self._thread: Thread | None = None
        self._last_sent: date | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._run, name="blackbox-digest", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.wait(60):
            now = datetime.now().astimezone()
            if (
                now.hour == get_settings().DIGEST_HOUR_LOCAL
                and self._last_sent != now.date()
            ):
                evaluate_rules("daily_digest", self.workspace)
                self._last_sent = now.date()


scheduler = DigestScheduler()