"""Exercise real loopback HTTP, negative cases, concurrency and local latency."""
from __future__ import annotations

import json
import math
import platform
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from service import create_server


def request(base: str, path: str = "/predict", payload: object = None, raw: bytes | None = None, content_type: str = "application/json") -> tuple[int, dict]:
    body = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
    req = urllib.request.Request(base + path, data=body, headers={"Content-Type": content_type})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def percentile(values: list[float], quantile: float) -> float:
    return sorted(values)[max(0, math.ceil(quantile * len(values)) - 1)]


def main() -> None:
    server = create_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    checks = []
    def check(name: str, expected_status: int, **kwargs: object) -> dict:
        status, body = request(base, **kwargs)
        assert status == expected_status, (name, status, body)
        checks.append({"name": name, "status": status, "passed": True})
        return body
    try:
        health = check("health", 200, path="/health")
        batch = check("batch_preserves_order", 200, payload={"texts": ["reset my password", "refund the payment", "application crashes"]})
        assert [p["label"] for p in batch["predictions"]] == ["access", "billing", "technical"]
        check("invalid_json", 400, raw=b"{")
        check("empty_batch", 422, payload={"texts": []})
        check("non_string", 422, payload={"texts": [12]})
        check("blank_text", 422, payload={"texts": ["   "]})
        check("unknown_field", 422, payload={"texts": ["password"], "admin": True})
        check("too_many_items", 422, payload={"texts": ["password"] * 17})
        check("text_too_long", 422, payload={"texts": ["p" * 1001]})
        check("unknown_vocabulary", 422, payload={"texts": ["zzqxxvv"]})
        check("unsupported_content_type", 415, raw=b"{}", content_type="text/plain")
        check("oversized_body", 413, raw=b"x" * 17000)
        check("unknown_route", 404, path="/unknown")
        concurrent_payload = {"texts": ["reset my password"]}
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: request(base, payload=concurrent_payload), range(20)))
        assert all(status == 200 and body["predictions"][0]["label"] == "access" for status, body in results)
        checks.append({"name": "20_requests_4_client_threads", "status": 200, "passed": True})
        for _ in range(5):
            request(base, payload=concurrent_payload)
        durations = []
        start_all = time.perf_counter()
        for _ in range(40):
            start = time.perf_counter()
            status, _ = request(base, payload=concurrent_payload)
            assert status == 200
            durations.append((time.perf_counter() - start) * 1000)
        elapsed = time.perf_counter() - start_all
        report = {
            "example_version": "2026-11-13", "run_at_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
            "system": platform.system(), "machine": platform.machine(),
            "model_id": health["model_id"], "checks": checks,
            "sample_response": batch,
            "benchmark": {"scope": "one local process; loopback; sequential HTTP incl client; synthetic 3-token input; not production load", "warmup": 5, "n": 40, "p50_ms": round(percentile(durations, 0.5), 3), "p95_ms": round(percentile(durations, 0.95), 3), "sequential_requests_per_second": round(40 / elapsed, 2), "raw_ms": [round(x, 4) for x in durations]},
            "limitations": ["http.server teaching server only", "No TLS/auth/rate limiting", "Request read timeout is not model cancellation", "No load/capacity or Internet latency claim", "Thread count is not bounded; bind is localhost only"],
        }
        output = Path(__file__).resolve().parent / "reports"
        output.mkdir(exist_ok=True)
        (output / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"project": "02_model_service", "passed_checks": len(checks), "benchmark": {k: report["benchmark"][k] for k in ("n", "p50_ms", "p95_ms")}}, ensure_ascii=False))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == "__main__":
    main()
