#!/usr/bin/env python3
"""Bounded, independent PDF-to-table interoperability benchmark.

Uses separately maintained MIT-licensed PDF Table Traps fixtures and
their keyed-cell oracle. Never claims "success" from preserved raw digits.
No OCR, LLM, downloads, or network requests.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

FIXTURES = ("ruled", "borderless", "prose")
PINNED_FIXTURE_COMMIT = "c63aab8884671aa4c789f08d0891f1a3f0ee5f5d"
ENGINES = (
    "pdfplumber_default",
    "pymupdf_find_tables",
    "camelot_stream",
    "camelot_lattice",
    "img2table_ruled",
    "img2table_borderless",
)
SCHEMA = "cite_refinery.external_pdf_interop.v1"


def canonical_tables(raw):
    """Preserve original cell strings, including signs, leading zeros, units."""
    tables = []
    for table in raw:
        if table is None:
            continue
        rows = []
        for row in table:
            if row is None:
                continue
            if not isinstance(row, (tuple, list)):
                raise TypeError("row not a sequence")
            normalized=[]
            for cell in row:
                if cell is None or (isinstance(cell, float) and math.isnan(cell)):
                    normalized.append("")
                elif isinstance(cell, str):
                    normalized.append(cell)
                else:
                    raise ValueError("non-string extracted cell would lose original numeric formatting")
            rows.append(normalized)
        if rows:
            tables.append(rows)
    return {"tables": tables}


def extraction(path: Path, engine: str):
    if engine == "pdfplumber_default":
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return canonical_tables(
                table for page in pdf.pages for table in (page.extract_tables() or [])
            )
    if engine == "pymupdf_find_tables":
        import pymupdf
        with pymupdf.open(path) as doc:
            return canonical_tables(
                table.extract() for page in doc
                for table in page.find_tables().tables
            )
    if engine.startswith("camelot_"):
        import camelot
        flavor = engine.split("_", 1)[1]
        return canonical_tables(
            t.df.values.tolist() for t in camelot.read_pdf(str(path), flavor=flavor, pages="all")
        )
    if engine.startswith("img2table_"):
        from img2table.document import PDF
        doc = PDF(src=str(path), pdf_text_extraction=True)
        result = doc.extract_tables(
            ocr=None, implicit_rows=False, implicit_columns=False,
            borderless_tables=engine == "img2table_borderless"
        )
        return canonical_tables(
            t.df.values.tolist()
            for page in sorted(result) for t in result[page]
        )
    raise ValueError("unknown extraction engine")


def run(root: Path, output: Path) -> dict:
    if not (root / "LICENSE").exists() or not (root / "cases/ruled.json").exists():
        raise ValueError("PDF Table Traps fixture root not recognized")
    commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    if commit != PINNED_FIXTURE_COMMIT:
        raise ValueError("fixture repository commit differs from benchmark's pinned upstream version")
    if output.exists():
        raise FileExistsError("output directory must not already exist")
    output.mkdir(parents=True, mode=0o700)
    out = []
    for case in FIXTURES:
        pdf = root / "fixtures" / f"{case}.pdf"
        rule = root / "cases" / f"{case}.json"
        if not pdf.is_file() or not rule.is_file():
            raise ValueError(f"missing fixture {case}")
        source_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
        for engine in ENGINES:
            start = time.perf_counter()
            extraction_error = None
            try:
                tables = extraction(pdf, engine)
            except Exception as ex:
                extraction_error = f"{type(ex).__name__}: {str(ex)[:160]}"
                tables = {"tables": []}
            extraction_ms = round((time.perf_counter() - start) * 1000, 1)
            artifact = output / f"{case}_{engine}.tables.json"
            artifact.write_text(json.dumps(tables, indent=2) + "\n", encoding="utf-8")
            report = output / f"{case}_{engine}.oracle.json"
            verify = subprocess.run(
                [sys.executable, "-m", "table_traps", "check",
                 "--input", str(artifact), "--format", "tables-json",
                 "--rules", str(rule), "--json", str(report)],
                cwd=root, capture_output=True, text=True, timeout=25, check=False,
            )
            oracle = json.loads(report.read_text()) if report.exists() else {}
            out.append({
                "case": case, "engine": engine, "fixture_sha256": source_hash,
                "time_ms": extraction_ms, "table_count": len(tables["tables"]),
                "extraction_error": extraction_error, "oracle_exit_code": verify.returncode,
                "oracle": oracle.get("status", "unavailable"),
                "check_counts": oracle.get("counts"),
                "notes": "Keyed-cell expectations from separately maintained fixture; no OCR or tuned prompts.",
            })
    verdict = {
        "schema": SCHEMA, "source_upstream": "https://github.com/LydiaTools/pdf-table-traps",
        "upstream_commit": commit,
        "engines": list(ENGINES), "source_cases": list(FIXTURES),
        "authority": "INDEPENDENT_FIXTURE_EVALUATION_NOT_ADOPTION",
        "results": out,
        "limits": [
            "3 small public synthetic source-checked PDF fixtures; not production OCR, financial filing, or general benchmark",
            "No official native Research Drive PDF table parser was verified in inspected checkout; generic local parsers are baselines",
            "Each engine uses one disclosed configuration; tuned accuracy and alternate document types remain untested",
            "Table Traps oracle can mark missing/ambiguous rows as unknown rather than a pass",
        ],
    }
    (output / "summary.json").write_text(json.dumps(verdict, indent=2) + "\n")
    return verdict


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--fixture-root", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    args = a.parse_args()
    result = run(args.fixture_root.resolve(), args.out.resolve())
    for e in ENGINES:
        rows = [r for r in result["results"] if r["engine"] == e]
        count = {"pass": sum(x["check_counts"].get("pass", 0) for x in rows if x["check_counts"]),
                 "fail": sum(x["check_counts"].get("fail", 0) for x in rows if x["check_counts"]),
                 "unknown": sum(x["check_counts"].get("unknown", 0) for x in rows if x["check_counts"])}
        print(e, count, "cases", {r["case"]:r["oracle"] for r in rows})
    print("summary", args.out.resolve() / "summary.json")


if __name__ == "__main__":
    main()
