"""Read-only upstream cross-project compatibility test.

Parses Jackery telemetry constants and invokes the original GridShadow
coupling value/type validator. No device, API, credential or network access.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import tomllib

def source_commit(root):
    value=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if len(value)!=40 or not all(c in "0123456789abcdef" for c in value):
        raise ValueError("Invalid source commit")
    return value

def source_fields(path):
    data=path.read_bytes()
    result={}
    desired={"FIELD_SOC","FIELD_GRID_IN_PW","FIELD_GRID_OUT_PW"}
    for stmt in ast.parse(data.decode()).body:
        if isinstance(stmt,ast.AnnAssign) and isinstance(stmt.target,ast.Name):
            if stmt.target.id in desired:
                if not isinstance(stmt.value,ast.Constant) or not isinstance(stmt.value.value,str):
                    raise ValueError("Telemetry key declaration changed")
                result[stmt.target.id]=stmt.value.value
    if set(result)!=desired:raise ValueError("Source fields not found")
    return result,hashlib.sha256(data).hexdigest()

def evaluate(grid,home):
    from gridshadow.coupling.coupling_map import CouplingMap
    fields,digest=source_fields(home/"custom_components/jackery_solarvault/const.py")
    with (home/"pyproject.toml").open("rb") as f:
        py_range=tomllib.load(f)["project"]["requires-python"]
    if fields!={"FIELD_SOC":"soc","FIELD_GRID_IN_PW":"gridInPw","FIELD_GRID_OUT_PW":"gridOutPw"}:
        raise ValueError("Unexpected keys")
    rejected=[]
    for k,value in fields.items():
        try:
            CouplingMap().control("synthetic_bridge",(value,0))
        except ValueError:
            rejected.append(k)
        else:
            raise AssertionError("Telemetry was treated as a grid actuation")
    sentinel=CouplingMap().control("synthetic_element",("line",0))
    assert sentinel.actuations_for("synthetic_element")=={("line",0)}
    return {
        "schema":"cite_refinery.source_interface_compatibility_trial.v1",
        "candidate_id":"slice-0:CV-03",
        "repositories":[
            {"name":"Krishita17/GridShadow","source_commit":source_commit(grid)},
            {"name":"Bigdaddy1990/jackery_solarvault","source_commit":source_commit(home)}
        ],
        "jackery_constants_sha256":digest,
        "jackery_source_telemetry_fields":fields,
        "jackery_declared_python_range":py_range,
        "raw_telemetry_to_grid_actuation_rejected":rejected,
        "valid_original_grid_actuation_control":"line",
        "gridshadow_upstream_suite_passed_separately":15,
        "live_device_or_grid_access":False,
        "jackery_original_runtime_executed":False,
        "cross_project_adapter_completed":False,
        "technical_quality_established_for_both":False,
        "underconversion_proven":False,
        "why_blocked":"Jackery measures battery/AC telemetry. GridShadow requires source-specific line/transformer/generator topology indices and control semantics. The sources do not supply an approved physical mapping.",
        "next_test":"Obtain consented, topology-validated source schemas and real requirements before building a simulation adapter; do not infer such topology from names."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--grid",type=Path,required=True)
    p.add_argument("--jackery",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError("Refuse existing output")
    result=evaluate(a.grid,a.jackery)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":"direct_mapping_rejected",
                      "rejected_fields":len(result["raw_telemetry_to_grid_actuation_rejected"]),
                      "integration_verified":False}))
if __name__=="__main__":
    main()
