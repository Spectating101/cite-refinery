#!/usr/bin/env python3
"""Positioned two-page source-cell acceptance using upstream fixture oracle.

Uses PDF Table Traps's existing positioned extractor; does not implement
another geometry solver. Exact fixture commit and explicit operator scope.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from interop_pdf_benchmark import extraction, PINNED_FIXTURE_COMMIT

ENGINES=("pdfplumber_default","pymupdf_find_tables","img2table_borderless",
         "operator_scoped_positioned")
SRC="fixtures/positional-two-page.pdf"
RULE="cases/positional-two-page.json"


def run(root: Path,out: Path) -> dict:
    commit=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],check=True,
                          capture_output=True,text=True).stdout.strip()
    if commit!=PINNED_FIXTURE_COMMIT: raise ValueError("source fixture commit mismatch")
    if out.exists():raise FileExistsError("immutable benchmark output must not exist")
    pdf=root/SRC
    rule=root/RULE
    if not pdf.is_file() or not rule.is_file():raise ValueError("missing source fixture")
    out.mkdir(parents=True,mode=0o700)
    sys.path.insert(0,str(root))
    from scripts.positional_table import extract as source_positioned_extract
    results=[]
    for engine in ENGINES:
        error=None
        try:
            if engine=="operator_scoped_positioned":
                tables,provenance=source_positioned_extract(
                    pdf,[0,60,612,500],[0,200,350,612],
                    ["Material","Quantity","Unit price"])
            else:
                tables=extraction(pdf,engine)
                provenance=None
        except Exception as exc:
            tables={"tables":[]}
            provenance=None
            error=type(exc).__name__+":"+str(exc)[:180]
        output=out/(engine+".json")
        output.write_text(json.dumps(tables,indent=2)+"\n")
        checks=out/(engine+".check.json")
        validation=subprocess.run([sys.executable,"-m","table_traps","check",
                "--input",str(output),"--format","tables-json","--rules",str(rule),
                "--json",str(checks)],cwd=root,capture_output=True,text=True,timeout=20)
        report=json.loads(checks.read_text()) if checks.exists() else {}
        results.append({"engine":engine,"tables":len(tables["tables"]),
                        "source_sha256":hashlib.sha256(pdf.read_bytes()).hexdigest(),
                        "status":report.get("status","unavailable"),
                        "counts":report.get("counts"),
                        "oracle_exit":validation.returncode,
                        "operator_defined_scope":engine=="operator_scoped_positioned",
                        "provenance_rows":len(provenance["rows"]) if provenance else None,
                        "error":error})
    receipt={"schema":"cite_refinery.positional_pdf_acceptance.v1",
             "source_commit":commit,"original_source":"https://github.com/LydiaTools/pdf-table-traps",
             "cases":"Two page same PDF coordinate / different extracted header width",
             "result":results,
             "limits":["Operator region/column edges are predeclared for this fixture; not automatic discovery.",
                       "Passing two price cells is not full table accuracy.",
                       "No OCR, long documents, scans or hostile PDFs tested."]}
    (out/"summary.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return receipt


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--fixtures",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    r=run(a.fixtures.resolve(),a.out.resolve())
    print(json.dumps({x["engine"]:{"status":x["status"],"checks":x["counts"]}
                      for x in r["result"]},indent=2))
