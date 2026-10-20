"""Optional, provenance-preserving adapters for existing research engines.

Nothing here writes to the authoritative Cite-Refinery graph. Returned records
are discovery/proposal artifacts requiring review and explicit ingestion.
External libraries are imported lazily so core installation remains stdlib.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree as ET


class EngineUnavailable(RuntimeError):
    """Requested external engine is not installed, configured or reachable."""


def _text(value: Any, limit: int = 10000) -> str:
    return " ".join(str(value or "").split())[:limit]


def _valid_query(value: str, max_length: int = 500) -> str:
    q = _text(value, max_length + 1)
    if not (3 <= len(q) <= max_length):
        raise ValueError(f"query must contain 3-{max_length} characters")
    return q


def _abstract(inverted: Any, max_words: int = 350) -> str:
    if not isinstance(inverted, dict):
        return ""
    pos = {}
    for word, positions in inverted.items():
        if not isinstance(positions, list):
            continue
        for n in positions:
            if isinstance(n, int) and 0 <= n < max_words:
                pos[n] = str(word)
    return " ".join(pos[n] for n in sorted(pos))


def openalex_discover(query: str, *, limit: int = 10, works_factory=None,
                      api_key: str | None = None) -> list[dict[str, Any]]:
    """Execute real PyAlex Works search; results are source leads, NOT findings."""
    q = _valid_query(query)
    if not isinstance(limit, int) or not 1 <= limit <= 30:
        raise ValueError("limit must be between 1 and 30")
    if works_factory is None:
        try:
            import pyalex
        except ImportError as exc:
            raise EngineUnavailable("Install cite-refinery[openalex] for PyAlex") from exc
        key = api_key or os.environ.get("OPENALEX_API_KEY")
        if key:
            pyalex.config.api_key = key
        works_factory = pyalex.Works
    try:
        works = works_factory().search(q).get(per_page=limit)
    except Exception as exc:
        raise EngineUnavailable(f"PyAlex discovery failed: {type(exc).__name__}: {exc}") from exc
    leads = []
    for work in works or []:
        if not isinstance(work, dict):
            work = dict(work)
        location = work.get("primary_location") or {}
        source = location.get("source") or {}
        doi = work.get("doi") or ""
        identifier = work.get("id") or doi
        if not identifier:
            continue
        leads.append({
            "id": str(identifier), "title": _text(work.get("title"), 600),
            "doi": str(doi) if doi else None,
            "publication_year": work.get("publication_year"),
            "venue": _text(source.get("display_name"), 250),
            "cited_by_count": work.get("cited_by_count"),
            "open_access": work.get("open_access"),
            "abstract_excerpt": _abstract(work.get("abstract_inverted_index")),
            "source_ref": str(doi or identifier),
            "source_provider": "OpenAlex via PyAlex",
            "layer": "academic", "kind": "source_lead",
            "review_status": "metadata_only_not_verified_evidence",
            "boundary": "Search metadata and abstract are not full-text analysis or confirmation of any claim.",
        })
    return leads


def _safe_file(path: str | Path, suffixes: set[str], max_mb: int = 40) -> Path:
    try:
        p = Path(path).expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError("source file does not exist") from exc
    if not p.is_file() or p.suffix.lower() not in suffixes:
        raise ValueError(f"expected an existing local file with extension {sorted(suffixes)}")
    if p.stat().st_size > max_mb * 1024 * 1024:
        raise ValueError(f"file exceeds {max_mb} MB limit")
    return p


def docling_extract(path: str | Path, *, converter=None) -> dict[str, Any]:
    """Use Docling on a local file, retaining a digest and unasserted excerpts."""
    p = _safe_file(path, {".pdf", ".docx", ".pptx", ".html", ".md", ".txt"})
    if converter is None:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as exc:
            raise EngineUnavailable("Install cite-refinery[documents] for Docling") from exc
        converter = DocumentConverter()
    result = converter.convert(str(p))
    if not hasattr(result, "document"):
        raise ValueError("Docling returned no converted document")
    md = result.document.export_to_markdown()
    if not isinstance(md, str) or not md.strip():
        raise ValueError("Docling returned an empty document")
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    return {
        "engine": "Docling", "source_id": f"sha256:{digest}",
        "sha256": digest, "file_name": p.name,
        "content_markdown": md, "characters": len(md),
        "review_status": "machine_extraction_requires_source_review",
        "boundary": "Extracted text is not a verified academic claim; review layout, tables and citations.",
    }


def paperqa_ask(papers_directory: str | Path, question: str, *,
                executable: str = "pqa", timeout_seconds: int = 240) -> dict[str, Any]:
    """Invoke real PaperQA2 CLI with a local-paper directory; no shell injection."""
    directory = Path(papers_directory).expanduser().resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("papers_directory must be an existing local directory")
    q = _valid_query(question, 1500)
    if not 5 <= timeout_seconds <= 1200:
        raise ValueError("timeout_seconds must be 5-1200")
    command = shutil.which(executable) if os.path.sep not in executable else executable
    if not command or not Path(command).exists():
        raise EngineUnavailable("PaperQA2 CLI unavailable; install cite-refinery[paperqa] and configure an LLM")
    try:
        proc = subprocess.run([command, "ask", q], cwd=str(directory),
                              capture_output=True, text=True,
                              timeout=timeout_seconds, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise EngineUnavailable(f"PaperQA2 execution failed: {type(exc).__name__}") from exc
    if proc.returncode != 0:
        raise EngineUnavailable(f"PaperQA2 exited {proc.returncode}: {proc.stderr[:600]}")
    return {
        "engine": "PaperQA2", "query": q, "answer_candidate": proc.stdout[:60000],
        "working_directory": str(directory),
        "review_status": "llm_answer_needs_citation_and_evidence_review",
        "boundary": "This is an external agent's draft synthesis; cited page spans must be checked before graph ingestion.",
    }


def _json_answer(value: Any) -> dict:
    text = value if isinstance(value, str) else str(value or "")
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^\`\`\`(?:json)?\s*|\s*\`\`\`$", "", cleaned)
    if len(cleaned) > 100000:
        raise ValueError("discovery response exceeds 100,000 characters")
    try:
        doc = json.loads(cleaned)
    except (ValueError, TypeError) as exc:
        raise ValueError("LightRAG must return a JSON object with a proposals array") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("proposals"), list):
        raise ValueError("LightRAG JSON response requires proposals array")
    return doc


async def lightrag_propose(rag, *, source_text: str, module_ids: set[str],
                          source_refs: set[str], query_param=None,
                          max_proposals: int = 25,
                          source_passages: dict[str, str] | None = None) -> dict[str, Any]:
    """Use a configured LightRAG instance, never accept free-form model edges.

    Caller supplies a configured rag (embedding + LLM + graph DB already set);
    retrieved proposals are restricted to known module keys and known source IDs.
    """
    if not 1 <= max_proposals <= 100:
        raise ValueError("max_proposals out of range")
    if not isinstance(source_text, str) or not 5 <= len(source_text) <= 600000:
        raise ValueError("source_text must be between 5 and 600000 characters")
    if not module_ids or not source_refs:
        raise ValueError("explicit module_ids and source_refs are required")
    if source_passages is not None:
        if not isinstance(source_passages, dict) or not source_passages or not set(source_passages) <= source_refs:
            raise ValueError("source_passages must be a nonempty subset of the allowed source refs")
    if query_param is None:
        try:
            from lightrag import QueryParam
            query_param = QueryParam(mode="hybrid")
        except ImportError as exc:
            raise EngineUnavailable("Install cite-refinery[lightrag] and configure a LightRAG backend") from exc
    await rag.ainsert(source_text)
    prompt = (
        "Propose ONLY evidence-backed semantic relationships for Cite-Refinery. "
        "Return JSON object: {\\\"proposals\\\":[{\\\"source\\\":module_id,\\\"target\\\":module_id,"
        "\\\"relation\\\":UPPER_SNAKE_CASE,\\\"evidence_refs\\\":[source_id],\\\"reason\\\":text}]}. "
        "When asked for quotes, supply evidence_quotes as {source_id:verbatim_source_span}. "
        "No inferred CAUSES, ADDRESSES, IMPLEMENTS or effectiveness. "
        f"Allowed module IDs: {sorted(module_ids)}. Allowed source IDs: {sorted(source_refs)}."
    )
    raw = await rag.aquery(prompt, param=query_param)
    parsed = _json_answer(raw)
    result = []
    rejected = 0
    for proposal in parsed["proposals"][:max_proposals]:
        if not isinstance(proposal, dict):
            rejected += 1
            continue
        source = proposal.get("source")
        target = proposal.get("target")
        refs = proposal.get("evidence_refs")
        relation = str(proposal.get("relation", ""))
        if (source not in module_ids or target not in module_ids or
            source == target or not isinstance(refs, list) or not refs or
            not set(refs) <= source_refs or not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", relation) or
            relation in {"CAUSES", "SUPPORTS", "PRODUCES", "IMPLEMENTS", "DEPLOYED_BY", "ADDRESSES"}):
            rejected += 1
            continue
        quote_checks = []
        if source_passages is not None:
            from .external_evidence_audit import verify_source_span
            candidate_quotes = proposal.get("evidence_quotes")
            if not isinstance(candidate_quotes, dict) or set(refs) - set(source_passages):
                rejected += 1
                continue
            try:
                quote_checks = [verify_source_span(
                    {"id": ref, "url": ref, "text": source_passages[ref]},
                    candidate_quotes.get(ref, "")) for ref in set(refs)]
            except ValueError:
                rejected += 1
                continue
            if not all(item["literal_quote_found"] for item in quote_checks):
                rejected += 1
                continue
        result.append({
            "source": source, "target": target, "relation": relation,
            "evidence_refs": sorted(set(refs)),
            "status": "candidate", "reason": _text(proposal.get("reason"), 1200),
            "boundary": "Generated relation requiring independent source/scope review; no authority promotion.",
            "origin": "LightRAG-proposal-not-accepted",
            "source_span_checks": quote_checks,
        })
    return {"engine": "LightRAG", "proposals": result,
            "rejected_proposals": rejected,
            "review_status": "independent_human_or_source_review_required",
            "boundary": "Source ID allowlisting and optional literal-quote checks prevent invented refs and quotes; they do NOT confirm semantic entailment or a causal relation."}


def _local_endpoint(base_url: str) -> str:
    p = urlparse(base_url)
    if p.scheme != "http" or p.hostname not in {"localhost", "127.0.0.1", "::1"} or p.username or p.password:
        raise ValueError("External engine endpoints must be explicit loopback HTTP addresses")
    return base_url.rstrip("/")


def executable_claims_analyze(text: str, *, endpoint: str = "http://127.0.0.1:8000",
                              client=None, fetch_result: bool = True) -> dict[str, Any]:
    """Call self-hosted ExecutableClaims API. Never run generated capsules."""
    q = _valid_query(text, 120000)
    base = _local_endpoint(endpoint)
    if client is None:
        try:
            import httpx
        except ImportError as exc:
            raise EngineUnavailable("Install cite-refinery[services] for httpx") from exc
        client = httpx.Client(timeout=50)
        own_client = True
    else:
        own_client = False
    try:
        response = client.post(base + "/api/v1/analyze",
                               json={"text": q, "extract_counterevidence": True,
                                     "generate_capsules": False})
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("ExecutableClaims API returned non-object")
        id_value = payload.get("id") or payload.get("analysis_id")
        detail = None
        if fetch_result and id_value is not None:
            detail_response = client.get(base + "/api/v1/analysis/" + str(id_value))
            detail_response.raise_for_status()
            detail = detail_response.json()
        return {
            "engine": "ExecutableClaims", "analysis_id": id_value,
            "submission": payload, "detail": detail,
            "review_status": "external_analysis_unaccepted",
            "boundary": "No generated capsule executed, no automatic acceptance of external entailment labels.",
        }
    finally:
        if own_client:
            client.close()


def grobid_extract(path: str | Path, *, endpoint: str = "http://127.0.0.1:8070",
                   client=None) -> dict[str, Any]:
    """Use the real GROBID fulltext endpoint without allowing arbitrary remote URLs."""
    p = _safe_file(path, {".pdf"})
    base = _local_endpoint(endpoint)
    if client is None:
        try:
            import httpx
        except ImportError as exc:
            raise EngineUnavailable("Install cite-refinery[services] for httpx") from exc
        client = httpx.Client(timeout=120)
        own_client = True
    else:
        own_client = False
    try:
        with p.open("rb") as file:
            r = client.post(base + "/api/processFulltextDocument",
                            files={"input": (p.name, file, "application/pdf")})
        r.raise_for_status()
        root = ET.fromstring(r.text)
        if not root.tag.endswith("TEI"):
            raise ValueError("GROBID did not return TEI XML")
        return {
            "engine": "GROBID",
            "source_id": "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest(),
            "tei_xml": r.text,
            "review_status": "machine_extraction_requires_source_review",
            "boundary": "Bibliographic/full-text extraction must be checked against the PDF.",
        }
    finally:
        if own_client:
            client.close()


def prov_export_packet(packet: dict[str, Any]) -> dict:
    """Use W3C PROV to export source-to-node lineage, NOT semantic truth/effect."""
    try:
        from prov.model import ProvDocument
    except ImportError as exc:
        raise EngineUnavailable("Install cite-refinery[provenance] for Python PROV") from exc
    if not isinstance(packet, dict) or not isinstance(packet.get("nodes"), list):
        raise ValueError("semantic packet with nodes is required")
    doc = ProvDocument()
    doc.add_namespace("cr", "https://cite-agent.com/ns/refinery/")
    source_index = {}
    for n in packet["nodes"]:
        identifier = "cr:node_" + hashlib.sha256(str(n.get("key")).encode()).hexdigest()[:24]
        doc.entity(identifier, {"prov:label": _text(n.get("statement"), 400),
                                "cr:layer": str(n.get("layer", "neutral")),
                                "cr:review_status": "candidate_or_input"})
        for ref in n.get("source_refs") or []:
            sid = "cr:source_" + hashlib.sha256(str(ref).encode()).hexdigest()[:24]
            if sid not in source_index:
                source_index[sid] = ref
                doc.entity(sid, {"prov:label": str(ref)})
            doc.wasDerivedFrom(identifier, sid)
    return {
        "format": "W3C_PROV_JSON", "document": json.loads(doc.serialize(format="json")),
        "source_count": len(source_index), "node_count": len(packet["nodes"]),
        "boundary": "PROV source derivation records provenance only; it never asserts that evidence supports a semantic claim.",
    }


async def paperqa_retrieve_local(
    source_path: str | Path,
    question: str,
    *,
    citation: str,
    title: str | None = None,
    doi: str | None = None,
    k: int = 3,
    docs_factory=None,
    settings=None,
) -> dict[str, Any]:
    """Actually ingest and retrieve PaperQA2 passages, without LLM answering.

    PaperQA2 metadata enrichment is explicitly disabled: source details are
    provided by caller, not silently fetched from rate-limited providers.
    The retrieved chunks are source candidates, not accepted academic claims.
    """
    import time
    p = _safe_file(source_path, {".pdf", ".txt", ".md", ".html", ".docx"}, max_mb=25)
    q = _valid_query(question, 1200)
    c = _valid_query(citation, 600)
    if not isinstance(k, int) or not 1 <= k <= 12:
        raise ValueError("k must be between 1 and 12")
    if docs_factory is None or settings is None:
        try:
            from paperqa import Docs, Settings
            from paperqa.settings import ParsingSettings
        except ImportError as exc:
            raise EngineUnavailable("Install cite-refinery[paperqa] for native PaperQA2 retrieval") from exc
        if docs_factory is None:
            docs_factory = Docs
        if settings is None:
            settings = Settings(
                llm="ollama/llama3.2:3b",
                summary_llm="ollama/llama3.2:3b",
                embedding="sparse",
                parsing=ParsingSettings(use_doc_details=False, multimodal=False),
            )
    docs = docs_factory()
    start = time.monotonic()
    await docs.aadd(str(p), citation=c, title=title or p.stem,
                    doi=doi, settings=settings)
    results = await docs.retrieve_texts(q, k=k, settings=settings)
    return {
        "engine": "PaperQA2 sparse retrieval",
        "source_document_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        "source_name": p.name,
        "citation_supplied_by_caller": c,
        "doi_supplied_by_caller": doi,
        "query": q,
        "matches": [
            {
                "chunk_id": str(getattr(chunk, "name", "")),
                "excerpt": str(getattr(chunk, "text", ""))[:4500],
                "source_document_id": str(getattr(getattr(chunk, "doc", None), "dockey", "")),
                "review_status": "retrieved_text_requires_passage_and_entailment_review",
            }
            for chunk in results
        ],
        "elapsed_seconds_excluding_python_startup": round(time.monotonic() - start, 3),
        "metadata_network_lookup": "disabled",
        "llm_answer_generation": "disabled",
        "boundary": "Retrieval is not semantic entailment, intervention effectiveness, or an accepted Academic claim.",
    }
