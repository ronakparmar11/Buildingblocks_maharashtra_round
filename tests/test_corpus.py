import numpy as np

from blackbox.corpus.hotpot import _sample_by_type
from blackbox.corpus.retriever import Retriever

PASSAGES = [
    {"pid": "p_scott", "title": "Scott Derrickson", "text": "American director."},
    {"pid": "p_ed", "title": "Ed Wood", "text": "American filmmaker."},
    {"pid": "p_paris", "title": "Paris", "text": "Capital of France."},
    {"pid": "p_mars", "title": "Mars", "text": "The fourth planet."},
    {"pid": "p_ocean", "title": "Pacific Ocean", "text": "Largest ocean."},
]

EMBEDDINGS = np.asarray(
    [
        [1.0, 0.0, 0.0],
        [0.8, 0.2, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, 0.5, 0.5],
    ],
    dtype=np.float32,
)


def _stub_embedder(texts: list[str]) -> np.ndarray:
    assert texts
    return np.asarray([[1.0, 0.0, 0.0] for _ in texts], dtype=np.float32)


def _retriever() -> Retriever:
    return Retriever(passages=PASSAGES, embeddings=EMBEDDINGS, embedder=_stub_embedder)


def test_search_uses_stub_embeddings() -> None:
    results = _retriever().search("Scott Derrickson nationality", k=2)

    assert [result["pid"] for result in results] == ["p_scott", "p_ed"]
    assert results[0]["score"] == 1.0


def test_get_passage_and_title_search() -> None:
    retriever = _retriever()

    assert retriever.get_passage("p_paris") == PASSAGES[2]
    assert retriever.get_passage("missing") is None
    assert retriever.search_titles("Scot Derrickson", k=1)[0]["pid"] == "p_scott"


def test_search_can_exclude_archived_passages() -> None:
    passages = [
        {**PASSAGES[0], "status": "archived"},
        {**PASSAGES[1], "status": "current"},
    ]
    retriever = Retriever(
        passages=passages,
        embeddings=EMBEDDINGS[:2],
        embedder=_stub_embedder,
    )

    assert retriever.search("nationality", k=1)[0]["pid"] == "p_scott"
    assert retriever.search("nationality", k=1, exclude_archived=True)[0][
        "pid"
    ] == "p_ed"


def test_sampling_is_balanced_deterministic_and_keeps_inspected_examples() -> None:
    examples = [
        {"id": f"{qtype}-{index}", "type": qtype}
        for qtype in ("bridge", "comparison")
        for index in range(5)
    ]

    sampled = _sample_by_type(examples, n_tasks=6, seed=42)

    assert sampled == _sample_by_type(examples, n_tasks=6, seed=42)
    assert {example["id"] for example in sampled} >= {"bridge-0", "comparison-0"}
    assert [example["type"] for example in sampled].count("bridge") == 3
    assert [example["type"] for example in sampled].count("comparison") == 3
