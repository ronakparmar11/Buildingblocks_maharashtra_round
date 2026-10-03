import json
import re
from collections import Counter
from pathlib import Path

SEED_DIR = Path(__file__).parents[1] / "blackbox" / "workspaces" / "nimbu"


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold().replace("₹", "inr"))


def test_nimbu_questions_are_grounded_in_current_articles() -> None:
    articles = json.loads((SEED_DIR / "articles.json").read_text())
    questions = json.loads((SEED_DIR / "questions.json").read_text())
    by_aid = {article["aid"]: article for article in articles}

    assert len(articles) == 40
    assert len(questions) == 40
    assert Counter(question["qtype"] for question in questions) == {
        "lookup": 15,
        "bridge": 15,
        "comparison": 10,
    }
    for question in questions:
        referenced = question["gold_aids"] + question["distractor_aids"]
        assert all(aid in by_aid for aid in referenced)
        current_gold = [
            by_aid[aid]
            for aid in question["gold_aids"]
            if by_aid[aid]["status"] == "current"
        ]
        assert current_gold
        normalized_answer = _normalize(question["answer"])
        assert any(
            normalized_answer in _normalize(article["text"])
            for article in current_gold
        )


def test_current_nimbu_articles_keep_key_policy_facts_consistent() -> None:
    articles = json.loads((SEED_DIR / "articles.json").read_text())
    current_text = " ".join(
        article["text"] for article in articles if article["status"] == "current"
    )

    required_facts = ["7 days", "₹999", "₹10,000", "5–7 business days"]
    assert all(fact in current_text for fact in required_facts)
    retired_facts = ["30 days", "above ₹499", "up to ₹5,000", "only by cheque"]
    assert all(fact not in current_text for fact in retired_facts)