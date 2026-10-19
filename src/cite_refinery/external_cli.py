"""Optional external-engine CLI. All outputs are staging artifacts, never auto-ingested."""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from pathlib import Path

from .external_engines import (
    docling_extract, executable_claims_analyze, grobid_extract, openalex_discover,
    paperqa_ask, prov_export_packet,
)
from .external_explorer import export_cytoscape_explorer
from .external_packets import source_lead_packet, relation_proposal_packet
from .external_evidence_audit import verify_source_span, detect_explicit_link_misread


def catalog() -> dict:
    names = {
        "pyalex": "pyalex", "docling": "docling",
        "paperqa": "paperqa", "lightrag": "lightrag",
        "prov": "prov", "httpx": "httpx",
        "cytoscape": None,
    }
    return {
        key: {"available": (True if module is None else importlib.util.find_spec(module) is not None),
              "role": {
                  "pyalex": "OpenAlex source discovery",
                  "docling": "local PDF/DOCX structured extraction",
                  "paperqa": "agentic scholarly Q&A; LLM/embedding setup needed",
                  "lightrag": "evidence-grounded candidate relation proposals; LLM/embedding setup needed",
                  "prov": "W3C PROV source lineage export",
                  "httpx": "self-hosted ExecutableClaims/GROBID service calls",
                  "cytoscape": "offline pinned interactive graph explorer",
              }[key]}
        for key, module in names.items()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cite-refinery-external",
        description="External research engines: discovery and proposed evidence, never automatic authority promotion.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("engines", help="Show locally installed/optional engines")
    oa = commands.add_parser("openalex", help="Search scholarly metadata through PyAlex")
    oa.add_argument("query")
    oa.add_argument("--limit", type=int, default=10)
    oa.add_argument("--api-key", default=None, help="Use OPENALEX_API_KEY environment variable instead when possible")
    oa.add_argument("--module-id", help="Stage neutral source leads for a module, never academic evidence")
    oa.add_argument("--module-title", help="Module title required if --module-id is provided")
    doc = commands.add_parser("docling", help="Extract local document through Docling")
    doc.add_argument("path")
    paper = commands.add_parser("paperqa", help="Run the PaperQA2 pqa ask CLI on a local paper directory")
    paper.add_argument("directory")
    paper.add_argument("question")
    paper.add_argument("--timeout", type=int, default=240)
    gro = commands.add_parser("grobid", help="Parse local PDF using a loopback GROBID TEI service")
    gro.add_argument("path")
    gro.add_argument("--endpoint", default="http://127.0.0.1:8070")
    clm = commands.add_parser("claims", help="Submit untrusted draft claims to loopback ExecutableClaims")
    clm.add_argument("text")
    clm.add_argument("--endpoint", default="http://127.0.0.1:8000")
    clm.add_argument("--fetch-result", action="store_true")
    pv = commands.add_parser("prov", help="Export semantic packet provenance to W3C PROV JSON")
    pv.add_argument("packet")
    viz = commands.add_parser("explore", help="Generate offline Cytoscape.js HTML explorer")
    viz.add_argument("packet")
    viz.add_argument("output_directory")
    rel = commands.add_parser("relations", help="Stage audited-model relation proposals into a candidate packet")
    rel.add_argument("module_titles_json", help="File containing {module_id:title} mapping")
    rel.add_argument("proposals_json", help="File containing candidate proposals array")
    span = commands.add_parser("audit-span", help="Check a claimed source quote against text, with no entailment promotion")
    span.add_argument("source_json", help="JSON object with source id, url and text")
    span.add_argument("quote")
    span.add_argument("--subject")
    span.add_argument("--object-name")
    span.add_argument("--model-decision", choices=["yes", "no", "unparseable"])
    for cmd in (oa, doc, paper, gro, clm, pv, rel, span):
        cmd.add_argument("--output", help="Write result as JSON rather than stdout")
    opts = parser.parse_args(argv)
    if opts.command == "engines":
        result = catalog()
    elif opts.command == "openalex":
        if bool(opts.module_id) != bool(opts.module_title):
            parser.error("--module-id and --module-title must be supplied together")
        leads = openalex_discover(opts.query, limit=opts.limit, api_key=opts.api_key)
        result = source_lead_packet(opts.module_id, opts.module_title, leads) if opts.module_id else leads
    elif opts.command == "docling":
        result = docling_extract(opts.path)
    elif opts.command == "paperqa":
        result = paperqa_ask(opts.directory, opts.question, timeout_seconds=opts.timeout)
    elif opts.command == "grobid":
        result = grobid_extract(opts.path, endpoint=opts.endpoint)
    elif opts.command == "claims":
        result = executable_claims_analyze(opts.text, endpoint=opts.endpoint, fetch_result=opts.fetch_result)
    elif opts.command == "prov":
        packet = json.loads(Path(opts.packet).read_text(encoding="utf-8"))
        result = prov_export_packet(packet)
    elif opts.command == "relations":
        modules = json.loads(Path(opts.module_titles_json).read_text(encoding="utf-8"))
        proposals = json.loads(Path(opts.proposals_json).read_text(encoding="utf-8"))
        if isinstance(proposals, dict):
            proposals = proposals.get("proposals", [])
        result = relation_proposal_packet(modules, proposals)
    elif opts.command == "audit-span":
        source = json.loads(Path(opts.source_json).read_text(encoding="utf-8"))
        if all((opts.subject, opts.object_name, opts.model_decision)):
            result = detect_explicit_link_misread(
                source, model_decision=opts.model_decision,
                exact_span=opts.quote, subject=opts.subject, object_name=opts.object_name)
        elif any((opts.subject, opts.object_name, opts.model_decision)):
            parser.error("--subject, --object-name and --model-decision must be given together")
        else:
            result = verify_source_span(source, opts.quote)
    elif opts.command == "explore":
        packet = json.loads(Path(opts.packet).read_text(encoding="utf-8"))
        result = export_cytoscape_explorer(packet, opts.output_directory)
    else:
        raise AssertionError("unhandled command")
    if getattr(opts, "output", None):
        out = Path(opts.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(str(out))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
