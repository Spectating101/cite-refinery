"""Validate source-pinned original Jasmine and Ruby RSpec runtime transcripts.

A scoped framework suite is not a full application regression or an accepted
maintainer contribution. No runner here posts or modifies external repos.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re
from .pinned_original_component_trials import PINS,verify

SCHEMA="cite_refinery.framework_scoped_integration.v1"

def karma(text:str)->dict:
    matches=re.findall(r"Executed (\d+) of (\d+)(?: \((\d+) FAILED\))?",text)
    if not matches or "Chrome Headless" not in text:
        raise ValueError("must show executed browser Karma/Jasmine results")
    done,total,bad=matches[-1]
    if (int(done),int(total))!=(14,14):
        raise ValueError("nine original and five additional browser tests required")
    return {"tests":14,"failed":int(bad or 0),
            "original_jasmine_spec_included":True,
            "headless_browser_executed":True,
            "full_frontend_app_tested":False}

def rspec(data:dict)->dict:
    summary=data.get("summary",{})
    examples=data.get("examples",[])
    total=summary.get("example_count")
    failed=summary.get("failure_count")
    if total!=9 or not isinstance(failed,int) or len(examples)!=9 or (
        sum(row.get("status")!="passed" for row in examples)!=failed) or (
        not all("Foodsoft original OrdersHelper" in x.get("full_description","") for x in examples)):
        raise ValueError("nine source-linked RSpec results required")
    return {"tests":9,"failed":failed,"real_original_helper_executed":True,
            "ruby_rspec_isolated_with_fake_article_models":True,
            "full_Rails_database_suite_executed":False}

def build(checkouts:Path,repo:Path,original_browser:str,patched_browser:str,
          original_rspec:dict,patched_rspec:dict)->dict:
    originals={key:verify(checkouts,key) for key in PINS}
    a,b=karma(original_browser),karma(patched_browser)
    c,d=rspec(original_rspec),rspec(patched_rspec)
    if (a["failed"],b["failed"],c["failed"],d["failed"])!=(4,0,3,0):
        raise ValueError("original failures and isolated candidate improvements must all reproduce")
    for name in ("single geocode","multiple outliers","nonfinite","cross-antimeridian"):
        if name not in original_browser:
            raise ValueError("missing source-level geographic regression: "+name)
    patchdir=repo/"scripts/original_app_verification/candidates"
    patches={}
    for name in ("map_bounds_circular_longitude.experimental.patch",
                 "orders_helper_consistent_precision.experimental.patch"):
        data=(patchdir/name).read_bytes()
        if not 100<len(data)<15000:
            raise ValueError("candidate patch absent or outside bounded scope")
        patches[name]=sha256(data).hexdigest()
    return {
        "schema":SCHEMA,"recorded_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_checks":{
            key:{"commit":PINS[key]["git_commit"],"blob":PINS[key]["blob"],
                 "verified_against_local_checkout":True}
            for key in originals
        },
        "patch_sha256":patches,
        "open_food_network":{
            "reporter_issue":14924,"original":a,"local_candidate":b,
            "original_repo_jasmine_examples":9,"new_geographic_jasmine_examples":5,
            "bounded_Canada_fixture_only":True,
            "proposed_geographic_bounds_implemented_in_product_config":False,
            "production_zoom_and_viewport_verified":False,
            "mixed_global_geography_verified":False,
            "candidate_complete_application_fix":False,
        },
        "foodsoft":{
            "reporter_issue":1368,"original":c,"local_candidate":d,
            "BigDecimal_realistic_conversion_1_7_over_1_3":True,
            "real_Rails_OrderArticle_models_used":False,
            "upstream_Rails_RSpec_suite_completed":False,
            "candidate_complete_application_fix":False,
        },
        "evidence":{
            "scoped_framework_examples_executed":46,
            "original_source_expected_failures":7,
            "local_candidate_failures":0,
            "complete_Rails_or_Angular_application_suite_run":False,
            "maintainer_review_obtained":False,
            "third_party_repo_modified":False,
            "commercial_contract_or_revenue_verified":False,
            "native_graph_status_promoted":False,
            "research_holdout_touched":False,
        },
        "limitations":"Karma ran the real repo Jasmine spec plus 5 authored geographic tests in a minimal Angular stub; Foodsoft RSpec ran 9 authored cases on its original helper with BigDecimal fake model, not its full Rails suite. Fourteen passing map cases do not validate zoom or production instance bounds.",
    }

def markdown(r:dict)->str:
    if r.get("schema")!=SCHEMA:raise ValueError("wrong suite")
    o,f=r["open_food_network"],r["foodsoft"]
    return "\n".join([
        "# Browser Jasmine and Ruby RSpec: real scoped framework verification","",
        "Real pinned original source and two experimental local patches were executed.",
        "The full Angular frontend and Rails/database suites were NOT executed.","",
        "| Scoped suite | Original source | Experimental local patch |",
        "|---|---|---|",
        f"| OFN Karma/Jasmine browser (9 original + 5 new) | {o['original']['tests']-o['original']['failed']}/14 pass; 4 fail | 14/14 pass |",
        f"| Foodsoft RSpec against original Ruby helper (9 new cases) | {f['original']['tests']-f['original']['failed']}/9 pass; 3 fail | 9/9 pass |",
        "",
        "The OFN candidate uses newly proposed region-bounds configuration, filters",
        "nonfinite coordinates and uses circular longitude calculation. It handles",
        "synthetic multiple bad geocodes and a two-point antimeridian fixture.",
        "It DOES NOT wire those new config keys into real OFN instances or test",
        "zoom, nationwide viewport, true geocoding errors or all global geometry.","",
        "The Foodsoft candidate rounds both sides of a price conversion comparison",
        "to three decimal places. It passes real-helper RSpec assertions for",
        "ordered, received, billed, priority, nil and genuine discrepancy behavior.",
        "It DOES NOT use actual Rails OrderArticle models or a database; policy",
        "around precision and the complete project suite remain unverified.","",
        "## Hard gate","",
        "No upstream edit, submit, maintainer consent, full deployment, scientific",
        "outcome or paid customer is established. See the source-pinned patch",
        "diffs and executable test harnesses for the bounded next step.","",
    ])

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser()
    for field in ("checkouts","karma_original","karma_candidate",
                  "rspec_original","rspec_candidate","output","markdown"):
        p.add_argument("--"+field.replace("_","-"),type=Path,required=True)
    a=p.parse_args(argv)
    def read_json(path):return json.loads(path.read_text())
    r=build(a.checkouts,Path(__file__).resolve().parents[2],
            a.karma_original.read_text(),a.karma_candidate.read_text(),
            read_json(a.rspec_original),read_json(a.rspec_candidate))
    a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n")
    a.markdown.write_text(markdown(r))
    print("Scoped frameworks: 23 original cases, seven original failures; 23 patch cases, zero failures. Full-app status: UNVERIFIED")
    return 0
if __name__=="__main__":raise SystemExit(main())
