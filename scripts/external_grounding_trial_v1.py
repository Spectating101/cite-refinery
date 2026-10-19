"""Reproducible *live* source-grounding trial using local Ollama and WMO pages.

This is a small falsifiable case, NOT a scientific measure of all search engines.
It tests whether supplied official source text corrects a closed-book mistake
and keeps unsupported causal outcomes explicitly unresolved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

SOURCES = [
    {
        "id": "WMO-HYDROSOS",
        "url": "https://wmo.int/activities/hydrosos",
        "match": "HydroSOS is the backbone supporting",
    },
    {
        "id": "WMO-EW4ALL",
        "url": "https://wmo.int/activities/early-warnings-all",
        "match": "Early Warnings for All is a groundbreaking initiative",
    },
]
QUESTIONS = [
    {
        "id": "explicit-link",
        "question": "Does WMO explicitly describe HydroSOS as supporting the Early Warnings for All initiative for hydrological disasters? Answer yes or no, followed by a brief reason.",
        "expected": "yes",
        "meaning": "Verifiable institutional relationship, not a causal outcome claim.",
    },
    {
        "id": "outcome-overreach",
        "question": "Do these pages establish by a local impact evaluation that deploying HydroSOS itself measurably reduced deaths? Answer yes or no, followed by a brief reason.",
        "expected": "no",
        "meaning": "No source-specific intervention outcome evaluation is present in these excerpts.",
    },
]


def build_corpus(*, session=None):
    import requests
    from bs4 import BeautifulSoup
    session = session or requests.Session()
    records = []
    for source in SOURCES:
        response = session.get(source["url"], timeout=15,
                               headers={"User-Agent": "Cite-Refinery external trial/1.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = [" ".join(p.get_text(" ", strip=True).split())
                      for p in soup.find_all("p")]
        matching = next((p for p in paragraphs if source["match"].lower() in p.lower()), None)
        if not matching or len(matching) < 80:
            raise RuntimeError(f"Expected source passage not found: {source['id']}")
        records.append({
            "id": source["id"], "url": source["url"],
            "text": matching[:1100],
            "page_sha256": hashlib.sha256(response.content).hexdigest(),
            "passage_sha256": hashlib.sha256(matching.encode("utf-8")).hexdigest(),
            "method": "paragraph selector matched directly in 200-response official WMO HTML",
        })
    return records


def classify_yes_no(text):
    text = str(text or "").strip().lower()
    a = re.search(r"\b(yes|no)\b", text[:100])
    return a.group(1) if a else "unparseable"


def ollama_generate(prompt, *, session=None, model="llama3.2:3b"):
    import requests
    session = session or requests.Session()
    started = time.monotonic()
    response = session.post("http://127.0.0.1:11434/api/generate",
                            json={"model": model, "prompt": prompt,
                                  "stream": False, "keep_alive": "2m",
                                  "options": {"num_ctx": 4096, "temperature": 0,
                                              "num_predict": 140}},
                            timeout=150)
    response.raise_for_status()
    body = response.json()
    return {"answer": body.get("response", "").strip(),
            "elapsed_s": round(time.monotonic() - started, 2),
            "model": model, "provider": "Ollama loopback"}


def run_grounding(output: Path, *, model: str = "llama3.2:3b"):
    sources = build_corpus()
    corpus = "\n\n".join(f"Source [{s['id']}]: {s['url']}\n{s['text']}" for s in sources)
    records = []
    for q in QUESTIONS:
        closed = ollama_generate("Answer from general knowledge only. " + q["question"],
                                 model=model)
        grounded = ollama_generate(
            "Use ONLY the following quoted passages from official WMO pages. "
            "If no local outcome evaluation is present, do not invent one. "
            "Cite page source IDs where possible.\n\n" + corpus + "\n\n" + q["question"],
            model=model,
        )
        records.append({
            "id": q["id"], "question": q["question"],
            "expected": q["expected"], "boundary": q["meaning"],
            "closed_book": {**closed, "decision": classify_yes_no(closed["answer"])},
            "grounded": {**grounded, "decision": classify_yes_no(grounded["answer"])},
        })
    report = {
        "experiment": "wmo-source-grounding-mini-v1",
        "status": "single-case-live-comparison_not_benchmark",
        "sources": [{k: v for k, v in s.items() if k != "text"} for s in sources],
        "source_passages": [{k: s[k] for k in ("id", "text")} for s in sources],
        "questions": records,
        "score": {
            name: sum(row[name]["decision"] == row["expected"] for row in records)
            for name in ("closed_book", "grounded")
        },
        "limitations": [
            "Two source pages and two questions, not a representative corpus.",
            "Human-defined expected classifications rely on the directly quoted WMO passage; no population impact is established.",
            "A model agreeing with the expected answer is NOT proof all its claims or citations are correct.",
            "No model-driven relationship is promoted to an accepted semantic edge.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("GROUNDING_SCORE", report["score"])
    for row in records:
        print(row["id"], "EXPECTED", row["expected"],
              "CLOSED", row["closed_book"]["decision"],
              "GROUNDED", row["grounded"]["decision"])
    print("OUTPUT", output)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="/tmp/cite-refinery-wmo-grounding-result.json")
    parser.add_argument("--model", default="llama3.2:3b")
    args = parser.parse_args()
    run_grounding(Path(args.out), model=args.model)


if __name__ == "__main__":
    main()
