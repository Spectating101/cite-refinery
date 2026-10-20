"""Independent published comparator data/code reproducibility metadata.

Does NOT conflate a 2018-2019 Italy/Ukraine dog survey with a 2021-2025
Sri Lanka intervention or claim to rerun the paper's fitted Stan posterior.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _csv(path):
    with Path(path).open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def _version(path):
    p=subprocess.run(["git","-C",str(path),"rev-parse","HEAD"],capture_output=True,text=True,check=True)
    value=p.stdout.strip()
    if len(value)!=40:raise ValueError("Expected pinned Git commit")
    return value


def audit_published_dog_repo(root):
    root=Path(root).resolve()
    raw=root/"data/PRDMR.csv"
    processed=root/"output/Population_size.csv"
    rscript=root/"R/01_Bayesian_PCRD_model.R"
    stan=root/"R/hmm-three-state-dapx-two-pop.stan"
    if any(not f.exists() for f in (raw,processed,rscript,stan)):
        raise ValueError("Not the expected population dynamics research dataset/code repository")
    rows=_csv(raw);est=_csv(processed)
    if not rows or not est:raise ValueError("Empty research files")
    visits=[f"P{period}S{survey}" for period in range(1,6) for survey in range(1,4)]
    if not {"Study Area","ID","Sex",*visits} <= set(rows[0]):
        raise ValueError("Missing study identifier/mark-resight repeated survey fields")
    if not {"Study_location","Study_site","Mean","Lower_95CI","Upper_95CI"} <= set(est[0]):
        raise ValueError("Missing estimated abundance output fields")
    ids=[row["ID"] for row in rows]
    if len(set(ids))!=len(rows):raise ValueError("Duplicate individual dog ID")
    if any(row[visit] not in {"0","1","NA",""} for row in rows for visit in visits):
        raise ValueError("Unexpected survey coding; do not silently coerce")
    captures={v:sum(row[v]=="1" for row in rows) for v in visits}
    if not any(captures.values()):raise ValueError("No resighting encounters")
    bad=[]
    for i,row in enumerate(est,2):
        lo,mean,hi=(float(row[x]) for x in ("Lower_95CI","Mean","Upper_95CI"))
        if not lo<=mean<=hi:bad.append(i)
    if bad:raise ValueError("Population-size posterior interval ordering invalid")
    filelist=[raw,processed,rscript,stan,root/"R/02_Extracting_parameter_estimates.R",
              root/"R/03_generate_figure_pop_size.R"]
    digest={str(p.relative_to(root)):_sha(p) for p in filelist if p.is_file()}
    is_licensed=any((root/name).is_file() for name in ("LICENSE","LICENSE.md","COPYING"))
    return {
        "schema":"cite_refinery.open_comparator_reproducibility.v1",
        "repository":"https://github.com/lauren-smith-r/Smith-et-al-Population-dynamics-free-roaming-dogs",
        "commit":_version(root),"source_study_doi":"10.1371/journal.pone.0266636",
        "location_and_period":"Pescara Italy + Lviv Ukraine; 2018-2019 (not Anuradhapura Sri Lanka)",
        "raw_identified_dogs":len(rows),
        "unique_dog_ids":len(set(ids)),
        "study_area_counts":dict(sorted(Counter(row["Study Area"] for row in rows).items())),
        "capture_observations_by_visit":captures,
        "raw_sighting_events":sum(captures.values()),
        "population_estimate_rows":len(est),
        "population_estimate_localities":dict(sorted(Counter(row["Study_location"] for row in est).items())),
        "invalid_estimate_intervals":len(bad),
        "files_sha256":digest,
        "bayesian_model_code_present":True,
        "posterior_refitted":False,
        "standalone_repository_license_detected":is_licensed,
        "inferences":[
            "R scripts, Stan model, encounter histories, and posterior-derived population estimates exist at a pinned public commit.",
            "Descriptive counts and intervals can be independently recomputed from published CSVs.",
            "Posterior results were NOT refitted from raw encounters; requires model runtime, exact dependency versions and convergence assessment.",
            "This is a separate country/time/population comparator, NOT raw data for the 2026 Anuradhapura paper.",
            "Before republishing dataset files, check upstream license; do not bundle them with this report.",
        ],
    }
