from fastapi import APIRouter, HTTPException

from blackbox.api.common import (
    fixture_run_summary,
    load_fixture,
    mock_mode,
    run_summary,
)
from blackbox.api.schemas import CompareResponse
from blackbox.store.db import get_session
from blackbox.store.models import Run

router = APIRouter()


@router.get("/compare", response_model=CompareResponse)
def compare_runs(a: str, b: str, workspace: str = "hotpot") -> CompareResponse:
    if mock_mode():
        if workspace != "hotpot":
            raise HTTPException(status_code=404, detail="Run not found")
        return _mock_compare(a, b)
    from blackbox.replay.compare import compare

    with get_session() as session:
        run_a = session.get(Run, a)
        run_b = session.get(Run, b)
        if (
            run_a is None
            or run_b is None
            or run_a.workspace != workspace
            or run_b.workspace != workspace
        ):
            raise HTTPException(status_code=404, detail="Run not found")
        result = compare(run_a, run_b)
        return CompareResponse(
            a=run_summary(session, run_a),
            b=run_summary(session, run_b),
            first_divergence=result["first_divergence"],
            rows=[
                {
                    "step_key": row["step_key"],
                    "status": row["status"],
                    "a_step": row["a_step"],
                    "b_step": row["b_step"],
                    "text_diff": row["text_diff"],
                }
                for row in result["rows"]
            ],
        )


def _mock_compare(a: str, b: str) -> CompareResponse:
    sample = load_fixture("sample_run.json")
    replay = load_fixture("mock_api.json")["replay"]
    rows = []
    for source in sample["steps"]:
        target = dict(source)
        target["run_id"] = b
        target["step_id"] = f"replay_{source['step_id']}"
        status = "same"
        text_diff: list[str] = []
        if source["step_key"] == "synthesize":
            target["output"] = {"answer": "yes", "reason": "Both are American."}
            target["output_text"] = "yes"
            target["output_hash"] = "repaired-synthesis-output"
            target["reused"] = False
            status = "changed"
            text_diff = ["- no", "+ yes"]
        else:
            target["reused"] = True
        rows.append(
            {
                "step_key": source["step_key"],
                "status": status,
                "a_step": source,
                "b_step": target,
                "text_diff": text_diff,
            }
        )
    return CompareResponse(
        a=fixture_run_summary({"run_id": a}),
        b=fixture_run_summary(
            {
                "run_id": b,
                "origin": "replay",
                "parent_run_id": a,
                "outcome": replay["outcome"],
                "score_f1": replay["score_f1"],
            }
        ),
        first_divergence="synthesize",
        rows=rows,
    )