"""Bounded source-inspected arithmetic reproductions of two real maintainer issues.

Fetch ONLY the exact reviewed public GitHub source blobs; verify Git's content
SHA before any analytical calculations. This is not execution of original
CoffeeScript/Angular or Foodsoft/Ruby runtime; this bridge is a scoped contract
and requires application-specific integration tests before a PR.
"""
from __future__ import annotations
import argparse
import base64
from decimal import Decimal,localcontext
from hashlib import sha1
import json
from pathlib import Path
import subprocess
from typing import Any

CASES=(
    {"id":"ofn_canada_map_bounds",
     "repo":"openfoodfoundation/openfoodnetwork",
     "ref":"1167aa7b7585c1794199e032fc15c0e9c1c74104",
     "path":"app/assets/javascripts/darkswarm/services/map_centre_calculator.js.coffee",
     "git_blob_sha":"74a669690f56c15f2c15ceffe34c8f02a96d0e27",
     "required_tokens":["minimumAngle = Math.min.apply(null, angles)",
                        "maximumAngle = Math.max.apply(null, angles)",
                        "minimumAngle + (distanceBetweenMinimumAndMaximum / 2)"],
    },
    {"id":"foodsoft_order_quantity_rounding",
     "repo":"foodcoops/foodsoft",
     "ref":"f594be8e64f4d3748d0e418df05fbb554ccce71b",
     "path":"app/helpers/orders_helper.rb",
     "git_blob_sha":"64567d22f2a02cd3d4b0a481ff1f8b581e90420d",
     "required_tokens":["def ordered_quantities_different_from_group_orders?",
                        "group_orders_sum_quantity = order_article.group_orders_sum[:quantity]",
                        "price.group_order_unit).round(3) == group_orders_sum_quantity"],
    },
)
SCHEMA="cite_refinery.reported_issue_arithmetic_contracts.v1"

def _read_source(spec:dict[str,Any])->str:
    path="repos/"+spec["repo"]+"/contents/"+spec["path"]+"?ref="+spec["ref"]
    proc=subprocess.run(["gh","api",path],capture_output=True,text=True,timeout=25)
    if proc.returncode:
        raise ValueError("pinned source unavailable; do not substitute current main")
    meta=json.loads(proc.stdout)
    if meta.get("path")!=spec["path"] or meta.get("sha")!=spec["git_blob_sha"] or \
       meta.get("encoding")!="base64":
        raise ValueError("pinned GitHub blob identity changed")
    data=base64.b64decode(meta["content"])
    true_sha=sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
    if true_sha!=spec["git_blob_sha"]:
        raise ValueError("local byte-level Git blob SHA mismatch")
    text=data.decode("utf-8")
    if any(token not in text for token in spec["required_tokens"]):
        raise ValueError("pinned source contract no longer matches inspected code")
    return text

