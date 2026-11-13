"""Select refusal threshold on dev, then evaluate the fixed teaching test set."""
from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

from retrieval import SearchIndex, evaluate, load_jsonl

ROOT = Path(__file__).resolve().parent


def main() -> None:
    corpus = load_jsonl(ROOT / "data/corpus.jsonl")
    questions = load_jsonl(ROOT / "data/questions.jsonl")
    normalized = [r["question"].strip().casefold() for r in questions]
    assert len(normalized) == len(set(normalized)), "duplicate question across splits"
    dev = [r for r in questions if r["split"] == "dev"]
    test = [r for r in questions if r["split"] == "test"]
    index = SearchIndex(corpus)
    trials = []
    for threshold in (1.0, 2.0, 3.0, 4.0):
        evaluation = evaluate(index, dev, threshold)
        trials.append({"threshold": threshold, "dev_task_accuracy": evaluation["task_accuracy"], "dev_unanswerable_refusal_rate": evaluation["unanswerable_refusal_rate"]})
    # Prespecified tie breaker prefers higher unanswerable refusal, then lower threshold.
    selected = max(trials, key=lambda row: (row["dev_task_accuracy"], row["dev_unanswerable_refusal_rate"], -row["threshold"]))["threshold"]
    evaluation = evaluate(index, test, selected)
    report = {"example_version": "2026-11-13", "run_at_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
              "method": "BM25 retrieval; full-passage extraction; literal pattern blocking; not an LLM",
              "data_sha256": {name: hashlib.sha256((ROOT / "data" / name).read_bytes()).hexdigest() for name in ("corpus.jsonl", "questions.jsonl")},
              "corpus_size": len(corpus), "dev_size": len(dev), "selection_trials": trials, "selected_threshold": selected,
              "test": evaluation,
              "limitations": ["Synthetic English corpus only", "Exact quotations do not prove answer relevance", "Lexical refusal is not semantic uncertainty or a security boundary", "No real LLM generation, embeddings or production RAG claim"]}
    output = ROOT / "reports"
    output.mkdir(exist_ok=True)
    (output / "evaluation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "failures.json").write_text(json.dumps(evaluation["failures"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert evaluation["answered_quote_integrity"] == 1.0
    assert evaluation["failures"], "retain a teaching failure"
    print(json.dumps({"project": "03_grounded_retrieval", "selected_threshold": selected, "test": {k: v for k, v in evaluation.items() if k not in {"records", "failures"}}, "failures": len(evaluation["failures"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
