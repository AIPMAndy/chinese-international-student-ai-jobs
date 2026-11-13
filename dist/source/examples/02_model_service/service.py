"""Local-only model API. Deliberately not a production server."""
from __future__ import annotations

import argparse
import hashlib
import json
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1] / "01_ml_experiment"
sys.path.insert(0, str(ML_ROOT))
from nb_classifier import predict  # noqa: E402

MAX_BODY_BYTES = 16384
MAX_BATCH_SIZE = 16
MAX_TEXT_CHARS = 1000


class InputError(ValueError):
    pass


def validate_payload(payload: object) -> list[str]:
    if not isinstance(payload, dict) or set(payload) != {"texts"}:
        raise InputError("JSON must contain exactly one field: texts")
    texts = payload["texts"]
    if not isinstance(texts, list) or not 1 <= len(texts) <= MAX_BATCH_SIZE:
        raise InputError("texts must be a list containing 1 to 16 strings")
    if any(not isinstance(x, str) or not x.strip() or len(x) > MAX_TEXT_CHARS for x in texts):
        raise InputError("each text must be a nonblank string of at most 1000 characters")
    return texts


def create_server(port: int = 8008, model_path: Path | None = None) -> ThreadingHTTPServer:
    path = model_path or ML_ROOT / "reports/model.json"
    if not path.exists():
        raise FileNotFoundError("model missing: run python3 examples/01_ml_experiment/run.py first")
    model_bytes = path.read_bytes()
    model = json.loads(model_bytes)
    model_id = hashlib.sha256(model_bytes).hexdigest()[:12]

    class Handler(BaseHTTPRequestHandler):
        server_version = "TeachingModelService/1.0"

        def log_message(self, format: str, *args: object) -> None:
            # No request text, credentials, or IP address is stored.
            return

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(3.0)

        def respond(self, status: int, payload: dict) -> None:
            content = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self) -> None:
            if self.path == "/health":
                self.respond(200, {"status": "ok", "model_id": model_id, "model_type": model["model_type"]})
            else:
                self.respond(404, {"error": "route_not_found"})

        def do_POST(self) -> None:
            if self.path != "/predict":
                self.respond(404, {"error": "route_not_found"})
                return
            if self.headers.get_content_type() != "application/json":
                self.respond(415, {"error": "content_type_must_be_application_json"})
                return
            length_value = self.headers.get("Content-Length")
            if length_value is None:
                self.respond(411, {"error": "content_length_required"})
                return
            try:
                length = int(length_value)
            except ValueError:
                self.respond(400, {"error": "invalid_content_length"})
                return
            if not 0 < length <= MAX_BODY_BYTES:
                self.respond(413, {"error": "body_size_must_be_between_1_and_16384_bytes"})
                return
            try:
                body = self.rfile.read(length)
                if len(body) != length:
                    self.respond(400, {"error": "incomplete_body"})
                    return
                payload = json.loads(body.decode("utf-8"))
            except socket.timeout:
                self.respond(408, {"error": "body_read_timeout"})
                return
            except (UnicodeDecodeError, json.JSONDecodeError):
                self.respond(400, {"error": "invalid_json"})
                return
            try:
                texts = validate_payload(payload)
                predictions = [predict(model, text) for text in texts]
                if any(p["known_token_count"] == 0 for p in predictions):
                    raise InputError("a text contains no known tokens; the teaching model supports English training vocabulary only")
            except InputError as error:
                self.respond(422, {"error": "invalid_input", "detail": str(error)})
                return
            self.respond(200, {"model_id": model_id, "count": len(predictions), "predictions": predictions})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8008)
    args = parser.parse_args()
    server = create_server(args.port)
    print(f"Local teaching server: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
