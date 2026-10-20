"""Run pinned upstream component functions, plus scratch-only candidate patches.

This is not a browser/Angular or Rails/database integration test. Node compiles
the ORIGINAL CoffeeScript factory with its declared 1.12.7 toolchain; Ruby
loads the ORIGINAL OrdersHelper inside an isolated, network-disabled container.
No external repo changes, no app deployments or maintainer outreach.
"""
from __future__ import annotations
import argparse
from hashlib import sha1
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

SCHEMA="cite_refinery.pinned_original_component_trials.v1"
PINS={
  "openfoodnetwork":{
    "git_commit":"1167aa7b7585c1794199e032fc15c0e9c1c74104",
    "path":"app/assets/javascripts/darkswarm/services/map_centre_calculator.js.coffee",
    "blob":"74a669690f56c15f2c15ceffe34c8f02a96d0e27",
    "issue_url":"https://github.com/openfoodfoundation/openfoodnetwork/issues/14924",
  },
  "foodsoft":{
    "git_commit":"337489007f863d64abf2fae7b20f440f1651ab00",
    "path":"app/helpers/orders_helper.rb",
    "blob":"64567d22f2a02cd3d4b0a481ff1f8b581e90420d",
    "issue_url":"https://github.com/foodcoops/foodsoft/issues/1368",
  },
}
# Immutable digest from the pulled official Ruby runtime image on test day.
RUBY_IMAGE="ruby@sha256:d9e5298c8c7dad54b40facac94be1baa10f593db7dec7a9afb47bd44a64c15a9"

def git_blob(content:bytes)->str:
    return sha1(b"blob "+str(len(content)).encode("ascii")+b"\0"+content).hexdigest()

def verify(root:Path,slug:str)->Path:
    if slug not in PINS:raise ValueError("unknown original source")
    spec=PINS[slug]
    base=root/slug
    if not (base/".git").exists():raise ValueError("original repo checkout missing")
    proc=subprocess.run(["git","-C",str(base),"rev-parse","HEAD"],
                        capture_output=True,text=True,timeout=12,check=True)
    if proc.stdout.strip()!=spec["git_commit"]:
        raise ValueError("source tree revision does not match checked snapshot")
    file=base/spec["path"]
    if git_blob(file.read_bytes())!=spec["blob"]:
        raise ValueError("original source file does not match checked Git blob")
    return file

def patch_source(slug:str,source:str)->str:
    if slug=="openfoodnetwork":
        original="      minimumAngle + (distanceBetweenMinimumAndMaximum / 2)"
        patched="""      sortedAngles = angles.slice().sort (a, b) -> a - b
      mid = Math.floor(sortedAngles.length / 2)
      if sortedAngles.length % 2 == 0
        (sortedAngles[mid - 1] + sortedAngles[mid]) / 2
      else
        sortedAngles[mid]"""
        occurrences=1
    elif slug=="foodsoft":
        original=".round(3) == group_orders_sum_quantity"
        patched=".round(3) == group_orders_sum_quantity.round(3)"
        occurrences=2
    else:raise ValueError("unverified patch target")
    if source.count(original)!=occurrences:
        raise ValueError("cannot safely patch changed upstream source")
    return source.replace(original,patched)

