from fastapi import APIRouter

from blackbox.api.common import load_fixture
from blackbox.api.schemas import GoldenDemoResponse

router = APIRouter(prefix="/demo")


@router.get("/golden", response_model=GoldenDemoResponse)
def golden_demo() -> GoldenDemoResponse:
    evidence = load_fixture("mock_api.json")
    return GoldenDemoResponse.model_validate(
        {
            "run": load_fixture("sample_run.json"),
            "diagnosis": evidence["diagnosis"],
            "repair": evidence["repair"],
        }
    )