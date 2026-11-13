"""Run fixed train/dev/test experiment; no network and no paid API."""
from __future__ import annotations

import hashlib
import json
import platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from nb_classifier import load_data, metrics, predict, train

ROOT = Path(__file__).resolve().parent


def main() -> None:
    data_path = ROOT / "data/tickets.jsonl"
    rows = load_data(data_path)
    splits = {s: [r for r in rows if r["split"] == s] for s in ("train", "dev", "test")}
    validation_runs = []
    candidates = []
    for bigrams in (False, True):
        for alpha in (0.25, 1.0, 2.0):
            model = train(splits["train"], alpha=alpha, bigrams=bigrams)
            score = metrics([r["label"] for r in splits["dev"]], [predict(model, r["text"])["label"] for r in splits["dev"]])
            validation_runs.append({"alpha": alpha, "bigrams": bigrams, "dev": score})
            candidates.append((model, score["macro_f1"]))
    # Stable tie breaker: first candidate, favouring the simpler unigram model.
    best_model = max(candidates, key=lambda pair: pair[1])[0]
    test = splits["test"]
    predictions = [{**r, **predict(best_model, r["text"]), "gold": r["label"]} for r in test]
    # predict() replaces label in the merged dict; gold preserves the annotation.
    test_metrics = metrics([r["gold"] for r in predictions], [r["label"] for r in predictions])
    majority = Counter(r["label"] for r in splits["train"]).most_common(1)[0][0]
    majority_metrics = metrics([r["label"] for r in test], [majority] * len(test))
    # Ablation: delete all content. This intentionally collapses to class priors.
    prior_metrics = metrics([r["label"] for r in test], [predict(best_model, "")["label"] for _ in test])
    failures = [r for r in predictions if r["gold"] != r["label"]]
    report = {
        "example_version": "2026-11-13", "run_at_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
        "data_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "data_provenance": "hand-authored synthetic teaching data; no user/customer records",
        "split_sizes": {s: len(v) for s, v in splits.items()},
        "selection_policy": "dev macro F1; fixed alpha grid; ties choose first; test never used for selection",
        "selected": {k: best_model[k] for k in ("alpha", "bigrams")},
        "validation_runs": validation_runs,
        "test": test_metrics, "majority_baseline": majority_metrics,
        "ablation_remove_all_features": prior_metrics,
        "predictions": predictions, "failures": failures,
        "limitations": ["Tiny synthetic dataset", "No real-world generalization claim", "No confidence calibration", "Normalized duplicate guard does not detect semantic or author leakage"],
    }
    output = ROOT / "reports"
    output.mkdir(exist_ok=True)
    (output / "model.json").write_text(json.dumps(best_model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "evaluation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert test_metrics["macro_f1"] > majority_metrics["macro_f1"], "baseline did not improve"
    assert failures, "teaching case must retain an observable failure"
    print(json.dumps({"project": "01_ml_experiment", "selected": report["selected"], "test": {k: test_metrics[k] for k in ("n", "accuracy", "macro_f1")}, "majority_macro_f1": majority_metrics["macro_f1"], "failures": len(failures)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
