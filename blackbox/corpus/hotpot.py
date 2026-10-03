import hashlib
import json
import random
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from datasets import load_dataset

from blackbox.config import Settings, get_settings
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Task
from blackbox.store.repo import upsert_task


def passage_id(title: str) -> str:
    digest = hashlib.sha1(title.encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"p_{digest[:10]}"


def _sample_by_type(
    examples: Iterable[Mapping[str, Any]], n_tasks: int, seed: int
) -> list[Mapping[str, Any]]:
    by_type: dict[str, list[Mapping[str, Any]]] = {
        "bridge": [],
        "comparison": [],
    }
    for example in examples:
        qtype = str(example["type"])
        if qtype in by_type:
            by_type[qtype].append(example)

    counts = {"bridge": n_tasks // 2, "comparison": n_tasks - n_tasks // 2}
    randomizer = random.Random(seed)
    sampled: list[Mapping[str, Any]] = []
    for qtype, count in counts.items():
        if len(by_type[qtype]) < count:
            raise ValueError(f"Not enough {qtype} examples to sample {count} tasks")
        if count:
            sampled.append(by_type[qtype][0])
            sampled.extend(randomizer.sample(by_type[qtype][1:], count - 1))
    return sampled


def _split_by_task(examples: Sequence[Mapping[str, Any]], seed: int) -> dict[str, str]:
    by_type: dict[str, list[str]] = {"bridge": [], "comparison": []}
    for example in examples:
        by_type[str(example["type"])].append(str(example["id"]))

    randomizer = random.Random(seed)
    splits: dict[str, str] = {}
    for task_ids in by_type.values():
        randomizer.shuffle(task_ids)
        train_count = round(len(task_ids) * 0.7)
        for index, task_id in enumerate(task_ids):
            splits[task_id] = "train" if index < train_count else "test"
    return splits


def _passages_for_example(example: Mapping[str, Any]) -> list[dict[str, str]]:
    context = example["context"]
    titles = context["title"]
    sentence_groups = context["sentences"]
    return [
        {
            "pid": passage_id(str(title)),
            "title": str(title),
            "text": "".join(str(sentence) for sentence in sentences).strip(),
        }
        for title, sentences in zip(titles, sentence_groups, strict=True)
    ]


def build_hotpot_corpus(
    settings: Settings | None = None,
    examples: Iterable[Mapping[str, Any]] | None = None,
) -> tuple[list[Task], list[dict[str, str]]]:
    settings = settings or get_settings()
    if examples is None:
        examples = load_dataset("hotpotqa/hotpot_qa", "distractor", split="validation")

    sampled = _sample_by_type(examples, settings.N_TASKS, settings.SEED)
    splits = _split_by_task(sampled, settings.SEED)
    passages_by_title: dict[str, dict[str, str]] = {}
    tasks: list[Task] = []

    for example in sampled:
        passages = _passages_for_example(example)
        for passage in passages:
            passages_by_title.setdefault(passage["title"], passage)

        gold_titles = list(dict.fromkeys(example["supporting_facts"]["title"]))
        gold_title_set = set(gold_titles)
        tasks.append(
            Task(
                task_id=str(example["id"]),
                question=str(example["question"]),
                gold_answer=str(example["answer"]),
                qtype=str(example["type"]),
                level=str(example["level"]),
                split=splits[str(example["id"])],
                gold_titles=gold_titles,
                distractor_pids=[
                    passage["pid"]
                    for passage in passages
                    if passage["title"] not in gold_title_set
                ],
            )
        )

    init_db()
    with get_session() as session:
        for task in tasks:
            upsert_task(session, task)

    data_dir = Path(settings.DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    passages = list(passages_by_title.values())
    with (data_dir / "passages.jsonl").open("w", encoding="utf-8") as file:
        for passage in passages:
            file.write(json.dumps(passage, ensure_ascii=False) + "\n")

    return tasks, passages
