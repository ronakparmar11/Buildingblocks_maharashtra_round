import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from blackbox.api.common import load_fixture, mock_mode
from blackbox.api.schemas import EvalResponse
from blackbox.config import get_settings

router = APIRouter()


@router.get("/eval", response_model=EvalResponse)
def get_evaluation(workspace: str = "hotpot") -> EvalResponse:
    del workspace
    if mock_mode():
        return EvalResponse.model_validate(load_fixture("mock_api.json")["eval"])
    path = Path(get_settings().ARTIFACTS_DIR) / "eval.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Evaluation artifact not found")
    return EvalResponse.model_validate(json.loads(path.read_text(encoding="utf-8")))