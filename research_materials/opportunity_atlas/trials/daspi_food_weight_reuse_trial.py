"""Bounded noncommercial capability-transfer experiment.

Uses unchanged original DaSPi GageStudyModel / GageRnRModel to evaluate
synthetic food-redistribution intake weighing. Demonstrates detection of
injected operator-specific bias, NOT actual food operator demand or benefit.
Run with installed original Daspi package at a pinned source checkout.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

def source_head(path: Path) -> str:
    result=subprocess.check_output(["git","-C",str(path),"rev-parse","HEAD"],text=True).strip()
    if len(result)!=40 or any(c not in "0123456789abcdef" for c in result):
        raise ValueError("Original DaSPi source commit is missing")
    return result

def generate(biased:bool):
    import pandas as pd
    known_masses=(8.4,9.0,9.6,10.3,10.8,11.2,11.9,12.4)
    operators=("intake_A","intake_B","intake_C")
    injected=(-0.55,0.0,0.55) if biased else (0.0,0.0,0.0)
    rows=[]
    for i,mass in enumerate(known_masses):
        for j,operator in enumerate(operators):
            for replicate in range(3):
                noise=0.055*((((i+1)*3+j+replicate*2)%5)-2)
                rows.append({"parcel":f"batch_{i+1:02d}",
                             "worker":operator,"weight_kg":mass+injected[j]+noise})
    return pd.DataFrame(rows),known_masses,operators,injected

def analyze(biased:bool):
    import pandas as pd
    import daspi as dsp
    sample,truth,workers,offsets=generate(biased)
    cal=pd.DataFrame({
        "measured":[10.0+0.03*((j%5)-2) for j in range(25)],
        "reference":[10.0]*25
    })
    study=dsp.GageStudyModel(cal,"measured","reference",
                             u_cal=0.02,tolerance=2.0,resolution=0.01)
    original=dsp.GageRnRModel(sample,"weight_kg","parcel",study,u_av="worker")
    frame=original.anova()
    p=float(frame.loc["worker","p"])
    worker_ss=float(frame.loc["worker","SS"])
    residual_ss=float(frame.loc["Residual","SS"])
    baseline=sample.groupby("parcel")["weight_kg"].mean()
    measured=sample.groupby(["parcel","worker"])["weight_kg"].mean()
    threshold=10.0
    baseline_mistakes=sum(int((baseline[f"batch_{i+1:02d}"]>=threshold)!=(truth[i]>=threshold))
                          for i in range(len(truth)))
    exposed=[]
    wrong=0
    for i,mass in enumerate(truth):
        classifications=[measured[f"batch_{i+1:02d}",w]>=threshold for w in workers]
        wrong+=sum(int(c!=(mass>=threshold)) for c in classifications)
        if len(set(classifications))>1:
            exposed.append(f"batch_{i+1:02d}")
    max_baseline_error=max(abs(float(baseline[f"batch_{i+1:02d}"])-mass)
                           for i,mass in enumerate(truth))
    return {
        "case":"injected_worker_bias" if biased else "negative_control_no_worker_bias",
        "synthetic_only":True,
        "parcels":len(truth),"operators":len(workers),"readings":len(sample),
        "injected_operator_offsets_kg":list(offsets),
        "threshold_kg":threshold,
        "naive_pooled_mean_wrong_parcel_classifications":baseline_mistakes,
        "naive_max_parcel_pooled_mean_error_kg":round(max_baseline_error,6),
        "single_operator_parcel_classification_errors":wrong,
        "single_operator_parcel_comparisons":len(truth)*len(workers),
        "operator_specific_threshold_disagreement_lots":exposed,
        "upstream_daspi_worker_anova_p":p,
        "upstream_daspi_worker_sum_of_squares":worker_ss,
        "upstream_daspi_residual_sum_of_squares":residual_ss,
        "detected_operator_effect_p_below_001":p<0.01,
        "decision":"audit_operator_and_scale_calibration_before_using_individual_weight_entries"
                   if p<0.01 else "no_operator_effect_detected_on_this_synthetic_fixture",
    }

def evaluate(source:Path):
    import daspi
    import pandas,numpy,scipy,statsmodels
    original_file=Path(daspi.__file__).resolve()
    # An editable installed package must point at the exact pinned checkout.
    if not original_file.is_relative_to(source.resolve()):
        raise ValueError("DaSPi model was not loaded from specified original repository")
    baseline=analyze(False)
    injected=analyze(True)
    assert baseline["detected_operator_effect_p_below_001"] is False
    assert injected["detected_operator_effect_p_below_001"] is True
    assert baseline["single_operator_parcel_classification_errors"]==0
    assert injected["naive_pooled_mean_wrong_parcel_classifications"]==0
    assert injected["single_operator_parcel_classification_errors"]==2
    assert len(injected["operator_specific_threshold_disagreement_lots"])==2
    return {
        "schema":"cite_refinery.cross_domain_conversion_functional_trial.v1",
        "candidate_id":"slice-2:CV-01",
        "source_repository":"j4ggr/DaSPi",
        "source_commit":source_head(source),
        "source_import_path":str(original_file.relative_to(source.resolve())),
        "source_license_from_original_file":"BSD-3-Clause",
        "original_license_sha256":hashlib.sha256((source/"LICENSE").read_bytes()).hexdigest(),
        "original_model_used":"DaSPi.GageStudyModel + DaSPi.GageRnRModel + original ANOVA",
        "dependency_versions":{
            x.__name__:x.__version__ for x in (pandas,numpy,scipy,statsmodels)
        },
        "synthetic_food_workflow":"food redistribution intake parcel weights, three fictional workers, repeated scale readings",
        "baseline_policy":"pooled averages per parcel without explicitly estimating worker/operator variation",
        "upstream_scoped_test_suite":"tests/anova_model_test.py -k GageStudyModel or GageRnRModel",
        "upstream_scoped_test_outcome":"run separately and attach verified test receipt",
        "biased_fixture":injected,
        "negative_control":baseline,
        "synthetic_operator_problem_detected_and_control_passed":True,
        "improvement_over_naive_pooling":"DaSPi detects an injected operator effect even when pooled parcel means classify all parcels correctly and conceal operator-specific threshold errors",
        "new_algorithm_created":False,
        "new_field_deployment_verified":False,
        "original_repo_modified":False,
        "dataset_is_real":False,
        "adoption_or_underconversion_proven":False,
        "practical_value_realized":False,
        "falsification_next":"Test against independently collected consented multi-worker repeated weighings; compare actual interventions and decision errors. Check whether this analysis is already routine in recipient organizations."
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--original-daspi",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():raise ValueError("Refuse to overwrite positive trial evidence")
    result=evaluate(args.original_daspi)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({
        "scenario":"synthetic_food_weight_quality",
        "biased_operator_p":result["biased_fixture"]["upstream_daspi_worker_anova_p"],
        "negative_control_operator_p":result["negative_control"]["upstream_daspi_worker_anova_p"],
        "single_operator_threshold_errors":result["biased_fixture"]["single_operator_parcel_classification_errors"],
        "actual_adoption_verified":False
    },indent=2))

if __name__=="__main__":
    main()
