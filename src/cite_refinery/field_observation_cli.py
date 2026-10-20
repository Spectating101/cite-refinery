"""Assess field data quality without estimating dog abundance or causal effects."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .field_observation_contract import assess,digest
from .field_observation_synthetic import build_examples

def main(argv=None):
    p=argparse.ArgumentParser(prog="cite-refinery-field-audit")
    p.add_argument("--input",type=Path,help="Approved privacy-minimized JSON observation dataset")
    p.add_argument("--out",type=Path,help="Quality summary output; no raw records or owner data")
    p.add_argument("--examples",type=Path,help="Create clearly labeled entirely synthetic fixtures")
    args=p.parse_args(argv)
    if bool(args.examples)==bool(args.input):
        p.error("Provide exactly one of --input or --examples")
    if args.examples:
        if args.out:p.error("--out is not used with --examples")
        manifest=build_examples(args.examples)
        print(json.dumps(manifest,indent=2))
        return
    if not args.out:p.error("--out is required with --input")
    payload=json.loads(args.input.read_text(encoding="utf-8"))
    summary=assess(payload)
    summary["source_dataset_digest"]=digest(payload)
    summary["data_retention"]="Input records never copied into the output readiness report"
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"input":str(args.input),"out":str(args.out),
                      "synthetic":summary["synthetic"],
                      "test_status":summary["test_status"],
                      "identified_mechanism":False},indent=2))

if __name__=="__main__":
    main()
