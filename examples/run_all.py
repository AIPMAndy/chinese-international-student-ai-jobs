"""Run every example, concrete risk tests, and deterministic acceptance checks."""
from __future__ import annotations

import json
import platform
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    for command in ([sys.executable, str(ROOT / "01_ml_experiment/run.py")],
                    [sys.executable, str(ROOT / "02_model_service/verify.py")],
                    [sys.executable, str(ROOT / "03_grounded_retrieval/run.py")],
                    [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"]):
        subprocess.run(command, check=True)
    expected = json.loads((ROOT / "expected_metrics.json").read_text())
    ml = json.loads((ROOT / "01_ml_experiment/reports/evaluation.json").read_text())
    serving = json.loads((ROOT / "02_model_service/reports/verification.json").read_text())
    retrieval = json.loads((ROOT / "03_grounded_retrieval/reports/evaluation.json").read_text())
    assert ml["split_sizes"] == expected["01_ml_experiment"]["split_sizes"]
    assert ml["test"]["accuracy"] == expected["01_ml_experiment"]["test_accuracy"]
    assert ml["test"]["macro_f1"] == expected["01_ml_experiment"]["test_macro_f1"]
    assert len(ml["failures"]) == expected["01_ml_experiment"]["failure_count"]
    assert len(serving["checks"]) == expected["02_model_service"]["passed_checks"]
    assert all(check["passed"] for check in serving["checks"])
    assert serving["benchmark"]["n"] == expected["02_model_service"]["benchmark_samples"]
    assert retrieval["selected_threshold"] == expected["03_grounded_retrieval"]["selected_threshold"]
    assert retrieval["test"]["n"] == expected["03_grounded_retrieval"]["test_n"]
    for metric in ("task_accuracy", "retrieval_recall_at_3", "answerable_coverage", "answerable_correct_rate", "unanswerable_refusal_rate", "injection_refusal_rate", "answered_quote_integrity"):
        assert retrieval["test"][metric] == expected["03_grounded_retrieval"][metric], metric
    assert len(retrieval["test"]["failures"]) == expected["03_grounded_retrieval"]["failure_count"]
    test_count = unittest.TestLoader().discover(str(ROOT / "tests")).countTestCases()
    summary = {"example_version": "2026-11-13", "run_at_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(), "unit_tests": test_count,
               "real_http_checks": len(serving["checks"]), "deterministic_acceptance": "passed",
               "commands": ["python3 examples/01_ml_experiment/run.py", "python3 examples/02_model_service/verify.py", "python3 examples/03_grounded_retrieval/run.py", "python3 -m unittest discover -s examples/tests -v"],
               "scope": "Local standard-library teaching examples; no external model or live production system tested"}
    (ROOT / "verification-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ALL_EXAMPLES_ACCEPTED")


if __name__ == "__main__":
    main()
