import json
import random
from pathlib import Path

from blackbox.config import Settings, get_settings
from blackbox.corpus.paths import workspace_data_dir
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Task
from blackbox.store.repo import upsert_task

SEED_DIR = Path(__file__).parents[1] / "workspaces" / "nimbu"


def build_nimbu_corpus(
    settings: Settings | None = None,
) -> tuple[list[Task], list[dict[str, object]]]:
    settings = settings or get_settings()
    articles = json.loads((SEED_DIR / "articles.json").read_text())
    questions = json.loads((SEED_DIR / "questions.json").read_text())
    by_aid = {article["aid"]: article for article in articles}
    passages: list[dict[str, object]] = [
        {
            "pid": f"p_{article['aid']}",
            "title": article["title"],
            "text": article["text"],
            "status": article["status"],
            "updated": article["updated"],
            "category": article["category"],
        }
        for article in articles
    ]

    question_ids = [str(question["qid"]) for question in questions]
    random.Random(settings.SEED).shuffle(question_ids)
    train_ids = set(question_ids[: round(len(question_ids) * 0.7)])
    tasks = [
        Task(
            task_id=question["qid"],
            workspace="nimbu",
            category=question["category"],
            question=question["question"],
            gold_answer=question["answer"],
            qtype=question["qtype"],
            level="medium",
            split="train" if question["qid"] in train_ids else "test",
            gold_titles=[by_aid[aid]["title"] for aid in question["gold_aids"]],
            distractor_pids=[
                f"p_{aid}" for aid in question["distractor_aids"]
            ],
        )
        for question in questions
    ]

    init_db()
    with get_session() as session:
        for task in tasks:
            upsert_task(session, task)

    data_dir = workspace_data_dir(settings, "nimbu")
    data_dir.mkdir(parents=True, exist_ok=True)
    with (data_dir / "passages.jsonl").open("w", encoding="utf-8") as file:
        for passage in passages:
            file.write(json.dumps(passage, ensure_ascii=False) + "\n")
    return tasks, passages