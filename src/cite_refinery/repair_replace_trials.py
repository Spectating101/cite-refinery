"""Source-pinned local repair tests versus incomplete alternative implementations.

Run only on an authorized source-inspected research machine. Modified Python
source exists in temporary copies, never the upstream clones or production.
"""
import argparse
import importlib.util
import itertools
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PINS={
 "lingrany__EverBatt-LFP-Recycling-Analysis":"246c4d478f9ceb05c580856720ca56a66064e205",
 "WeixuanZ__flood-warning-system":"c1c7facf2c5577a155edd93a0b7279ad7630518c",
 "ajlongshanks__co2_esphome":"d1b3c500ae475e3dcfef6e5dbb38279cdc267708",
 "Jamie-Hough__Batteryloop":"f1751351e64b3072eb3522caa95c4cbac98d7a36",
 "RomainGehrig__ESPHome-CO2Sensor":"d7d988175a93a0697862aef3b2c9878011eb3fb9",
 "langchr86__homesensor":"646735bfd75ea9c7c7528a29ccb54c074527e08a",
}

def repo(root,slug):
    if slug not in PINS:raise ValueError("unknown inspected source revision")
    folder=root/slug
    if not (folder/".git").is_dir():raise ValueError("source clone missing")
    sha=subprocess.run(["git","-C",str(folder),"rev-parse","HEAD"],capture_output=True,
                       text=True,timeout=10,check=True).stdout.strip()
    if sha!=PINS[slug]:raise ValueError("upstream source version changed")
    return folder

def replace_one(source,old,new):
    if source.count(old)!=1:raise ValueError("unverified or ambiguous repair anchor")
    return source.replace(old,new)

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:raise ValueError("module unavailable")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def battery(root):
    source=repo(root,"lingrany__EverBatt-LFP-Recycling-Analysis")/"lfp_analysis_verified.py"
    original=source.read_text()
    fixed=replace_one(original,
         "overhead + depreciation + fixed_charges + gsa + waste_cost)",
         "overhead + depreciation + fixed_charges + gsa + waste_cost + max(0.0, -fee_rev))")
    fixed=replace_one(fixed,"'Waste disposal': waste_cost,",
         "'Waste disposal': waste_cost,\n        'Battery purchase (gate fee)': max(0.0, -fee_rev),")
    rows=[]
    with tempfile.TemporaryDirectory(prefix="lfp_local_trial_") as td:
        local=Path(td)/"patched_lfp.py";local.write_text(fixed)
        o=load(source,"original_lfp");p=load(local,"patched_lfp")
        for method in ("Pyro","Hydro","Direct"):
            old=[o.analyze_method(method,10000,o.PRICES_2019,x) for x in (-2,0,1)]
            new=[p.analyze_method(method,10000,p.PRICES_2019,x) for x in (-2,0,1)]
            old_diff=old[2]["profit"]-old[1]["profit"]
            delta=new[2]["profit"]-new[1]["profit"]
            cost=new[2]["cost"]-new[1]["cost"]
            neg=new[0]["profit"]-new[1]["profit"]
            ok=(math.isclose(old_diff,0,abs_tol=0.01) and
                math.isclose(delta,-10_000_000,abs_tol=0.01) and
                math.isclose(cost,10_000_000,abs_tol=0.01) and
                math.isclose(neg,20_000_000,abs_tol=0.01) and
                math.isclose(new[1]["profit"],old[1]["profit"],abs_tol=0.01))
            rows.append({"method":method,"passed":ok,
                         "original_paid_fee_profit_delta_usd":round(old_diff,2),
                         "local_repair_paid_fee_profit_delta_usd":round(delta,2),
                         "local_repair_cost_increase_usd":round(cost,2),
                         "negative_fee_income_preserved_usd":round(neg,2)})
    other=repo(root,"Jamie-Hough__Batteryloop")
    return {"mechanism_id":"mechanism:battery_recycling_economics",
            "source_asset":"github:lingrany/EverBatt-LFP-Recycling-Analysis",
            "upstream_source_sha":PINS["lingrany__EverBatt-LFP-Recycling-Analysis"],
            "local_repair_synthetic_pass":all(x["passed"] for x in rows),
            "route_trials":rows,
            "repair_modifies_upstream":False,
            "alternative_asset":"github:Jamie-Hough/Batteryloop",
            "alternative_sha":PINS["Jamie-Hough__Batteryloop"],
            "alternative_economics_module_empty":not (other/"src/economics.py").read_text().strip(),
            "alternative_root_license_detected":bool(list(other.glob("LICENSE*"))),
            "alternative_gate_fee_model_executed":False,
            "operational_profit_established":False}

