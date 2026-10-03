import json
from collections.abc import Callable
from functools import lru_cache
from typing import TypedDict

import numpy as np
from rapidfuzz import fuzz, process

from blackbox.config import Settings, get_settings
from blackbox.corpus.embed import embed_texts
from blackbox.corpus.paths import workspace_data_dir


class SearchResult(TypedDict):
    pid: str
    title: str
    text: str
    score: float


class Retriever:
    def __init__(
        self,
        settings: Settings | None = None,
        passages: list[dict[str, str]] | None = None,
        embeddings: np.ndarray | None = None,
        embedder: Callable[[list[str]], np.ndarray] = embed_texts,
        workspace: str = "hotpot",
    ) -> None:
        self._settings = settings or get_settings()
        self._passages = passages
        self._embeddings = embeddings
        self._embedder = embedder
        self._workspace = workspace
        self._by_pid: dict[str, dict[str, str]] | None = None

    def _load(self) -> None:
        if self._passages is None:
            data_dir = workspace_data_dir(self._settings, self._workspace)
            with (data_dir / "passages.jsonl").open(encoding="utf-8") as file:
                self._passages = [json.loads(line) for line in file if line.strip()]
            self._embeddings = np.load(data_dir / "embeddings.npy")
            pid_index = json.loads((data_dir / "pid_index.json").read_text())
            passages_by_pid = {passage["pid"]: passage for passage in self._passages}
            self._passages = [passages_by_pid[pid] for pid in pid_index]
        if self._embeddings is None:
            raise ValueError("Embeddings are required for retrieval")
        if len(self._passages) != len(self._embeddings):
            raise ValueError("Passage and embedding counts do not match")
        self._by_pid = {passage["pid"]: passage for passage in self._passages}

    def _ensure_loaded(self) -> None:
        if self._by_pid is None:
            self._load()

    @classmethod
    def for_workspace(
        cls, workspace: str, settings: Settings | None = None
    ) -> "Retriever":
        return cls(settings=settings, workspace=workspace)

    def search(
        self, query: str, k: int = 3, exclude_archived: bool = False
    ) -> list[SearchResult]:
        self._ensure_loaded()
        assert self._passages is not None
        assert self._embeddings is not None
        query_embedding = np.asarray(self._embedder([query])[0], dtype=np.float32)
        query_norm = np.linalg.norm(query_embedding)
        if query_norm:
            query_embedding = query_embedding / query_norm
        scores = self._embeddings @ query_embedding
        ranked_indices = np.argsort(scores)[::-1]
        if exclude_archived:
            ranked_indices = np.asarray(
                [
                    index
                    for index in ranked_indices
                    if self._passages[index].get("status") != "archived"
                ]
            )
        top_indices = ranked_indices[: max(0, min(k, len(ranked_indices)))]
        return [
            SearchResult(**self._passages[index], score=float(scores[index]))
            for index in top_indices
        ]

    def get_passage(self, pid: str) -> dict[str, str] | None:
        self._ensure_loaded()
        assert self._by_pid is not None
        return self._by_pid.get(pid)

    def search_titles(self, entity: str, k: int = 3) -> list[SearchResult]:
        self._ensure_loaded()
        assert self._passages is not None
        matches = process.extract(
            entity,
            {index: passage["title"] for index, passage in enumerate(self._passages)},
            scorer=fuzz.WRatio,
            limit=max(0, k),
        )
        return [
            SearchResult(**self._passages[index], score=float(score) / 100.0)
            for _, score, index in matches
        ]


@lru_cache(maxsize=4)
def get_retriever(workspace: str = "hotpot") -> Retriever:
    return Retriever.for_workspace(workspace)