def evaluate_source(spec:dict[str,Any],text:str)->dict[str,Any]:
    if any(t not in text for t in spec["required_tokens"]):
        raise ValueError("source-derived arithmetic contract not anchored")
    id=spec["id"]
    if id=="ofn_canada_map_bounds":
        # Representative synthetic latitudes, not any actual enterprise location.
        canada=[49.0,53.0,51.0]
        outlier=-15.0
        def midpoint(a):return min(a)+(max(a)-min(a))/2
        before=midpoint(canada)
        after=midpoint(canada+[outlier])
        result={
            "fixture":"three invented Canada-like latitudes 49/53/51 and a synthetic mis-geocoded latitude -15",
            "without_outlier_latitude":before,
            "with_outlier_latitude":after,
            "latitude_shift_degrees":round(after-before,2),
            "center_is_robust_to_outlier":False if abs(after-before)>10 else True,
            "regression_contract":"Outlier must not move first-view map outside normal region; use instance-defined override or robust geographic bounds.",
            "code_execution_mode":"independent numeric analog of exact source min/max arithmetic, not original CoffeeScript execution",
        }
        passed=before==51.0 and after==19.0
    elif id=="foodsoft_order_quantity_rounding":
        with localcontext() as c:
            c.prec=35
            raw=Decimal("1.7")/Decimal("1.3")
            left=raw.quantize(Decimal("0.001"))
            old_match=left==raw
            new_match=left==raw.quantize(Decimal("0.001"))
        result={
            "fixture":"1.7 kg ordered divided by 1.3 kg per unit",
            "exact_group_quantity":str(raw),
            "rounded_order_quantity":str(left),
            "asymmetric_original_equality":old_match,
            "symmetrically_rounded_equality":new_match,
            "regression_contract":"Compared quantities must use consistent precision, including a fixture for units 1.7kg/1.3kg.",
            "code_execution_mode":"independent Decimal analog of source helper, not original Ruby execution",
        }
        passed=(not old_match and new_match and left==Decimal("1.308"))
    else:
        raise ValueError("unknown source-backed issue")
    if not passed:
        raise ValueError("arithmetic fixture no longer reproduces described mechanism")
    return {
        "id":id,"issue_url":{
            "ofn_canada_map_bounds":"https://github.com/openfoodfoundation/openfoodnetwork/issues/14924",
            "foodsoft_order_quantity_rounding":"https://github.com/foodcoops/foodsoft/issues/1368"}[id],
        "source_url":"https://github.com/"+spec["repo"]+"/blob/"+spec["ref"]+"/"+spec["path"],
        "source_commit":spec["ref"],
        "source_git_blob_sha":spec["git_blob_sha"],
        "source_anchors_present":True,
        "arithmetic_analog_reproduced":True,
        "upstream_application_executed":False,
        "runtime_integration_test_available":False,
        "full_application_impact_verified":False,
        "reproduction":result,
        "source_scope":"Exact original source blob and arithmetic only; no Ruby/CoffeeScript app or end-user field simulation",
    }

def run(fetch=_read_source)->dict[str,Any]:
    outcomes=[]
    for s in CASES:
        original=fetch(s)
        outcomes.append(evaluate_source(s,original))
    return {
        "schema":SCHEMA,"cases":outcomes,
        "source_verification":"Public GitHub blob SHA1 and inspected source tokens verified at exact commit",
        "original_app_executed":False,"model_output_used_as_proof":False,
        "source_check_implies_operator_demand":False,
        "external_contact_made":False,"commercial_revenue_verified":False,
        "boundary":"Source-derived analogs support bug mechanism and regression design only, not end-to-end fix, deployment or paid maintainer request.",
    }

def markdown(data:dict[str,Any])->str:
    if data.get("schema")!=SCHEMA:raise ValueError("missing source contracts")
    out=[
        "# Two reported maintainer problems with source-fingerprinted arithmetic reproductions", "",
        "Open public issue reports are paired with exact code blobs at independently "
        "checked repository commit SHAs. These tests execute **numeric analogs** "
        "of their underlying calculations, not the CoffeeScript or Ruby applications.","",
    ]
    for row in data["cases"]:
        r=row["reproduction"]
        out+=["## "+row["id"].replace("_"," ").title(),"",
              "[Source]("+row["source_url"]+") · [Issue]("+row["issue_url"]+")", "",
              "**Reproduction:** "+r["fixture"],"",
              "**Engineering contract:** "+r["regression_contract"],"",
              "**Execution status:** "+r["code_execution_mode"],""]
        if row["id"]=="ofn_canada_map_bounds":
            out+=["Latitude midpoint without synthetic outlier: "+
                  str(r["without_outlier_latitude"])+
                  "; with one outlier: "+str(r["with_outlier_latitude"])+".",""]
        else:
            out+=["Exact computed units: "+r["exact_group_quantity"]+
                  "; rounded units: "+r["rounded_order_quantity"]+
                  "; original asymmetric equality: "+str(r["asymmetric_original_equality"])+
                  "; symmetric precision equality: "+str(r["symmetrically_rounded_equality"])+".",""]
    out+=["## Required next proof","",
          "Run the original application-specific test suite, inspect geography/"
          "decimal edge cases and safe fixes with maintainer guidance. A reported "
          "bug does not imply a purchase commitment, and matching code tokens "
          "does not establish a production failure outside the reported case.",""]
    return "\n".join(out)

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(prog="cite-refinery-reported-issue-contracts")
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    a=p.parse_args(argv)
    data=run()
    a.output.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    a.markdown.write_text(markdown(data),encoding="utf-8")
    print("Exact source anchors:",len(data["cases"]),"original application runtimes executed:",data["original_app_executed"])
    return 0
if __name__=="__main__":
    raise SystemExit(main())
