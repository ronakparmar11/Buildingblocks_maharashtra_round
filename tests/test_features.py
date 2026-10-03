import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from blackbox.config import Settings
from blackbox.features import extract
from blackbox.features.extract import assert_no_leakage, features_for_run
from blackbox.store.models import Run, Step


@pytest.fixture
def sample_run() -> tuple[Run, list[Step], str]:
    fixture_path = (
        Path(__file__).parents[1] / "blackbox" / "api" / "fixtures" / "sample_run.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return (
        Run.model_validate(fixture["run"]),
        [Step.model_validate(step) for step in fixture["steps"]],
        str(fixture["task"]["question"]),
    )


@pytest.fixture
def feature_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    def fake_embed_texts(texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), 4), dtype=np.float32)
        for index, text in enumerate(texts):
            for character in text.lower():
                vectors[index, ord(character) % 4] += 1
            norm = np.linalg.norm(vectors[index])
            if norm:
                vectors[index] /= norm
        return vectors

    monkeypatch.setattr(extract, "embed_texts", fake_embed_texts)
    return Settings(
        DB_PATH=str(tmp_path / "features.db"),
        DATA_DIR=str(tmp_path / "data"),
        ARTIFACTS_DIR=str(tmp_path / "artifacts"),
    )


def _features(
    sample_run: tuple[Run, list[Step], str], settings: Settings
) -> pd.DataFrame:
    run, steps, question = sample_run
    return features_for_run(run, steps, {}, question=question, settings=settings)


def test_features_have_one_row_per_fixture_step(
    sample_run: tuple[Run, list[Step], str], feature_settings: Settings
) -> None:
    frame = _features(sample_run, feature_settings)

    assert len(frame) == len(sample_run[1]) == 12
    assert list(frame["idx"]) == list(range(12))


def test_grounding_detects_answer_missing_from_retrieved_passages(
    sample_run: tuple[Run, list[Step], str], feature_settings: Settings
) -> None:
    run, steps, question = sample_run
    changed_steps = [step.model_copy(deep=True) for step in steps]
    extract_step = next(step for step in changed_steps if step.step_key == "q1/extract#0")
    extract_step.output["answer"] = "Martian"
    extract_step.output_text = "Martian"

    frame = features_for_run(
        run, changed_steps, {}, question=question, settings=feature_settings
    )

    assert frame.loc[extract_step.idx, "answer_in_passages"] == 0
    assert frame.loc[extract_step.idx, "answer_fuzzy"] < 0.5


def test_dag_features_match_fixture_edges(
    sample_run: tuple[Run, list[Step], str], feature_settings: Settings
) -> None:
    frame = _features(sample_run, feature_settings).set_index("idx")

    assert frame.loc[0, "dag_depth"] == 0
    assert frame.loc[0, "n_children"] == 2
    assert frame.loc[0, "n_descendants"] == 11
    assert frame.loc[0, "is_ancestor_of_final"] == 1
    assert frame.loc[11, "n_children"] == 0
    assert frame.loc[11, "is_ancestor_of_final"] == 0


@pytest.mark.parametrize(
    "column",
    ["fault_type", "label", "run_origin", "was_overridden", "reused", "gold_answer"],
)
def test_leakage_guard_rejects_forbidden_columns(column: str) -> None:
    with pytest.raises(ValueError, match=column):
        assert_no_leakage(pd.DataFrame({column: [1]}))


def test_leakage_guard_accepts_documented_features() -> None:
    assert_no_leakage(pd.DataFrame({"name": ["plan"], "latency_z": [0.0]}))