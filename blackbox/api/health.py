import json
from pathlib import Path

from fastapi import APIRouter
from sqlmodel import func, select

from blackbox.api.common import load_fixture, mock_mode
from blackbox.api.schemas import HealthResponse
from blackbox.config import get_settings
from blackbox.store.db import get_session
from blackbox.store.models import Run

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    settings = get_settings()
    if mock_mode():
        model_version = load_fixture("mock_api.json")["diagnosis"]["model_version"]
        return HealthResponse(
            status="ok", demo_mode=True, model_version=model_version, n_runs=1
        )
    metadata_path = Path(settings.ARTIFACTS_DIR) / "model_meta.json"
    model_version = "unavailable"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        model_version = str(metadata.get("version", "unavailable"))
    with get_session() as session:
        n_runs = int(session.exec(select(func.count()).select_from(Run)).one())
    return HealthResponse(
        status="ok",
        demo_mode=bool(settings.BLACKBOX_DEMO_MODE),
        model_version=model_version,
        n_runs=n_runs,
    )