import re
import string
from collections import Counter


def normalize_answer(answer: str) -> str:
    lowered = answer.lower()
    without_punctuation = "".join(
        character for character in lowered if character not in string.punctuation
    )
    without_articles = re.sub(r"\b(a|an|the)\b", " ", without_punctuation)
    return " ".join(without_articles.split())


def exact_match(prediction: str, gold: str) -> bool:
    return normalize_answer(prediction) == normalize_answer(gold)


def f1(prediction: str, gold: str) -> float:
    prediction_tokens = normalize_answer(prediction).split()
    gold_tokens = normalize_answer(gold).split()
    if not prediction_tokens or not gold_tokens:
        return float(prediction_tokens == gold_tokens)

    common = Counter(prediction_tokens) & Counter(gold_tokens)
    shared = sum(common.values())
    if shared == 0:
        return 0.0
    precision = shared / len(prediction_tokens)
    recall = shared / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def is_pass(prediction: str, gold: str) -> bool:
    return exact_match(prediction, gold) or f1(prediction, gold) >= 0.6