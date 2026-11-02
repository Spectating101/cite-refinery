#!/usr/bin/env python3
"""Multi-page PDF semantic continuity acceptance on upstream source-checked PDFs.

Compares extraction defaults to a *separate*, explicitly operator-authorized,
fixture-specific header continuation. No generic automatic trust promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

FIXTURE_COMMIT="c63aab8884671aa4c789f08d0891f1a3f0ee5f5d"
HEAD=["Item","Zone","Count","Price"]
ENGINE_NAMES=["pdfplumber_default","pymupdf_find_tables","img2table_borderless"]
CASES=["single-header","repeat-header"]


def extract_per_page(path: Path, engine: str) -> list[list[list[list[str]]]]:
    if engine=="pdfplumber_default":
        import pdfplumber
        with pdfplumber.open(path) as d:
            return [[[[("" if v is None else str(v)) for v in row] for row in t]
                     for t in (page.extract_tables() or [])] for page in d.pages]
    if engine=="pymupdf_find_tables":
        import pymupdf
        with pymupdf.open(path) as d:
            return [[[[("" if v is None else str(v)) for v in row] for row in t.extract()]
                     for t in page.find_tables().tables] for page in d]
    if engine=="img2table_borderless":
        from img2table.document import PDF
        import math
        tabs=PDF(src=str(path),pdf_text_extraction=True).extract_tables(
            ocr=None,implicit_rows=False,implicit_columns=False,borderless_tables=True)
        return [[[[("" if v is None or (isinstance(v,float) and math.isnan(v)) else str(v))
                   for v in row] for row in table.df.values.tolist()] for table in tabs.get(i,[])]
                for i in range(3)]
    raise ValueError("unknown engine")


def verify(pages, *, carry_forward: bool):
    normalized=[]
    details=[]
    for n,pagetables in enumerate(pages,1):
        if len(pagetables)!=1:
            details.append({"page":n,"status":"NO_UNAMBIGUOUS_TABLE","tables":len(pagetables)})
            continue
        tab=pagetables[0]
        if not tab or len(tab[0])!=len(HEAD):
            details.append({"page":n,"status":"UNKNOWN_COLUMN_SHAPE"})
            continue
        header=tab[0]
        if header==HEAD:
            data=tab[1:]
            state="EXPLICIT_SOURCE_HEADER"
        elif carry_forward and n>1 and re.fullmatch(r"Plant-\d{2}",header[0] or ""):
            # Only available with an operator predeclared known header and
            # strong fixture-specific row key. Never silent automatic repair.
            data=tab
            state="OPERATOR_APPROVED_HEADER_CARRY_FORWARD"
        else:
            data=tab[1:]
            state="MISSING_REPEATED_HEADER_FIRST_ROW_AT_RISK"
        for row in data:
            if len(row)==len(HEAD) and re.fullmatch(r"Plant-\d{2}",row[0] or ""):
                normalized.append((row[0],row[2],n))
        details.append({"page":n,"status":state,"source_header_or_row":header,
                        "recognized_data_rows":sum(1 for r in data if r and re.fullmatch(r"Plant-\d{2}",r[0] or ""))})
    expected={f"Plant-{i:02}":str(20+i) for i in range(1,25)}
    found={a:b for a,b,n in normalized}
    good=sorted(k for k,v in expected.items() if found.get(k)==v)
    missing=sorted(k for k in expected if k not in found)
    wrong=sorted(k for k,v in expected.items() if k in found and found[k]!=v)
    duplicates=sorted({k for k,_,_ in normalized if [v[0] for v in normalized].count(k)>1})
    return {"pass":len(good),"missing":missing,"wrong":wrong,"duplicates":duplicates,
            "complete":len(good)==24 and not missing and not wrong and not duplicates,
            "details":details,
            "authority":"OPERATOR_DECLARED_KNOWN_24_ROWS_NOT_AUTOMATIC_VERIFICATION"}


def run(fixtures:Path,out:Path):
    commit=subprocess.run(["git","-C",str(fixtures),"rev-parse","HEAD"],
                          capture_output=True,text=True,check=True).stdout.strip()
    if commit!=FIXTURE_COMMIT:raise ValueError("unrecognized source fixture version")
    if out.exists():raise FileExistsError("immutable benchmark run output already exists")
    case_root=fixtures/"docs/cases/continuation"
    data=[]
    for case in CASES:
        p=case_root/(case+".pdf")
        if not p.is_file():raise FileNotFoundError(p)
        for engine in ENGINE_NAMES:
            t0=time.perf_counter()
            try:
                pages=extract_per_page(p,engine)
                error=None
            except Exception as e:
                pages=[]
                error=type(e).__name__+":"+str(e)[:140]
            for override in [False,True]:
                verdict=verify(pages,carry_forward=override)
                data.append({
                    "case":case,"engine":engine,
                    "mode":"operator_declared_header" if override else "naive_page_header",
                    "pdf_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
                    "duration_ms":round((time.perf_counter()-t0)*1000,1) if not override else None,
                    "extract_error":error,**verdict,
                })
    out.mkdir(parents=True,mode=0o700)
    result={"schema":"cite_refinery.multi_page_pdf_acceptance.v1",
            "upstream_repo":"https://github.com/LydiaTools/pdf-table-traps","source_commit":commit,
            "expected_rows_from_upstream_fixture_docs":24,
            "results":data,
            "limitations":["Synthetic 3-page originally source-checked fixture; not real reporting corpus.",
                           "Header recovery is fixture-specific, operator supplied, never general auto-adoption.",
                           "Identical 24 row labels across sources do not verify every other cell or page semantics."]}
    (out/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--fixtures",required=True,type=Path);ap.add_argument("--out",required=True,type=Path)
    a=ap.parse_args()
    r=run(a.fixtures,a.out)
    for row in r["results"]:
        print(row["case"],row["engine"],row["mode"],"valid",row["pass"],"missing",row["missing"],
              "complete",row["complete"],"error",row["extract_error"])