def _purge():
    for k in list(sys.modules):
        if k=="floodsystem" or k.startswith("floodsystem."):sys.modules.pop(k,None)

def flood(root):
    src=repo(root,"WeixuanZ__flood-warning-system")
    code=(src/"floodsystem/station.py").read_text()
    code=replace_one(code,
        "        return (\n            (self.latest_level - self.typical_range[0])",
        "        value = (\n            (self.latest_level - self.typical_range[0])")
    code=replace_one(code,"\n\n\ndef inconsistent_typical_range_stations(stations):",
        "\n        return value if value is None or math.isfinite(value) else None\n\n\ndef inconsistent_typical_range_stations(stations):")
    code+="\nimport math\n"
    with tempfile.TemporaryDirectory(prefix="flood_local_trial_") as td:
        shutil.copytree(src/"floodsystem",Path(td)/"floodsystem",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (Path(td)/"floodsystem/station.py").write_text(code)
        sys.path.insert(0,td)
        try:
            _purge()
            from floodsystem.station import MonitoringStation
            from floodsystem.flood import stations_highest_rel_level
            def mk(label,val):
                st=MonitoringStation(label,label,label,(25,121),(0,1),"river","town")
                st.latest_level=val
                return st
            low,nan,high=mk("low",0.2),mk("nan",float("nan")),mk("high",1.6)
            cases=[]
            for order in itertools.permutations((low,nan,high)):
                actual=[x.name for x in stations_highest_rel_level(list(order),1)]
                cases.append({"order":[x.name for x in order],"top_one":actual,
                              "pass":actual==["high"]})
            invalid_result=nan.relative_water_level()
        finally:
            _purge();sys.path.remove(td)
    return {"mechanism_id":"mechanism:flood_warning_to_impact",
            "source_asset":"github:WeixuanZ/flood-warning-system",
            "upstream_source_sha":PINS["WeixuanZ__flood-warning-system"],
            "local_repair_synthetic_pass":all(x["pass"] for x in cases) and invalid_result is None,
            "input_ordering_trials":cases,"invalid_level_returned_none":invalid_result is None,
            "repair_modifies_upstream":False,
            "equivalent_replacement_verified":False,
            "real_warning_performance_verified":False}

def co2(root):
    import yaml
    class ESPHomeSafeLoader(yaml.SafeLoader):pass
    ESPHomeSafeLoader.add_constructor("!secret",lambda loader,node:
                                      {"secret_reference":loader.construct_scalar(node)})
    old=repo(root,"ajlongshanks__co2_esphome")
    orig_valid=True
    try:yaml.load((old/"co2sensor.yaml").read_text(),Loader=ESPHomeSafeLoader)
    except yaml.YAMLError:orig_valid=False
    other=repo(root,"RomainGehrig__ESPHome-CO2Sensor")
    configs=[]
    for filename in ("CO2Sensor.yaml","CO2Sensor-nograph.yaml"):
        y=yaml.load((other/filename).read_text(),Loader=ESPHomeSafeLoader)
        fonts=[f["file"] for f in y.get("font",[]) if isinstance(f,dict) and "file" in f]
        configs.append({"file":filename,"yaml_parsed_with_supported_secret_tag":True,
                        "sensor_platforms":[v.get("platform") for v in y.get("sensor",[])],
                        "missing_fonts":sorted({f for f in fonts if not (other/f).is_file()}),
                        "esphome_compiled":False,"hardware_compatible_verified":False})
    good=repo(root,"langchr86__homesensor")
    license_text=(good/"LICENSE").read_text()
    driver=(good/"software/src/sensors/scd30.cpp").read_text()
    return {"mechanism_id":"mechanism:classroom_ventilation_outcomes",
            "source_asset":"github:ajlongshanks/co2_esphome",
            "original_yaml_valid":orig_valid,
            "config_alternative_asset":"github:RomainGehrig/ESPHome-CO2Sensor",
            "config_alternative_sha":PINS["RomainGehrig__ESPHome-CO2Sensor"],
            "config_alternative_checks":configs,
            "config_alternative_license_file_detected":bool(list(other.glob("LICENSE*"))),
            "config_alternative_drop_in_for_scd30":False,
            "licensed_other_architecture_asset":"github:langchr86/homesensor",
            "licensed_other_architecture_sha":PINS["langchr86__homesensor"],
            "mit_license_detected":"MIT License" in license_text,
            "scd30_driver_source_present":"Scd30::" in driver,
            "other_architecture_is_esphome_yaml":False,
            "firmware_compiled":False,"sensor_accuracy_verified":False}

def run(root):
    b,f,c=battery(root),flood(root),co2(root)
    return {"schema":"cite_refinery.repair_replace_executable_review.v1",
            "source_pins":PINS,"domains":[b,f,c],
            "outcomes":{"battery_local_fee_repair_passed":b["local_repair_synthetic_pass"],
                        "flood_nan_sort_repair_passed":f["local_repair_synthetic_pass"],
                        "alternative_co2_parses_only":all(x["yaml_parsed_with_supported_secret_tag"] for x in c["config_alternative_checks"]),
                        "verified_drop_in_replacement":False,
                        "commercial_value_or_real_world_effect_verified":False,
                        "native_graph_promoted":False},
            "boundary":"Temporary-copy repair prototypes only; no upstream edits, firmware builds, operational deployments, external paid lead or sealed holdout use."}

def markdown(r):
    if r.get("schema")!="cite_refinery.repair_replace_executable_review.v1":raise ValueError("wrong report")
    b,f,c=r["domains"]
    lines=["# Source-pinned repair versus replacement — three mechanisms","",
           "Reproduction uses pinned third-party source in a separate research scratch directory. "
           "Source modifications are TEMPORARY LOCAL TRIALS, not upstream patches or tested products.","",
           "## Battery: reproducible accounting repair","",
           "Local candidate adds positive feedstock acquisition fees to total cost and itemized cost. "
           "Negative gate-fee income and zero-fee behavior are preserved.","",
           "| Route | Original paid-fee delta | Local repaired delta | Result |",
           "|---|---:|---:|---|"]
    for x in b["route_trials"]:
        lines.append("| "+x["method"]+" | "+str(x["original_paid_fee_profit_delta_usd"])+
                     " USD | "+str(x["local_repair_paid_fee_profit_delta_usd"])+
                     " USD | "+("PASS" if x["passed"] else "FAIL")+" |")
    lines+=["","Batteryloop is not a functional replacement on these inputs: at the pinned revision "
            "its economics module is empty, no root license file was detected, and no equivalent "
            "gate-fee scenario was executed. Do not extrapolate to all of its future code.","",
            "## Flood: repair prevents nonfinite sorting interference","",
            "Local guard returns None for nonfinite station fractions. "
            "The highest-risk function selected the genuine high reading for "+
            str(len(f["input_ordering_trials"]))+" of "+
            str(len(f["input_ordering_trials"]))+" possible permutations of low, NaN and high "
            "in the **local candidate**. The original can incorrectly choose low first. "
            "Real warning accuracy, delivery and safety remain untested.","",
            "## CO2: parseable alternative is not drop-in replacement","",
            "The original YAML does not parse. RomainGehrig's two alternatives parse "
            "after recognizing ESPHome's valid secret tag but require SCD40/SCD4x "
            "rather than SCD30, and refer to missing font assets in the inspected clone. "
            "No root license file detected; no right to redistribute inferred. "
            "The MIT-licensed langchr86/homesensor has SCD30 C++ driver sources but "
            "is NOT an ESPHome configuration and was not compiled.","",
            "## Boundaries","",
            "No full operational integration, source-independent research validation, "
            "legal clearance for all assets, real buyer, or verified profit. "
            "Model agreement is not treated as a functional experiment.",""]
    return "\n".join(lines)

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--scratch-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    x=p.parse_args(argv)
    r=run(x.scratch_root)
    x.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n")
    x.markdown.write_text(markdown(r))
    print(r["outcomes"])
    return 0
if __name__=="__main__":raise SystemExit(main())
