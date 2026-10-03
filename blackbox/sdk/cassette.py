from collections.abc import Callable
from typing import Any, TypedDict

from sqlmodel import Session

from blackbox.config import get_settings
from blackbox.store.hashing import sha256_json
from blackbox.store.models import Cassette as CassetteRow


class CassetteMissError(RuntimeError):
    pass


class Usage(TypedDict, total=False):
    tokens_in: int
    tokens_out: int
    model: str


class Cassette:
    def __init__(self, session: Session, demo_mode: bool | None = None) -> None:
        self.session = session
        self.demo_mode = (
            bool(get_settings().BLACKBOX_DEMO_MODE) if demo_mode is None else demo_mode
        )

    def get_or_call(
        self,
        kind: str,
        model: str,
        payload: dict[str, Any],
        temperature: float,
        sample_idx: int,
        call_fn: Callable[[], tuple[dict[str, Any], Usage]],
    ) -> tuple[dict[str, Any], Usage, bool]:
        key = sha256_json(
            {
                "kind": kind,
                "model": model,
                "payload": payload,
                "temperature": temperature,
                "sample_idx": sample_idx,
            }
        )
        stored = self.session.get(CassetteRow, key)
        if stored is not None:
            return (
                stored.response,
                {
                    "tokens_in": stored.tokens_in,
                    "tokens_out": stored.tokens_out,
                    "model": model,
                },
                True,
            )

        if self.demo_mode:
            raise CassetteMissError(f"Cassette miss in demo mode: {key}")

        response, usage = call_fn()
        row = CassetteRow(
            key=key,
            kind=kind,
            response=response,
            tokens_in=usage.get("tokens_in", 0),
            tokens_out=usage.get("tokens_out", 0),
        )
        self.session.add(row)
        self.session.commit()
        return response, usage, False