def _call(command:list[str],*,timeout:int=30)->dict[str,Any]:
    p=subprocess.run(command,check=False,capture_output=True,text=True,timeout=timeout)
    if p.returncode:
        # Avoid leaking environment-specific error output to generated reports.
        raise RuntimeError("original component test runner failed; exit="+str(p.returncode))
    try:
        out=json.loads(p.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("runner did not return strict JSON") from exc
    if not isinstance(out,dict):raise ValueError("invalid test report")
    return out

def _validate(ofn_o,ofn_p,food_o,food_p)->None:
    for x,expected in ((ofn_o,"pinned_upstream"),(ofn_p,"local_candidate_patch"),
                       (food_o,"pinned_upstream"),(food_p,"local_candidate_patch")):
        if x.get("source_kind")!=expected or not isinstance(x.get("validations"),list):
            raise ValueError("runtime report type mismatch")
    if not (ofn_o.get("upstream_source_compiled_and_executed") is True and
            ofn_p.get("upstream_source_compiled_and_executed") is True and
            food_o.get("upstream_ruby_helper_loaded_and_executed") is True and
            food_p.get("upstream_ruby_helper_loaded_and_executed") is True):
        raise ValueError("original code was not actually executed")
    if ofn_o.get("outlier_regression_pass") is not False or \
       ofn_p.get("outlier_regression_pass") is not True:
        raise ValueError("outlier original failure/partial repair did not reproduce")
    if ofn_o.get("multiple_outliers_regression_pass") is not False or \
       ofn_p.get("multiple_outliers_regression_pass") is not False:
        raise ValueError("known limitations of simple median were obscured")
    if ofn_o.get("all_standard_regressions_pass") is not True or \
       ofn_p.get("all_standard_regressions_pass") is not True:
        raise ValueError("standard map center regression failed")
    if food_o.get("equal_ordered_and_received_precision_regressions_pass") is not False or \
       food_p.get("equal_ordered_and_received_precision_regressions_pass") is not True:
        raise ValueError("Foodsoft original failure/candidate repair did not reproduce")
    if food_p.get("genuine_difference_regressions_pass") is not True:
        raise ValueError("Foodsoft local patch hides genuine discrepancies")
    if any(x.get("full_angular_app_executed") or
           x.get("original_application_test_suite_executed") for x in (ofn_o,ofn_p)) or \
       any(x.get("rails_app_executed") or x.get("rails_test_suite_executed") for x in (food_o,food_p)):
        raise ValueError("component execution cannot claim full app integration")

def run(checkouts:Path,repo_root:Path)->dict[str,Any]:
    ofn=verify(checkouts,"openfoodnetwork")
    food=verify(checkouts,"foodsoft")
    coffee=checkouts/"tooling/node_modules/coffee-script"
    if not (coffee/"package.json").exists() or \
       json.loads((coffee/"package.json").read_text())["version"]!="1.12.7":
        raise ValueError("project-pinned CoffeeScript 1.12.7 not installed")
    scripts=repo_root/"scripts/original_app_verification"
    js=scripts/"ofn_coffeescript_component.js"
    ruby=scripts/"foodsoft_ruby_helper.rb"
    if not (js.is_file() and ruby.is_file()):
        raise ValueError("bound original-function harness absent")
    # scratch-only patch: candidate files exist solely in an ephemeral,
    # source-independent path. Original checkouts are verified before and after.
    with tempfile.TemporaryDirectory(prefix="candidate_trials_",dir=checkouts) as td:
        scratch=Path(td)
        coffeep=scratch/"map_centre_calculator.coffee"
        rubyp=scratch/"orders_helper.rb"
        coffeep.write_text(patch_source("openfoodnetwork",ofn.read_text()))
        rubyp.write_text(patch_source("foodsoft",food.read_text()))
        ofn_o=_call(["node",str(js),str(ofn),str(coffee),"original"])
        ofn_p=_call(["node",str(js),str(coffeep),str(coffee),"candidate"])
        # Run Ruby with no network, immutable rootfs, minimal privileges,
        # no root capabilities, bounded resources and pinned image digest.
        ruby_base=[
            "docker","run","--rm","--pull=never",
            "--user",f"{os.getuid()}:{os.getgid()}",
            "--network","none","--read-only","--memory","256m",
            "--pids-limit","64","--cap-drop","ALL",
            "-v",str(checkouts)+":/inputs:ro",
            "-v",str(scripts)+":/runner:ro",
            RUBY_IMAGE,"ruby","/runner/foodsoft_ruby_helper.rb",
        ]
        rel=scratch.relative_to(checkouts)
        food_o=_call(ruby_base+["/inputs/foodsoft/app/helpers/orders_helper.rb","original"],timeout=45)
        food_p=_call(ruby_base+["/inputs/"+str(rel/"orders_helper.rb"),"candidate"],timeout=45)
    verify(checkouts,"openfoodnetwork")
    verify(checkouts,"foodsoft")
    _validate(ofn_o,ofn_p,food_o,food_p)
    return {
        "schema":SCHEMA,
        "original_source_pins":PINS,
        "runtimes":{"ofn":"node+coffee-script@1.12.7 (original project pin)",
                    "foodsoft":"ruby 3.3-alpine digest-pinned network-disabled container"},
        "cases":[
            {"id":"ofn_canada_map_bounds","issue_url":PINS["openfoodnetwork"]["issue_url"],
             "source_kind":"exact_original_coffeescript_factory",
             "original_execution":ofn_o,"temporary_candidate_execution":ofn_p,
             "original_defect_reproduced":True,"candidate_one_outlier_passes":True,
             "candidate_multiple_outliers_passes":False,
             "candidate_zoom_and_geographic_bounds_verified":False,
             "next_gate":"Full Angular component/Jasmine tests, outlier strategy across multiple countries, configurable zoom/bounds and maintainer approval."},
            {"id":"foodsoft_order_quantity_rounding","issue_url":PINS["foodsoft"]["issue_url"],
             "source_kind":"exact_original_Ruby_OrdersHelper_in_container",
             "original_execution":food_o,"temporary_candidate_execution":food_p,
             "original_defect_reproduced":True,"candidate_ordered_received_pass":True,
             "candidate_genuine_discrepancies_preserved":True,
             "rails_application_integration_verified":False,
             "next_gate":"Execute original Foodsoft Rails helper/integration suite, check rounding policy at decimal boundaries, get maintainer feedback."},
        ],
        "limitations":{
            "actual_original_functions_executed":True,
            "full_angular_app_or_browser_tested":False,
            "rails_database_or_complete_suite_tested":False,
            "all_proposed_repair_requirements_passed":False,
            "third_party_repository_modified":False,
            "published_external_patches":False,
            "paid_operator_demand_verified":False,
            "commercial_conversion_achieved":False,
            "native_graph_status_promoted":False,
            "research_holdout_touched":False,
        },
        "scope":"Component-level original runtime execution on synthetic fixtures; the simple map median candidate still fails multiple outliers and leaves configurable zoom unaddressed.",
    }

def markdown(j:dict[str,Any])->str:
    if j.get("schema")!=SCHEMA:raise ValueError("incorrect runtime record")
    a,b=j["cases"]
    lines=[
        "# Original-runtime component execution: OFN and Foodsoft", "",
        "**Both original source functions were actually executed using appropriate "
        "language runtimes and SHA-checked source revisions.** This is materially "
        "stronger than an arithmetic analog, but not yet full framework integration.","",
        "## Open Food Network — original CoffeeScript factory", "",
        f"Source: {a['issue_url']}. The actual MapCentreCalculator service was "
        "compiled with coffee-script 1.12.7 and exercised using a minimal "
        "Angular factory capture with synthetic geocoded-enterprise data.","",
        "| Test | Original | Local median candidate |",
        "|---|---|---|",
        f"| Prior ordinary/default-center fixtures | {'pass' if a['original_execution']['all_standard_regressions_pass'] else 'fail'} | {'pass' if a['temporary_candidate_execution']['all_standard_regressions_pass'] else 'fail'} |",
        f"| One wrong geographic outlier | {'pass' if a['original_execution']['outlier_regression_pass'] else 'FAIL'} | {'pass' if a['temporary_candidate_execution']['outlier_regression_pass'] else 'FAIL'} |",
        f"| Three coordinated wrong outliers | {'pass' if a['original_execution']['multiple_outliers_regression_pass'] else 'FAIL'} | {'pass' if a['temporary_candidate_execution']['multiple_outliers_regression_pass'] else 'FAIL'} |",
        "",
        "**Not ready as a full fix:** the median prototype fails the multi-outlier "
        "regression and does not implement zoom/viewport policy. No browser, "
        "real address or nationwide bounds integration was exercised.","",
        "## Foodsoft — original Ruby OrdersHelper", "",
        f"Source: {b['issue_url']}. The actual module was loaded and invoked "
        "inside a digest-pinned Ruby container with network disabled, "
        "read-only mounts and BigDecimal conversion fakes.","",
        "| Test | Original | Local symmetric-rounding candidate |",
        "|---|---|---|",
        f"| Equal quantities, ordered/received branches | {'pass' if b['original_execution']['equal_ordered_and_received_precision_regressions_pass'] else 'FAIL'} | {'pass' if b['temporary_candidate_execution']['equal_ordered_and_received_precision_regressions_pass'] else 'FAIL'} |",
        f"| Genuine differences still flagged | {'pass' if b['original_execution']['genuine_difference_regressions_pass'] else 'FAIL'} | {'pass' if b['temporary_candidate_execution']['genuine_difference_regressions_pass'] else 'FAIL'} |",
        "",
        "**Not a merged application fix:** Rails models, DB integration and "
        "project test suite were not run; maintainers must adjudicate acceptable "
        "unit and decimal precision semantics.","",
        "## External conversion gate","",
        "Both are independently reported public problems, not paid work orders. "
        "Source and runtime checks support a credible contribution proposal, "
        "but do not validate rights, financing, deployment or user outcomes. "
        "Upstream repositories remain untouched.","",
    ]
    return "\n".join(lines)

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(prog="cite-refinery-original-component-trials")
    p.add_argument("--checkouts",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    a=p.parse_args(argv)
    repo_root=Path(__file__).resolve().parents[2]
    report=run(a.checkouts,repo_root)
    a.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    a.markdown.write_text(markdown(report))
    print("Original functions executed: 2; full app integration: 0; local experimental patches: 2 (map patch incomplete)")
    return 0

if __name__=="__main__":raise SystemExit(main())
