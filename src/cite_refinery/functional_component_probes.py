"""Reproducible, bounded functional and configuration trials of *existing* OSS leads.

Only evaluate upstream source snapshots the operator has independently cloned
into a scratch research directory; never download, edit, install, auto-patch, or
execute the entire remote project. Two small imported modules have been
manually inspected and are executed on synthetic inputs; ESPHome is YAML-only
because no board/compiler is available. These trials are NOT an execution sandbox.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime,timezone
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from .execution import SubprocessExecutor

SCHEMA="cite_refinery.functional_component_trials.v1"
REVISIONS={
    "lingrany__EverBatt-LFP-Recycling-Analysis":"246c4d478f9ceb05c580856720ca56a66064e205",
    "WeixuanZ__flood-warning-system":"c1c7facf2c5577a155edd93a0b7279ad7630518c",
    "ajlongshanks__co2_esphome":"d1b3c500ae475e3dcfef6e5dbb38279cdc267708",
}

def _source(repo_root:Path,key:str)->dict[str,Any]:
    expected=REVISIONS[key]
    folder=repo_root/key
    if not folder.is_dir() or not (folder/".git").exists():
        raise ValueError("source repository snapshot absent: "+key)
    commit=subprocess.run(["git","-C",str(folder),"rev-parse","HEAD"],
                          capture_output=True,text=True,timeout=12,check=True).stdout.strip()
    if commit != expected:
        raise ValueError(f"source revision changed {key}: {commit} != {expected}")
    return {
        "directory":folder,
        "git_commit":commit,
        "source_url":"https://github.com/"+key.replace("__","/",1)+"/tree/"+commit,
        "test_isolated_from_authority":True,
    }

def check(name:str,contract:str,status:str, *,
          actual:Any=None,expected:Any=None,note:str="",critical:bool=True)->dict[str,Any]:
    if status not in {"pass","fail","blocked","not_tested"}:
        raise ValueError("invalid test status")
    return {
        "name":name,"requirement":contract,"status":status,"critical":critical,
        "actual":actual,"expected":expected,
        "interpretation":note,
        "claim_authority":"synthetic_code_or_static_configuration_probe_only",
    }

def _load_file_module(file:Path,name:str)->Any:
    spec=importlib.util.spec_from_file_location(name,file)
    if spec is None or spec.loader is None:
        raise ValueError("upstream Python module loader unavailable")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def battery(repo_root:Path)->dict[str,Any]:
    s=_source(repo_root,"lingrany__EverBatt-LFP-Recycling-Analysis")
    folder=s["directory"]
    # These upstream functions have been inspected. Third-party Python imports
    # are not a security sandbox; run only on authorized separate test machine.
    m=_load_file_module(folder/"lfp_analysis_verified.py","upstream_lfp_20261021")
    t=10000
    cases=[]
    for method in ("Pyro","Hydro","Direct"):
        base=m.analyze_method(method,t,m.PRICES_2019,0)
        inbound=m.analyze_method(method,t,m.PRICES_2019,-2)
        outbound=m.analyze_method(method,t,m.PRICES_2019,1)
        required_difference=t*1000
        actual_difference=round(base["profit"]-outbound["profit"],2)
        cases.append(check(
            method.lower()+"_positive_fee_accounting",
            "A positive gate fee ($1/kg paid to obtain feedstock) must reduce annual profit by mass in kg times $1.",
            "pass" if math.isclose(actual_difference,required_difference,abs_tol=1e-3) else "fail",
            actual={"profit_usd_fee_zero":round(base["profit"],2),
                    "profit_usd_fee_positive_one":round(outbound["profit"],2),
                    "actual_profit_reduction_usd":actual_difference},
            expected={"profit_reduction_usd":required_difference},
            note="Upstream --battery-fee CLI says negative means recycler is paid. This result checks the reverse paid-fee direction using its own convention.",
        ))
        incoming=inbound["profit"]-base["profit"]
        cases.append(check(
            method.lower()+"_negative_gate_fee_income",
            "Negative gate fee -$2/kg should increase revenue/profit by $2/kg at unchanged throughput.",
            "pass" if math.isclose(incoming,t*1000*2,abs_tol=1e-3) else "fail",
            actual={"profit_increase_usd":round(incoming,2)},
            expected={"profit_increase_usd":t*1000*2},
            note="Verifies the supported positive-income side of the gate-fee handling.",
        ))
    cases.append(check(
        "localized_hazard_control_and_pilot_yield",
        "Economics must incorporate site-specific safety/compliance costs and pilot recovery yields.",
        "not_tested",
        actual="Original default parameters only; no field, regulator, or plant records provided.",
        expected="Local project feedstock, compliance CAPEX/OPEX, verified yield and buyer prices.",
        note="The upstream model has parameters but no verified local inputs; a synthetic profit output cannot establish investment economics.",
    ))
    return {
        "mechanism_id":"mechanism:battery_recycling_economics",
        "asset_id":"github:lingrany/EverBatt-LFP-Recycling-Analysis",
        "source":{k:v for k,v in s.items() if k!="directory"},
        "technology_type":"economic_scenario_model",
        "source_entry_point":"lfp_analysis_verified.py:analyze_method",
        "execution":"actual_upstream_python_calculation_synthetic_input",
        "cases":cases,
        "relevant_scope":"Route/fee scenario computation; not recycler permit, plant profitability, safety or observed performance.",
        "commercial_reuse_permission":"MIT file in checked repo; third-party workbook/data/embedded assets and derivative license compatibility not independently assessed.",
    }

def flood(repo_root:Path)->dict[str,Any]:
    s=_source(repo_root,"WeixuanZ__flood-warning-system")
    folder=s["directory"]
    old=list(sys.path)
    try:
        sys.path.insert(0,str(folder))
        from floodsystem.station import MonitoringStation
        from floodsystem.flood import stations_level_over_threshold,stations_highest_rel_level
        def station(name:str,low:float=0.0,high:float=1.0,value:float|None=None):
            a=MonitoringStation(name,name,name,(25.0,121.0),(low,high),"synthetic","synthetic")
            a.latest_level=value
            return a
        high=station("high",value=1.60)
        normal=station("normal",value=0.25)
        missing=station("missing",value=None)
        invalid_range=station("invalid",low=0,high=0,value=1.6)
        nan=station("nan",value=float("nan"))
        observed=stations_level_over_threshold(
            [normal,missing,invalid_range,high],0.5)
        actual_ids=[x.name for x,_ in observed]
        cases=[
            check("threshold_selection",
                  "Elevated water-level fractions above 0.5 are selected, without normal/missing/invalid stations.",
                  "pass" if actual_ids==["high"] else "fail",
                  actual=actual_ids,expected=["high"],
                  note="Synthetic values exercise the upstream station normalization and risk filter; thresholds are not calibrated for real rivers."),
            check("missing_level_handling",
                  "Missing station levels return no risk fraction rather than a fabricated warning.",
                  "pass" if missing.relative_water_level() is None else "fail",
                  actual=None if missing.relative_water_level() is None else str(missing.relative_water_level()),
                  expected=None),
            check("invalid_typical_range_handling",
                  "Zero-width typical range is rejected.",
                  "pass" if invalid_range.relative_water_level() is None else "fail",
                  actual=None if invalid_range.relative_water_level() is None else str(invalid_range.relative_water_level()),
                  expected=None),
        ]
        rel=nan.relative_water_level()
        selected=stations_highest_rel_level([high,nan],2)
        accepted=nan in selected
        cases.append(check(
            "nonfinite_sensor_level_is_excluded",
            "NaN water-level readings must not be returned as candidates for an operational highest-risk list.",
            "fail" if accepted or (rel is not None and not math.isfinite(rel)) else "pass",
            actual={"nan_relative_value":str(rel),"nan_in_ranked_stations":accepted},
            expected={"nan_relative_value":None,"nan_in_ranked_stations":False},
            note="Nonfinite measurements are invalid telemetry; passing them into risk sorting can mislead downstream processing.",
        ))
        cases.append(check(
            "local_warning_distribution_and_health_outcomes",
            "A forecast/threshold module must be paired with validated local alert delivery and downstream response.",
            "not_tested",
            actual="Synthetic UK-style MonitoringStation data only.",
            expected="Site-calibrated telemetry, uncertainty, actual recipient alerts, response timestamps and health outcomes.",
            note="No live station feed, dissemination authority or health endpoint was tested.",
        ))
    finally:
        sys.path[:]=old
        for pkg in ("floodsystem.station","floodsystem.flood","floodsystem.utils","floodsystem"):
            sys.modules.pop(pkg,None)
    return {
        "mechanism_id":"mechanism:flood_warning_to_impact",
        "asset_id":"github:WeixuanZ/flood-warning-system",
        "source":{k:v for k,v in s.items() if k!="directory"},
        "technology_type":"hydrological_station_threshold_module",
        "source_entry_point":"floodsystem.station, floodsystem.flood",
        "execution":"actual_upstream_python_code_synthetic_station_fixtures",
        "cases":cases,
        "relevant_scope":"Station threshold/ranking utilities; not weather forecast skill, alert delivery, local calibration or reduced harm.",
        "commercial_reuse_permission":"MIT license in checked repo; external data provider and operational regulatory requirements unresolved.",
    }

def co2(repo_root:Path)->dict[str,Any]:
    s=_source(repo_root,"ajlongshanks__co2_esphome")
    folder=s["directory"]
    conf=folder/"co2sensor.yaml"
    text=conf.read_text(encoding="utf-8")
    import yaml
    yaml_valid=True
    parse_error=None
    try:yaml.safe_load(text)
    except yaml.YAMLError as exc:
        yaml_valid=False
        parse_error=str(exc)[:330]
    declared=set(re.findall(r"(?m)^\s+id:\s*(face_[A-Za-z0-9_]+)\s*$",text))
    used=set(re.findall(r"\bid\((face_[A-Za-z0-9_]+)\)",text))
    missing=sorted(used-declared)
    has_license=any(folder.glob("LICENSE*")) or any(folder.glob("COPYING*"))
    cases=[
        check("esphome_yaml_syntax",
              "Configuration must parse as valid YAML before considering firmware build.",
              "pass" if yaml_valid else "fail",
              actual={"yaml_valid":yaml_valid,"parse_error":parse_error},
              expected={"yaml_valid":True},
              note="PyYAML syntax parser, NOT ESPHome schema validator or firmware compiler."),
        check("display_image_identifiers",
              "Every face image referenced by the display lambda must be declared as a configuration image.",
              "pass" if not missing else "fail",
              actual={"undeclared_image_ids":missing},expected={"undeclared_image_ids":[]},
              note="Static reference check; not an ESPHome C++ lambda compilation."),
        check("licensing_provenance",
              "A verifiable distribution/reuse license must be established before commercial component reuse.",
              "pass" if has_license else "blocked",
              actual={"license_file_detected":has_license},
              expected={"license_file_detected":True},
              note="No LICENSE/COPYING file in checked snapshot. This is a documentation gap, not a definitive legal ruling."),
        check("firmware_compile_and_sensor_calibration",
              "Compile the configuration, flash approved hardware, calibrate SCD30 readings against a reference and test sensor faults.",
              "not_tested",
              actual="No ESPHome compiler, ESP32/T-Display hardware, or physical calibration instrument in this trial.",
              expected="Successful current-version ESPHome compile, hardware test and calibration trace.",
              note="Static syntax failure already blocks firmware testing; hardware/clinical effect cannot be inferred."),
    ]
    return {
        "mechanism_id":"mechanism:classroom_ventilation_outcomes",
        "asset_id":"github:ajlongshanks/co2_esphome",
        "source":{k:v for k,v in s.items() if k!="directory"},
        "technology_type":"esphome_sensor_configuration",
        "source_entry_point":"co2sensor.yaml",
        "execution":"static_yaml_syntax_and_reference_inspection_only_not_firmware_execution",
        "cases":cases,
        "relevant_scope":"Configuration plausibility, not actual CO2 sensing, school ventilation or respiratory outcome.",
        "commercial_reuse_permission":"No license file detected in pinned repository; clarify rights before reuse.",
    }

def aggregate(probes:list[dict[str,Any]])->dict[str,Any]:
    if not 2<=len(probes)<=12:
        raise ValueError("bounded cross-domain sample required")
    assets=[p["asset_id"] for p in probes]
    if len(assets)!=len(set(assets)):
        raise ValueError("duplicate asset")
    records=[case for p in probes for case in p["cases"]]
    counts=dict(Counter(x["status"] for x in records))
    return {
        "schema":SCHEMA,
        "observed_at":datetime.now(timezone.utc).isoformat(),
        "probes":probes,"test_case_counts":counts,
        "count_is_not_performance_estimate":True,
        "technical_fit_confirmed":False,
        "real_deployment_confirmed":False,
        "scientific_intervention_outcome_confirmed":False,
        "commercial_eligibility_confirmed":False,
        "graph_status_promotion_allowed":False,
        "development_source_holdout_touched":False,
        "scope":"Cloned checked upstream revisions; synthetic calculation/risk logic and static YAML only; no device calibration, live flood forecasts, academic effect estimation or independent business demand.",
        "execution_safety":"Manual source review before import; research scratch clones and local interpreter on authorized device, NOT OS-level network/isolation sandbox.",
    }


PROBE_REGISTRY = {
    "battery": battery,
    "flood": flood,
    "co2": co2,
}


class SubprocessProbeRunner:
    """Execute functional component probes in an isolated child process and optionally record Cite-Refinery rrun/rexp provenance."""

    def __init__(self, executor: SubprocessExecutor | None = None, timeout_seconds: float = 60.0) -> None:
        self.executor = executor or SubprocessExecutor()
        self.timeout_seconds = timeout_seconds

    def invocation_spec(self) -> dict[str, Any]:
        src_root = str(Path(__file__).resolve().parents[1])
        return {
            "argv": [
                sys.executable,
                "-c",
                f"import sys; sys.path.insert(0, {src_root!r}); from cite_refinery.functional_component_probes import main; raise SystemExit(main(['--worker-stdin']))",
            ],
            "input_mode": "json_stdin",
            "timeout_seconds": self.timeout_seconds,
        }

    def run_probe_isolated(
        self,
        scratch_root: Path,
        probe_name: str,
        *,
        revision_overrides: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if probe_name not in PROBE_REGISTRY:
            raise ValueError(f"unknown functional probe: {probe_name}")
        res = self.executor.execute(
            self.invocation_spec(),
            {
                "scratch_root": str(scratch_root),
                "probe": probe_name,
                "revision_overrides": revision_overrides or {},
            },
        )
        if res.status != "succeeded" or not isinstance(res.output, dict) or "asset_id" not in res.output:
            detail = (res.stderr or res.stdout or "isolated probe failed").strip()
            raise RuntimeError(f"isolated subprocess probe {probe_name} failed: {detail}")
        probe = dict(res.output)
        probe["isolated_subprocess"] = True
        probe["duration_ms"] = res.duration_ms
        return probe

    def run_into_project(
        self,
        app: Any,
        project_id: str,
        scratch_root: Path,
        *,
        probes: list[str] | None = None,
        revision_overrides: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        selected = probes or ["battery", "flood", "co2"]
        results: list[dict[str, Any]] = []
        for name in selected:
            if name not in PROBE_REGISTRY:
                raise ValueError(f"unknown functional probe: {name}")
            cap = app.refinery.register_capability(
                project_id=project_id,
                name=f"Functional probe: {name}",
                description=f"Bounded synthetic/static component probe for {name}",
                tags=["functional_probe", name],
            )
            impl = app.refinery.register_implementation(
                capability_id=cap.id,
                project_id=project_id,
                provider="subprocess",
                invocation=self.invocation_spec(),
            )
            run = app.invoke(
                project_id,
                impl.id,
                input_data={
                    "scratch_root": str(scratch_root),
                    "probe": name,
                    "revision_overrides": revision_overrides or {},
                },
            )
            if run.status != "succeeded" or not isinstance(run.output, dict) or "asset_id" not in run.output:
                raise RuntimeError(f"project subprocess probe {name} failed (run {run.id}): {run.stderr}")
            probe_data = dict(run.output)
            counts = Counter(c["status"] for c in probe_data["cases"])
            has_defect_or_gap = bool(counts["fail"] or counts["blocked"] or counts["not_tested"])
            verdict = "failed" if has_defect_or_gap else "passed"
            exp = app.add_experiment(
                project_id,
                name=f"Component requirement trial: {probe_data['asset_id']}",
                method=probe_data["execution"],
                result=f"counts={dict(counts)}; promotion_allowed=False",
                verdict=verdict,
                metrics={
                    "pass": counts.get("pass", 0),
                    "fail": counts.get("fail", 0),
                    "blocked": counts.get("blocked", 0),
                    "not_tested": counts.get("not_tested", 0),
                },
                run_ids=[run.id],
            )
            probe_data["refinery_provenance"] = {
                "project_id": project_id,
                "capability_id": cap.id,
                "implementation_id": impl.id,
                "run_id": run.id,
                "experiment_id": exp.id,
                "experiment_verdict": verdict,
            }
            results.append(probe_data)
        return aggregate(results)

def render_md(data:dict[str,Any])->str:
    if data.get("schema")!=SCHEMA:raise ValueError("unrecognized trial product")
    out=["# Functional component verification: executable evidence vs operational promise","",
         "Probes use original pinned upstream files in a separate research scratch directory. "
         "A **pass** demonstrates only the specific synthetic requirement. A **fail** "
         "is a reproducible gap in that bounded trial; **blocked** means missing "
         "prerequisite/evidence and **not tested** means no field result. "
         "No external code is copied into Cite–Refinery.",""]
    for row in data["probes"]:
        out+=["## ["+row["asset_id"].removeprefix("github:")+"]("+row["source"]["source_url"]+")", "",
              "**Three-layer problem:** "+row["mechanism_id"]+"; **execution:** "+row["execution"],"",
              "| Requirement check | Result | Measured behavior / limitation |",
              "|---|---|---|"]
        for x in row["cases"]:
            actual=json.dumps(x["actual"],ensure_ascii=False,sort_keys=True)
            out+=["| "+x["name"].replace("|","/")+" | **"+x["status"].upper()+"** | "+
                  actual.replace("|","/")[:200]+" |"]
        out+=["","**Scope boundary:** "+row["relevant_scope"],"",
              "**Reuse boundary:** "+row["commercial_reuse_permission"],"",
              "### Interpretation",""]
        for x in row["cases"]:
            if x["status"] in ("fail","blocked","not_tested"):
                out+=["- **"+x["name"]+"** ("+x["status"]+"): "+x["interpretation"]]
        out.append("")
    out+=["## Evidence gate","",
          "These trials do **not** establish a product fit for the complete operational need, "
          "an independently replicated research mechanism, a safe installation, "
          "or a viable commercial conversion. In particular, an apparent profit "
          "from a model with a failed fee-cost accounting invariant must not be "
          "presented as the project's economic value.",""]
    return "\n".join(out)

def main(argv:list[str]|None=None)->int:
    if argv is None and "--worker-stdin" in sys.argv[1:] or (argv is not None and "--worker-stdin" in argv):
        payload = json.loads(sys.stdin.read() or "{}")
        probe_name = payload.get("probe")
        scratch_root = Path(payload.get("scratch_root", ""))
        overrides = payload.get("revision_overrides") or {}
        if isinstance(overrides, dict):
            for k, v in overrides.items():
                if k in REVISIONS and isinstance(v, str) and len(v) == 40:
                    REVISIONS[k] = v
        if probe_name not in PROBE_REGISTRY:
            raise ValueError(f"unknown worker probe: {probe_name}")
        out = PROBE_REGISTRY[probe_name](scratch_root)
        print(json.dumps(out, ensure_ascii=False), flush=True)
        return 0
    p=argparse.ArgumentParser(prog="cite-refinery-functional-probes")
    p.add_argument("--scratch-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    p.add_argument("--isolated-subprocess",action="store_true",help="Run each probe in an isolated child process")
    args=p.parse_args(argv)
    if args.isolated_subprocess:
        runner=SubprocessProbeRunner()
        probes=[runner.run_probe_isolated(args.scratch_root,name) for name in ("battery","flood","co2")]
    else:
        probes=[battery(args.scratch_root),flood(args.scratch_root),co2(args.scratch_root)]
    result=aggregate(probes)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    args.markdown.write_text(render_md(result),encoding="utf-8")
    for row in result["probes"]:
        print(row["asset_id"],Counter(x["status"] for x in row["cases"]),flush=True)
    print("No status promotion allowed",flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
