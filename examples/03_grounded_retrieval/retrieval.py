"""BM25 + extractive evidence + explicit abstention. This is NOT an LLM."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

STOPWORDS = set("a an the is are was were to of for and or on in at by do does how what when where can i we it this that my with from should be about".split())
BLOCK_PATTERNS = [r"ignore\b.*\binstructions", r"reveal\b.*\bsecret", r"system\s+prompt", r"print\b.*\bapi\s+key"]


def tokenize(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in STOPWORDS]


class SearchIndex:
    def __init__(self, documents: list[dict]):
        if not documents or len({d["id"] for d in documents}) != len(documents):
            raise ValueError("corpus must be nonempty with unique document ids")
        self.documents = documents
        self.term_counts = [Counter(tokenize(d["title"] + " " + d["text"])) for d in documents]
        self.lengths = [sum(counts.values()) for counts in self.term_counts]
        self.average_length = sum(self.lengths) / len(self.lengths)
        self.df = Counter(term for counts in self.term_counts for term in counts)

    def search(self, query: str, k: int = 3) -> list[dict]:
        query_terms = set(tokenize(query))
        if not query_terms:
            return []
        results = []
        k1, b = 1.5, 0.75
        for document, term_counts, length in zip(self.documents, self.term_counts, self.lengths):
            score = 0.0
            for term in query_terms:
                frequency = term_counts.get(term, 0)
                if not frequency:
                    continue
                inverse_frequency = math.log(1 + (len(self.documents) - self.df[term] + 0.5) / (self.df[term] + 0.5))
                denominator = frequency + k1 * (1 - b + b * length / self.average_length)
                score += inverse_frequency * frequency * (k1 + 1) / denominator
            if score > 0:
                results.append({"document": document, "score": round(score, 6)})
        return sorted(results, key=lambda row: (-row["score"], row["document"]["id"]))[:k]

    def answer(self, query: str, threshold: float) -> dict:
        if any(re.search(pattern, query, re.IGNORECASE) for pattern in BLOCK_PATTERNS):
            return {"status": "refused", "reason": "blocked_instruction_pattern", "answer": None, "citations": [], "retrieved_ids": []}
        results = self.search(query)
        ids = [r["document"]["id"] for r in results]
        if not results or results[0]["score"] < threshold:
            return {"status": "refused", "reason": "insufficient_lexical_evidence", "answer": None, "citations": [], "retrieved_ids": ids}
        top = results[0]
        document = top["document"]
        return {"status": "answered", "reason": "extractive_baseline", "answer": document["text"],
                "citations": [{"document_id": document["id"], "title": document["title"], "quote": document["text"]}],
                "retrieved_ids": ids, "retrieval_score": top["score"]}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate(index: SearchIndex, rows: list[dict], threshold: float) -> dict:
    if not rows:
        raise ValueError("evaluation data must be nonempty")
    records = []
    for row in rows:
        # Retrieval recall is measured before the answer/refusal layer.
        retrieved = index.search(row["question"], k=3)
        result = index.answer(row["question"], threshold)
        if row["kind"] == "answerable":
            correct = result["status"] == "answered" and bool(result["citations"]) and result["citations"][0]["document_id"] == row["expected_document"] and row["expected_phrase"].lower() in result["answer"].lower()
        else:
            correct = result["status"] == "refused"
        records.append({**row, "result": result, "correct": correct,
                        "gold_in_top3": row.get("expected_document") in [r["document"]["id"] for r in retrieved] if row["kind"] == "answerable" else None})
    answerable = [r for r in records if r["kind"] == "answerable"]
    unanswerable = [r for r in records if r["kind"] == "unanswerable"]
    injection = [r for r in records if r["kind"] == "injection"]
    answered = [r for r in records if r["result"]["status"] == "answered"]
    def ratio(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 6) if denominator else None
    document_lookup = {d["id"]: d for d in index.documents}
    supported_quotes = sum(all(c["document_id"] in document_lookup and c["quote"] in document_lookup[c["document_id"]]["text"] for c in r["result"]["citations"]) and bool(r["result"]["citations"]) for r in answered)
    return {"n": len(records), "answerable_n": len(answerable), "unanswerable_n": len(unanswerable), "injection_n": len(injection),
            "task_accuracy": ratio(sum(r["correct"] for r in records), len(records)),
            "retrieval_recall_at_3": ratio(sum(r["gold_in_top3"] for r in answerable), len(answerable)),
            "answerable_coverage": ratio(sum(r["result"]["status"] == "answered" for r in answerable), len(answerable)),
            "answerable_correct_rate": ratio(sum(r["correct"] for r in answerable), len(answerable)),
            "unanswerable_refusal_rate": ratio(sum(r["correct"] for r in unanswerable), len(unanswerable)),
            "injection_refusal_rate": ratio(sum(r["correct"] for r in injection), len(injection)),
            "answered_quote_integrity": ratio(supported_quotes, len(answered)),
            "records": records, "failures": [r for r in records if not r["correct"]]}
