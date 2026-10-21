"""Read-only publisher text matching for user-supplied investigation sources.

Strict adapters only; never fetch an arbitrary user URL. Supported:
GitHub public issues, GitHub exact-commit code blobs, Europe PMC PMID abstracts.

A matched excerpt authenticates the text against an observed publisher record
at a point in time; it does NOT establish truth, independent field measurement,
causation, successful integration, reuse rights, operator need or revenue.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from hashlib import sha1, sha256
import html
import json
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

SCHEMA = "cite_refinery.publisher_text_match.v1"
_ISSUE = re.compile(r"^/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)$")
_BLOB = re.compile(r"^/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/blob/([0-9a-fA-F]{40})/([A-Za-z0-9_./+-]+)$")
_MED = re.compile(r"^/article/MED/([1-9][0-9]{4,9})$")
_MAX_RESPONSE = 1_000_000

class _RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Publisher endpoint attempted an unexpected redirect")

def classify(url):
    """Identify allowlisted public publisher routes, not arbitrary link targets."""
    try:
        p = urlsplit(url)
        if (p.scheme != "https" or p.port not in (None, 443) or
            p.username or p.password or p.query or p.fragment):
            return None
    except ValueError:
        return None
    if p.hostname == "github.com":
        m = _ISSUE.fullmatch(p.path)
        if m and all(x not in {".", ".."} for x in m.group(1, 2)):
            return ("github_issue", *m.groups())
        m = _BLOB.fullmatch(p.path)
        if m and all(segment not in {"", ".", ".."} for segment in m.group(4).split("/")) and (
            m.group(1) not in {".", ".."} and m.group(2) not in {".", ".."}
        ):
            return ("github_blob", *m.groups())
    if p.hostname == "europepmc.org":
        m = _MED.fullmatch(p.path)
        if m:return ("europepmc_abstract", m.group(1))
    return None

def _gh_api(path):
    # Validated paths are produced only from classify() route groups;
    # never allow a caller-supplied REST path or gh flags.
    p = subprocess.run(["gh", "api", "repos/" + path],
                       capture_output=True, text=True, timeout=22)
    if p.returncode:
        raise ConnectionError("Authenticated read-only GitHub source retrieval failed")
    if len(p.stdout)>_MAX_RESPONSE*2:
        raise ValueError("GitHub API response exceeded bounded maximum")
    return json.loads(p.stdout)

def _epmc(pmid):
    api = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urlencode({
        "query": "EXT_ID:" + pmid + " AND SRC:MED",
        "resultType": "core", "format": "json", "pageSize": 3,
    })
    opener = build_opener(_RejectRedirect())
    req = Request(api, headers={"User-Agent":"CiteRefinery-PublisherVerifier/0.1"})
    with opener.open(req, timeout=15) as response:
        if urlsplit(response.geturl()).hostname != "www.ebi.ac.uk":
            raise ValueError("Europe PMC publisher identity changed")
        raw=response.read(_MAX_RESPONSE+1)
        if len(raw)>_MAX_RESPONSE:
            raise ValueError("Europe PMC record exceeds bounded size")
        return json.loads(raw)

def _norm(value):
    return " ".join(html.unescape(value).split())

def _sha(data):
    return sha256(data.encode("utf-8")).hexdigest()

def match_source(source,*, github_fetch=_gh_api, epmc_fetch=_epmc):
    """Observe a canonical record and compare an exact whitespace-normalized span.

    Result has evidence-level status only; source assertions are NOT evaluated.
    Raises only for network/record failure or a programmatic security violation.
    """
    ident = classify(source["url"])
    text=source["text"]
    if not isinstance(text,str) or source.get("text_sha256")!=_sha(text):
        raise ValueError("Supplied source text digest mismatch; cannot authenticate changed evidence")
    result={
        "id":source["id"],"family":source["source_family"],
        "url":source["url"],"text_sha256":source["text_sha256"],
        "schema":SCHEMA,
        "checked_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_claim_verified":False,
        "source_independent_field_outcome_verified":False,
        "implementation_function_executed":False,
        "semantic_entailment_verified":False,
        "authority":"NONE_ACCEPTED",
    }
    if ident is None:
        return {**result,"status":"unsupported_publisher_route",
                "reason":"No arbitrary URL fetch. Only public GitHub issue, commit-pinned GitHub blob and Europe PMC PMID abstracts."}
    kind,*parts=ident
    expected_family={
        "github_issue":"practical",
        "github_blob":"implementation",
        "europepmc_abstract":"academic",
    }[kind]
    if source["source_family"]!=expected_family:
        return {
            **result,
            "status":"publisher_route_source_family_mismatch",
            "reason":"This constrained provider route does not verify the declared conceptual layer.",
            "expected_family":expected_family,
        }
    body=None
    publisher_url=None
    metadata={}
    if kind=="github_issue":
        owner,repo,number=parts
        record=github_fetch(f"{owner}/{repo}/issues/{number}")
        publisher_url=f"https://github.com/{owner}/{repo}/issues/{number}"
        if (record.get("html_url")!=publisher_url or
            record.get("number")!=int(number) or record.get("pull_request")):
            raise ValueError("Publisher issue identity mismatch or pull request impersonation")
        body=record.get("body") or ""
        metadata={
            "publisher_record_type":"github_issue_report",
            "publisher_updated_at":record.get("updated_at"),
            "publisher_body_sha256":_sha(body),
            "reporter_post_is_independent_field_measurement":False,
        }
    elif kind=="github_blob":
        owner,repo,commit,filename=parts
        record=github_fetch(f"{owner}/{repo}/contents/{filename}?ref={commit}")
        if (record.get("type")!="file" or record.get("encoding")!="base64" or
            record.get("path")!=filename or not record.get("sha")):
            raise ValueError("GitHub code record identity mismatch")
        raw=base64.b64decode(record.get("content",""),validate=False)
        if len(raw)>_MAX_RESPONSE:
            raise ValueError("Source blob exceeds bounded maximum")
        blob_sha=sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
        if blob_sha!=record["sha"]:
            raise ValueError("Publisher blob identity failed Git SHA-1 verification")
        try: body=raw.decode("utf-8")
        except UnicodeDecodeError as e:raise ValueError("Only UTF-8 plaintext is supported") from e
        publisher_url=f"https://github.com/{owner}/{repo}/blob/{commit}/{filename}"
        metadata={"publisher_record_type":"github_exact_commit_source_file",
                  "publisher_git_blob_sha":blob_sha,
                  "commit_locator":commit,
                  "source_executed":False,"license_reviewed":False}
    elif kind=="europepmc_abstract":
        pmid=parts[0]
        value=epmc_fetch(pmid)
        records=value.get("resultList",{}).get("result",[])
        matches=[r for r in records if str(r.get("pmid"))==pmid and
                 str(r.get("source","MED"))=="MED"]
        if len(matches)!=1:raise ValueError("Europe PMC PMID identity missing or ambiguous")
        record=matches[0]
        abstract=record.get("abstractText") or ""
        body=(record.get("title") or "")+" "+re.sub(r"<[^>]*>"," ",abstract)
        publisher_url=f"https://europepmc.org/article/MED/{pmid}"
        metadata={"publisher_record_type":"europepmc_bibliographic_abstract",
                  "publisher_pmid":pmid,"abstract_sha256":_sha(body),
                  "full_text_or_peer_review_verified":False}
    else:raise ValueError("unexpected constrained publisher type")
    if not body.strip():
        return {**result,"status":"publisher_record_without_text",
                "publisher_url":publisher_url,**metadata}
    # Require an actual contiguous passage from the original; don't infer
    # semantic equivalence from lexical overlap, punctuation or model votes.
    matched=_norm(text) in _norm(body)
    return {**result,
        "status":"publisher_passage_matched_claim_unreviewed" if matched
                 else "submitted_text_does_not_match_publisher",
        "publisher_url":publisher_url,
        "publisher_content_sha256":_sha(body),
        "publisher_content_bytes":len(body.encode("utf-8")),
        "exact_normalized_source_excerpt_match":matched,
        "matching_method":"case_sensitive_contiguous_passage_whitespace_and_html_entity_normalized",
        **metadata,
    }

def audit_sources(sources,*,github_fetch=_gh_api,epmc_fetch=_epmc):
    if not isinstance(sources,list) or len(sources)>6:
        raise ValueError("Maximum six source passages")
    results=[]
    for item in sources:
        try:
            results.append(match_source(item,github_fetch=github_fetch,epmc_fetch=epmc_fetch))
        except (ConnectionError, TimeoutError, HTTPError, URLError):
            # A network/provider failure is NOT a text mismatch or proof of
            # a forged record. Report abstention, no retry side effects.
            results.append({
                "schema":SCHEMA,"id":item["id"],"family":item["source_family"],
                "url":item["url"],"text_sha256":item["text_sha256"],
                "checked_at_utc":datetime.now(timezone.utc).isoformat(),
                "status":"publisher_verification_unavailable",
                "authority":"NONE_ACCEPTED",
                "source_claim_verified":False,
                "source_independent_field_outcome_verified":False,
                "implementation_function_executed":False,
                "semantic_entailment_verified":False,
            })
    return results
