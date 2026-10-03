from __future__ import annotations

import json
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np

from blackbox.config import Settings, get_settings
from blackbox.corpus.paths import workspace_data_dir

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> np.ndarray:
    embeddings = _get_model().encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return np.asarray(embeddings, dtype=np.float32)


def build_embeddings(
    settings: Settings | None = None, workspace: str = "hotpot"
) -> np.ndarray:
    settings = settings or get_settings()
    data_dir = workspace_data_dir(settings, workspace)
    with (data_dir / "passages.jsonl").open(encoding="utf-8") as file:
        passages = [json.loads(line) for line in file if line.strip()]

    embeddings = embed_texts(
        [f"{passage['title']}. {passage['text']}" for passage in passages]
    )
    np.save(data_dir / "embeddings.npy", embeddings)
    (data_dir / "pid_index.json").write_text(
        json.dumps([passage["pid"] for passage in passages]), encoding="utf-8"
    )
    return embeddings
