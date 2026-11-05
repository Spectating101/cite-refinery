#!/usr/bin/env python3
"""Offline, reproducible issuer-source-to-decision research dossier.

Reuses Research Drive's strict original SEC/EDGAR issuer witness.
Not a new extraction engine, investment recommendation or dataset publisher.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from decimal import Decimal,ROUND_HALF_UP
import hashlib,json
from pathlib import Path
import sys,time
from urllib.parse import urlsplit

SCHEMA="atlas.issuer_financial_decision_dossier.v1"
PRIMARY_IDS=("manulife-01","manulife-02","manulife-04","manulife-06",
             "manulife-05","manulife-07","manulife-08")
NAMES={"manulife-01":"Net income attributed to shareholders",
"manulife-02":"Core earnings (non-GAAP)","manulife-04":"APE sales",
"manulife-06":"New business CSM","manulife-05":"New business value (NBV)",
"manulife-07":"Global WAM net flows","manulife-08":"Average AUMA",
"general_expenses":"General expenses","total_expenses":"Total expenses",
"core_expenses":"Core expenses"}
EXPENSES=(("general_expenses",4,"General expenses - Statements of Income"),
          ("total_expenses",7,"Total expenses"),("core_expenses",13,"Core expenses"))

def percentage(now,then):
    if then==0:raise ValueError("zero original prior-year denominator")
    return (now/then-1)*100

def fmt(n,decimals=1):
    return f"{Decimal(n).quantize(Decimal('1').scaleb(-decimals),rounding=ROUND_HALF_UP):,.{decimals}f}"

def run(issuer_oracle,figure_oracle,source_dir,drive_root,secondary_pdf=None):
    t0=time.monotonic()
    sys.path.insert(0,str(drive_root.resolve(strict=True)/"drive"))
    from scripts.cluster_agent.optional_issuer_edgar_reconcile import (
        verify_issuer_filing_rows,_read_cell,_decimal)
    from bs4 import BeautifulSoup
    oracle=json.loads(issuer_oracle.read_text())
    figure=json.loads(figure_oracle.read_text())
    if oracle["schema"]!="atlas.manulife_2024q1_sec_filing_reconciliation_oracle.v1":
        raise ValueError("issuer row oracle changed")
    if figure["source_sha256"]!=oracle["original_reproduced_figure_sha256"]:
        raise ValueError("secondary original source figure hash changed")
    secondary_same=False
    if secondary_pdf is not None:
        secondary_same=hashlib.sha256(secondary_pdf.read_bytes()).hexdigest()==figure["source_sha256"]
        if not secondary_same:raise ValueError("pinned secondary PDF source changed")
    base=oracle["primary_issuer_edgar_exhibits"]
    specs={};docs={};tables={};verified={}
    for role,key in (("shareholder_report","shareholder_report_rows"),
                     ("earnings_release","earnings_release_rows")):
        original=base[role];spec=deepcopy(original)
        filename=Path(urlsplit(spec["url"]).path).name
        source=(source_dir/filename).resolve(strict=True)
        raw=source.read_bytes()
        spec["size_bytes"]=len(raw);spec["sha256"]=hashlib.sha256(raw).hexdigest()
        result=verify_issuer_filing_rows(source,spec,oracle[key])
        if result["matched"]!=len(oracle[key]) or result["abstained"]:
            raise ValueError("issuer primary financial source numeric or label mismatch")
        specs[role]=spec;docs[role]=source
        tables[role]=BeautifulSoup(raw,"html.parser").find_all("table")
        verified[role]=result
    context=verify_issuer_filing_rows(docs["shareholder_report"],
            specs["shareholder_report"],oracle["extra_context_checks"])
    if context["matched"]!=1:raise ValueError("issuer expense qualifier not validated")
    report_rows={r["case_id"]:r for r in oracle["shareholder_report_rows"]}
    release_rows={r["case_id"]:r for r in oracle["earnings_release_rows"]}
    metrics=[]
    for id in PRIMARY_IDS:
        a=report_rows[id];b=release_rows[id]
        if a["table_index"]!=10:raise ValueError("expected original issuer quarterly summary")
        first=tables["shareholder_report"][10]
        second=tables["earnings_release"][b["table_index"]]
        if (_read_cell(first,3,2)!="1Q24" or _read_cell(first,3,5)!="1Q23" or
            _read_cell(second,3,2)!="1Q24" or _read_cell(second,3,5)!="1Q23"):
            raise ValueError("cross-filing historical header mismatch")
        old=_decimal(_read_cell(first,a["row_index"],7))
        now=_decimal(_read_cell(first,a["row_index"],3))
        if (old is None or now is None or
            now!=_decimal(a["expected_source_numeric"]) or
            _decimal(_read_cell(second,b["row_index"],7))!=old or
            _decimal(_read_cell(second,b["row_index"],3))!=now):
            raise ValueError("cross-filing 2023/2024 numeric disagreement")
        if (_read_cell(first,a["row_index"],0)!=a["expected_source_label"] or
            _read_cell(second,b["row_index"],0)!=b["expected_source_label"]):
            raise ValueError("cross-filing original issuer metric label mismatch")
        metrics.append({"id":id,"label":NAMES[id],"now":str(now),"prior":str(old),
            "unit":a["issuer_unit"],"computed_nominal_change_pct":str(percentage(now,old)),
            "issuer_printed_change":_read_cell(first,a["row_index"],10),
            "filing_correspondence":"BOTH_ISSUER_EXHIBITS",
            "source_cells":[
             {"role":"shareholder_report","table":10,"row":a["row_index"],
              "col_2024":3,"col_2023":7},
             {"role":"earnings_release","table":b["table_index"],"row":b["row_index"],
              "col_2024":3,"col_2023":7}]})
    expense_table=tables["shareholder_report"][329]
    if _read_cell(expense_table,2,2)!="1Q24" or _read_cell(expense_table,2,14)!="1Q23":
        raise ValueError("expense original quarterly historical header mismatch")
    if "millions" not in _read_cell(expense_table,2,0).lower():
        raise ValueError("expense scale unspecified")
    for id,row,label in EXPENSES:
        if _read_cell(expense_table,row,0)!=label:
            raise ValueError("original issuer expense source label mismatch")
        now=_decimal(_read_cell(expense_table,row,3))
        old=_decimal(_read_cell(expense_table,row,19))
        if now is None or old is None:raise ValueError("original issuer expense number not atomic")
        metrics.append({"id":id,"label":NAMES[id],"now":str(now),"prior":str(old),
            "unit":"CAD_millions","computed_nominal_change_pct":str(percentage(now,old)),
            "issuer_printed_change":None,
            "filing_correspondence":"SHAREHOLDER_REPORT_ONLY",
            "source_cells":[{"role":"shareholder_report","table":329,"row":row,
                             "col_2024":3,"col_2023":19}]})
    by={x["id"]:x for x in metrics}
    def val(id,when):return Decimal(by[id][when])
    analysis={"gap_core_minus_net_2024_cad_millions":
              str(val("manulife-02","now")-val("manulife-01","now")),
              "gap_core_minus_net_2023_cad_millions":
              str(val("manulife-02","prior")-val("manulife-01","prior")),
              "issuer_reported_change_and_nominal_arithmetic_kept_distinct":True}
    for role,s in specs.items():
        if hashlib.sha256(docs[role].read_bytes()).hexdigest()!=s["sha256"]:
            raise ValueError("original issuer filing mutated during decision workflow")
    return {"schema":SCHEMA,"issuer":"Manulife Financial Corporation",
       "scope":"First quarter 2024 versus first quarter 2023",
       "source_exhibits":{k:{"url":s["url"],"source_sha256":s["sha256"],
          "source_size_bytes":s["size_bytes"],"earlier_pinned_sha256":base[k]["sha256"],
          "earlier_capture_same_bytes":s["sha256"]==base[k]["sha256"],
          "source_kind":"SEC_FILED_ISSUER_HTML_NOT_ISSUER_ORIGINAL_PDF"}
           for k,s in specs.items()},
       "metrics":metrics,"analysis":analysis,
       "issuer_2024_rows_verified_shareholder":verified["shareholder_report"]["matched"],
       "issuer_2024_rows_verified_release":verified["earnings_release"]["matched"],
       "issuer_2024_expense_qualifier_verified":context["matched"],
       "historical_rows_with_two_same_issuer_exhibits":7,
       "historical_expense_rows_one_exhibit":3,
       "secondary_pdf_sha_rechecked":secondary_same,
       "secondary_parser_prior_strict_matches":6,
       "secondary_parser_prior_abstentions":2,
       "uncertainties":[
         "The full core-earnings to net-income reconciliation was not performed",
         "Published changes may be on a constant-exchange-rate/non-GAAP basis, not nominal arithmetic",
         "The original issuer PDF binary is not verified; primary evidence is SEC-filed issuer HTML",
         "The previously parsed secondary PDF has two unresolved strict parser abstentions",
         "Neither source agreement nor a generated report is independent human semantic review"],
       "independent_human_approvals":0,"trusted_dataset_promotions":0,
       "auto_publish":False,"decision":"HOLD_REVIEW_BEFORE_TRUSTED_PUBLICATION",
       "execution_seconds":round(time.monotonic()-t0,3)}

def validate_snapshot(r):
    """Guard against turning a source row receipt into unsupported analysis."""
    if (r.get("schema")!=SCHEMA or r.get("auto_publish") is not False or
        r.get("trusted_dataset_promotions")!=0 or
        r.get("independent_human_approvals")!=0 or
        r.get("issuer_2024_rows_verified_shareholder")!=8 or
        r.get("issuer_2024_rows_verified_release")!=7 or
        r.get("issuer_2024_expense_qualifier_verified")!=1):
        raise ValueError("issuer research trust or original source witness contract invalid")
    sources=r.get("source_exhibits")
    if not isinstance(sources,dict) or set(sources)!={"shareholder_report","earnings_release"}:
        raise ValueError("issuer source roles missing")
    for role,s in sources.items():
        if (not s["url"].startswith("https://www.sec.gov/Archives/edgar/data/1086888/") or
            len(s["source_sha256"])!=64 or s["source_size_bytes"]<10000 or
            s["source_kind"]!="SEC_FILED_ISSUER_HTML_NOT_ISSUER_ORIGINAL_PDF"):
            raise ValueError("issuer source custody metadata not supported")
    rows=r.get("metrics")
    if not isinstance(rows,list) or len(rows)!=10 or len({x["id"] for x in rows})!=10:
        raise ValueError("expected original research coverage differs")
    if {x["id"] for x in rows}!=set(PRIMARY_IDS)|{e[0] for e in EXPENSES}:
        raise ValueError("financial dossier metric identity differs")
    for x in rows:
        if (x["unit"] not in ("CAD_millions","CAD_billions") or
            Decimal(x["computed_nominal_change_pct"])!=percentage(Decimal(x["now"]),Decimal(x["prior"]))):
            raise ValueError("nominal comparison is not computed from source literals")
        roles={z["role"] for z in x["source_cells"]}
        expected_roles={"shareholder_report","earnings_release"} if x["id"] in PRIMARY_IDS else {"shareholder_report"}
        if roles!=expected_roles or len(x["source_cells"])!=len(expected_roles):
            raise ValueError("historical source evidence coverage was overstated")
        for z in x["source_cells"]:
            if z["table"]<0 or z["row"]<0 or z["col_2024"]<0 or z["col_2023"]<0:
                raise ValueError("invalid source cell coordinates")
    cells={x["id"]:x for x in rows}
    if (Decimal(r["analysis"]["gap_core_minus_net_2024_cad_millions"])!=
        Decimal(cells["manulife-02"]["now"])-Decimal(cells["manulife-01"]["now"]) or
        Decimal(r["analysis"]["gap_core_minus_net_2023_cad_millions"])!=
        Decimal(cells["manulife-02"]["prior"])-Decimal(cells["manulife-01"]["prior"])):
        raise ValueError("core versus net income interpretation not mathematically supported")
    return True

def render_markdown(r):
    x={d["id"]:d for d in r["metrics"]}
    def change(id):
        n=Decimal(x[id]["computed_nominal_change_pct"])
        return ("+" if n>0 else "")+fmt(n)+"%"
    def amount(id,when):
        item=x[id];n=1 if item["unit"]=="CAD_billions" else 0
        return fmt(item[when],n)
    lines=[
      "# Manulife: improving core earnings, falling net income",
      "",
      "Issuer-backed research brief | Q1 2024 versus Q1 2023 | Analyst review pending",
      "",
      "## What matters",
      "",
      "Core earnings (non-GAAP) increased "+change("manulife-02")+
        " on displayed nominal C$ figures, while net income attributed to shareholders fell "+
        change("manulife-01")+". The numerical gap between them widened from C$"+
        fmt(r["analysis"]["gap_core_minus_net_2023_cad_millions"],0)+
        "m to C$"+fmt(r["analysis"]["gap_core_minus_net_2024_cad_millions"],0)+
        "m. This is a real difference in printed values, NOT an established causal explanation.",
      "",
      "APE sales rose "+change("manulife-04")+", new business CSM "+
         change("manulife-06")+", and NBV "+change("manulife-05")+
         ". Core expenses rose "+change("core_expenses")+
         ". These signals justify reviewing the non-GAAP reconciliation and currency context, not a trading conclusion.",
      "",
      "## Original issuer data and calculated comparison","",
      "| Metric | 1Q24 | 1Q23 | Nominal change | Reported change | SEC source |",
      "|---|---:|---:|---:|---:|---|"
    ]
    for m in r["metrics"]:
        suffix="C$bn" if m["unit"]=="CAD_billions" else "C$m"
        given=m["issuer_printed_change"] or "—"
        src="; ".join("["+s["role"].replace("_"," ")+" T"+
            str(s["table"])+" R"+str(s["row"])+"]("+
            r["source_exhibits"][s["role"]]["url"]+")" for s in m["source_cells"])
        lines.append("| "+m["label"]+" ("+suffix+") | "+
            amount(m["id"],"now")+" | "+amount(m["id"],"prior")+" | "+
            change(m["id"])+" | "+given+" | "+src+" |")
    lines+=["",
      "Reported change is transcribed from the issuer's 1Q24 shareholder report; nominal change is calculated as (1Q24/1Q23 - 1) × 100 from displayed amounts. They can differ because the issuer reports some changes on constant-exchange-rate or non-GAAP bases. Do not treat them as equivalent.","",
      "## Reproducible evidence chain",""]
    for role,v in r["source_exhibits"].items():
        lines.append("- "+role.replace("_"," ")+": ["+v["url"]+"]("+v["url"]+
          "); this capture SHA-256 "+v["source_sha256"]+
          "; "+str(v["source_size_bytes"])+
          " bytes. Earlier pinned SEC capture byte-identical? "+str(v["earlier_capture_same_bytes"])+".")
    lines+=["",
      "The existing Research Drive EDGAR witness revalidated eight 1Q24 issuer shareholder rows and seven 1Q24 earnings-release rows, plus one expense qualifier. Seven historical metric pairs matched across two separate SEC exhibits by the **same issuer**, and three expense pairs were sourced from the shareholder report only.",
      "",
      "The reproduced secondary PDF is not the issuer's source. Its earlier strict parser check matched six of eight cells and abstained on two. Primary issuer HTML corroboration does not silently approve those parser failures.",
      "",
      "## Decision and limitations","",
      "**Next research question:** determine the items explaining the widening difference between core earnings and net income, and reconcile constant-exchange-rate reporting using the issuer's MD&A before asserting the drivers.",
      "",
    ]
    lines+=["- "+u for u in r["uncertainties"]]
    lines+=["",
      "Outcome: 10 issuer-linked historical metric comparisons; 7 dual-exhibit checks; 3 expense context checks. Zero independent human approvals and zero trusted dataset promotions. Historical issuer analysis only, not investment advice.",""]
    validate_snapshot(r)
    return "\n".join(lines).replace("C$","C\\$")

def main():
    p=argparse.ArgumentParser()
    for k in ("issuer-oracle","figure-oracle","issuer-dir","research-drive-root","out-json","out-md"):
        p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--secondary-pdf",type=Path)
    a=p.parse_args()
    if a.out_json.exists() or a.out_md.exists():raise FileExistsError("refuse to overwrite prior research dossier")
    result=run(a.issuer_oracle,a.figure_oracle,a.issuer_dir,a.research_drive_root,a.secondary_pdf)
    validate_snapshot(result)
    a.out_json.parent.mkdir(parents=True,exist_ok=True)
    a.out_md.parent.mkdir(parents=True,exist_ok=True)
    a.out_json.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    a.out_md.write_text(render_markdown(result))
    print(json.dumps({"status":result["decision"],"rows":len(result["metrics"]),
                      "dual":result["historical_rows_with_two_same_issuer_exhibits"],
                      "sources":len(result["source_exhibits"]),
                      "runtime_seconds":result["execution_seconds"]}))
if __name__=="__main__":main()
