from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from random import Random
from typing import Any

import numpy as np
import pandas as pd

from blackbox.llm.base import LLMClient
from blackbox.sdk.cassette import Cassette
from blackbox.store.models import Step


def _scores_by_group(
    groups: Sequence[int], score_fn: Callable[[int, int], Sequence[float]]
) -> np.ndarray:
    scores: list[float] = []
    for run_index, size in enumerate(groups):
        scores.extend(score_fn(run_index, int(size)))
    return np.asarray(scores, dtype=float)


def random_scores(groups: Sequence[int], seed: int) -> np.ndarray:
    rng = Random(seed)
    return _scores_by_group(groups, lambda _run, size: [rng.random() for _ in range(size)])


def last_step_scores(features: pd.DataFrame) -> np.ndarray:
    return features["idx"].to_numpy(dtype=float)


def heuristic_scores(features: pd.DataFrame) -> np.ndarray:
    red_flag = (
        features.get("answer_in_passages", pd.Series(np.nan, index=features.index)).eq(0)
        | features.get("checked_unsupported", pd.Series(0, index=features.index)).eq(1)
        | features.get("top1_score_z", pd.Series(np.nan, index=features.index)).lt(-1)
        | features.get("yesno_mismatch", pd.Series(0, index=features.index)).eq(1)
    )
    return red_flag.astype(float).to_numpy() * 1_000_000 - features["idx"].to_numpy(dtype=float)


def judge_ranking(
    steps: Sequence[Step], llm: LLMClient, cassette: Cassette
) -> list[str]:
    compact = [
        {
            "step_key": step.step_key,
            "name": step.name,
            "input": json.dumps(step.input, ensure_ascii=False)[:300],
            "output": step.output_text[:300],
        }
        for step in steps
    ]
    prompt = (
        "Rank the three most likely failure-causing steps. Return JSON exactly as "
        '{"step_keys":["key1","key2","key3"]}. Trace: '
        + json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    )

    def call() -> tuple[dict[str, Any], dict[str, Any]]:
        response = llm.complete_json(prompt, temperature=0)
        return response.json, {
            "tokens_in": response.tokens_in,
            "tokens_out": response.tokens_out,
            "model": response.model,
        }

    model = getattr(llm, "model", "judge")
    response, _, _ = cassette.get_or_call(
        "llm_judge", str(model), {"prompt": prompt}, 0, 0, call
    )
    raw = response.get("step_keys", [])
    valid = {step.step_key for step in steps}
    return [str(item) for item in raw if str(item) in valid][:3]