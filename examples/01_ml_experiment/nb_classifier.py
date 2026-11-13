"""Small, transparent multinomial NB baseline; original MIT teaching code."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

LABELS = ("access", "billing", "technical")


def tokens(text: str, bigrams: bool = False) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return words + [f"{a}__{b}" for a, b in zip(words, words[1:])] if bigrams else words


def canonical_text(text: str) -> str:
    return " ".join(tokens(text))


def load_data(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = set()
    seen_text = {}
    for row in rows:
        if row["id"] in ids:
            raise ValueError(f"duplicate id: {row['id']}")
        ids.add(row["id"])
        if row["label"] not in LABELS or row["split"] not in {"train", "dev", "test"}:
            raise ValueError(f"invalid label/split: {row['id']}")
        normalized = canonical_text(row["text"])
        if not normalized:
            raise ValueError(f"empty normalized text: {row['id']}")
        if normalized in seen_text:
            raise ValueError(f"duplicate normalized text / leakage risk: {row['id']} and {seen_text[normalized]}")
        seen_text[normalized] = row["id"]
    for split in ("train", "dev", "test"):
        if set(r["label"] for r in rows if r["split"] == split) != set(LABELS):
            raise ValueError(f"missing class in {split}")
    return rows


def train(rows: list[dict], alpha: float = 1.0, bigrams: bool = False) -> dict:
    if not rows or alpha <= 0:
        raise ValueError("training data must be nonempty and alpha must be positive")
    if any(r["split"] != "train" for r in rows):
        raise ValueError("train() accepts the training split only")
    counts = {label: Counter() for label in LABELS}
    documents = Counter()
    for row in rows:
        documents[row["label"]] += 1
        counts[row["label"]].update(tokens(row["text"], bigrams))
    if set(documents) != set(LABELS):
        raise ValueError("all fixed labels must occur in training data")
    vocabulary = sorted(set().union(*(set(c) for c in counts.values())))
    return {
        "schema_version": 1, "model_type": "multinomial_naive_bayes",
        "alpha": alpha, "bigrams": bigrams, "labels": list(LABELS),
        "vocabulary": vocabulary, "document_counts": dict(documents),
        "token_counts": {k: dict(v) for k, v in counts.items()},
        "token_totals": {k: sum(v.values()) for k, v in counts.items()},
        "training_ids": [r["id"] for r in rows],
    }


def predict(model: dict, text: str) -> dict:
    vocabulary = set(model["vocabulary"])
    observed = Counter(t for t in tokens(text, model["bigrams"]) if t in vocabulary)
    alpha = model["alpha"]
    n_docs = sum(model["document_counts"].values())
    scores = {}
    for label in model["labels"]:
        score = math.log(model["document_counts"][label] / n_docs)
        denominator = model["token_totals"][label] + alpha * len(vocabulary)
        for token, frequency in observed.items():
            score += frequency * math.log((model["token_counts"][label].get(token, 0) + alpha) / denominator)
        scores[label] = score
    max_score = max(scores.values())
    relative = {k: math.exp(v - max_score) for k, v in scores.items()}
    total = sum(relative.values())
    probabilities = {k: round(v / total, 6) for k, v in relative.items()}
    label = max(model["labels"], key=lambda value: scores[value])
    return {"label": label, "uncalibrated_probabilities": probabilities, "known_token_count": sum(observed.values())}


def metrics(gold: list[str], predicted: list[str]) -> dict:
    if not gold or len(gold) != len(predicted):
        raise ValueError("metric lists must be nonempty and equally long")
    if any(label not in LABELS for label in gold + predicted):
        raise ValueError("unknown metric label")
    per_class = {}
    for label in LABELS:
        tp = sum(a == label and b == label for a, b in zip(gold, predicted))
        fp = sum(a != label and b == label for a, b in zip(gold, predicted))
        fn = sum(a == label and b != label for a, b in zip(gold, predicted))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"support": sum(x == label for x in gold), "precision": round(precision, 6), "recall": round(recall, 6), "f1": round(f1, 6)}
    confusion = {a: {b: sum(x == a and y == b for x, y in zip(gold, predicted)) for b in LABELS} for a in LABELS}
    return {"n": len(gold), "accuracy": round(sum(a == b for a, b in zip(gold, predicted)) / len(gold), 6),
            "macro_f1": round(sum(v["f1"] for v in per_class.values()) / len(LABELS), 6),
            "per_class": per_class, "confusion_gold_rows_predicted_columns": confusion}
