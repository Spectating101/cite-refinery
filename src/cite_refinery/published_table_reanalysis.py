"""Reanalyse published program-level catch counts (not missing raw field data).

Table T2 program rows support several sensitivity refits. They do not
automatically identify the authors' exact T3 or buffer intervention dataset.
Record all source-table arithmetic anomalies; never repair silently.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from .fulltext_audit import parse_article


def parse_published_program_table(jats_bytes,source_url):
    paper=parse_article(jats_bytes,source_url)
    if paper["doi"]!="10.14202/vetworld.2026.2816-2849":
        raise ValueError("This exact table replication targets the Anuradhapura source only")
    table=next((t for t in paper["tables"] if t["id"]=="T2"),None)
    if not table:raise ValueError("Missing source table T2")
    expected=["Year","Zone","Program no.","Total","Male","Female","No. of days"]
    if table["rows"][0]!=expected:raise ValueError("Unexpected program table layout; no guessed column mappings")
    data=[];source_subtotals={};issues=[]
    for index,row in enumerate(table["rows"][1:],2):
        if len(row)!=7:raise ValueError(f"Unexpected table row width: {index}")
        year,zone,program,total,male,female,days=row
        try:
            numerical=dict(Year=int(year),Zone=zone,Program=program,
                           Total=int(total),Male=int(male),Female=int(female),Days=int(days))
        except ValueError as exc:raise ValueError(f"Unexpected numeric value T2 row {index}") from exc
        if numerical["Year"] not in range(2021,2026) or zone not in {"1","2","3","Buffer"}:
            raise ValueError("Unexpected year or zone, inspect original publication")
        if any(v<0 for k,v in numerical.items() if k in {"Total","Male","Female","Days"}):
            raise ValueError("Negative population counts or effort")
        # Original JATS table has one blank program-number cell (2023/zone 1)
        # for the printed subtotal; recognize only when group context supports it.
        if program=="Sub total" or (program=="" and year=="2023" and zone=="1"):
            if program=="":
                issues.append({"type":"unlabelled_printed_subtotal","table_row":index,
                               "year":year,"zone":zone,"boundary":"Publisher table has blank subtotal label"})
            key=(year,zone)
            if key in source_subtotals:raise ValueError("Duplicated zone/year subtotal")
            source_subtotals[key]=numerical
            continue
        if not program.isdigit():raise ValueError("Unsupported program identifier")
        if numerical["Days"]==0 and numerical["Total"]!=0:
            issues.append({"type":"count_with_zero_days","table_row":index,"year":year,"zone":zone,
                           "program":program,"total":numerical["Total"]})
        if numerical["Total"]!=numerical["Male"]+numerical["Female"]:
            issues.append({
                "type":"within_row_sex_total_mismatch",
                "table_row":index,"year":year,"zone":zone,"program":program,
                "total":numerical["Total"],"male":numerical["Male"],"female":numerical["Female"],
                "sex_sum":numerical["Male"]+numerical["Female"],
                "difference_total_minus_sex_sum":numerical["Total"]-numerical["Male"]-numerical["Female"],
                "boundary":"Source table arithmetic discrepancy; cause unknown, no automatic correction.",
            })
        data.append(numerical)
    groups=defaultdict(list)
    for d in data:groups[(str(d["Year"]),d["Zone"])].append(d)
    for key,subtotal in source_subtotals.items():
        obs=groups.get(key)
        if not obs:
            issues.append({"type":"subtotal_without_program_rows","year":key[0],"zone":key[1]})
            continue
        calc={metric:sum(r[metric] for r in obs) for metric in ["Total","Male","Female","Days"]}
        if any(calc[k]!=subtotal[k] for k in calc):
            issues.append({"type":"source_subtotal_mismatch","year":key[0],"zone":key[1],
                           "reported":{k:subtotal[k] for k in calc},"computed":calc})
    if len(groups)!=20 or len(data)<60:
        raise ValueError("Program coverage radically differs from expected published source")
    return {
        "schema":"cite_refinery.published_program_table.v1",
        "source_doi":paper["doi"],"source_sha256":paper["source_sha256"],
        "source_url":source_url,"table_id":"T2","table_title":table["caption"],
        "observations":data,"source_subtotals_checked":len(source_subtotals),
        "row_count":len(data),"positive_effort_rows":sum(x["Days"]>0 for x in data),
        "arithmetic_issues":issues,
        "boundary":"Published program-level table, NOT original underlying operational intake records.",
    }


def write_reanalysis_materials(dataset,out_dir):
    base=Path(out_dir);base.mkdir(parents=True,exist_ok=True)
    table_path=base/"table2_programs_from_publication.csv"
    with table_path.open("w",newline="",encoding="utf-8") as f:
        columns=["Year","Zone","Program","Total","Male","Female","Days"]
        w=csv.DictWriter(f,fieldnames=columns,lineterminator="\n")
        w.writeheader();w.writerows(dataset["observations"])
    audit={key:value for key,value in dataset.items() if key!="observations"}
    audit["generated_csv_sha256"]=hashlib.sha256(table_path.read_bytes()).hexdigest()
    (base/"published_program_table_quality.json").write_text(json.dumps(audit,indent=2,ensure_ascii=False)+"\n")
    return audit
