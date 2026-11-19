"""Read-only source exporter; writes only its dedicated refresh evidence folder."""
from __future__ import annotations

from collections import Counter, OrderedDict
from datetime import datetime, timezone
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
from urllib.parse import urlparse

BASE = None
OUT = None
RUNS = ('signals-20pct-20261118', 'signals-second20pct-20261118', 'signals-final60pct-20261119')
FINAL = None
SECOND = None
SOURCE_FIELDS = set('acquisition byte_integrity_checked bytes catalog_id git_blob_sha head_binding html_url_at_capture id identity_checked kind manifest_record_sha256 observed_at original_path path quality_flags receipt_path sha256 source_url status runtime_tested'.split())
RESULT_FIELDS = set('analysis_method catalog_id custom_glue evidence additional_evidence explanation_state human_work inputs limits outputs publication_observations purpose review_method review_reason reviewed_by revision_of_sha256 semantic_support_verified source_sha256 status title url runtime_tested workflow_tested worker'.split())
PROJECT_FIELDS = set('catalog_id slug title url description topics keywords ordinal announcement publication_observations source_archive source source_url provider watch_url page_url stars'.split())
SENSITIVE_KEYS = {'account_attribution', 'last_account_check', 'metered_calls', 'attempts', 'rate_remaining', 'rate_reset', 'rate_limit', 'access_token', 'bearer_token', 'authorization', 'api_key', 'password', 'private_key', 'cookie', 'cookies', 'usage', 'resource_metrics', 'remote_model_invocations'}
CONTEXT_KEYS = {'buyer_validated', 'buyers', 'buyer_demand', 'market_demand', 'workflow_opportunities', 'workflow_families', 'workflow_roles', 'contribution', 'commercial_status', 'opportunities'}


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def object_sha(value):
    return sha(json_text(value).encode())


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def sanitize(value, excluded=None, prefix=''):
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            location = prefix + '.' + key if prefix else key
            if key in SENSITIVE_KEYS or key in CONTEXT_KEYS:
                if excluded is not None:
                    excluded.append(location)
                continue
            output[key] = sanitize(item, excluded, location)
        return output
    if isinstance(value, list):
        return [sanitize(item, excluded, prefix + '[]') for item in value]
    return value


def select(value, fields, excluded):
    if not isinstance(value, dict):
        return None
    excluded.extend(sorted(set(value) - fields))
    return sanitize({key: item for key, item in value.items() if key in fields}, excluded)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def parsed(value):
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def connect(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    connection.execute('PRAGMA query_only=ON')
    connection.execute('BEGIN')
    return connection


def file_receipt(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': file_sha(path), 'bytes': path.stat().st_size}


def database_files(path):
    path = Path(path).resolve()
    return [file_receipt(p) for p in (path, Path(str(path) + '-wal')) if p.exists()]


class Checks:
    def __init__(self):
        self.sources = {}
        self.quotes = {}
        self.cache = OrderedDict()
        self.cache_bytes = 0

    def original(self, path, expected):
        key = (str(path), expected)
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        receipt = {'path': str(path), 'expected_sha256': expected}
        try:
            target = Path(path).resolve()
            if not target.is_relative_to(BASE) or not target.is_file() or target.stat().st_size > 16 * 1024 * 1024:
                raise ValueError('source outside retained archive scope or byte budget')
            raw = target.read_bytes()
            actual = sha(raw)
            receipt.update(actual_sha256=actual, bytes=len(raw), state='match' if actual == expected else 'mismatch')
        except (OSError, ValueError, TypeError) as exc:
            raw = None
            receipt.update(actual_sha256=None, state='unavailable', error_type=type(exc).__name__)
        previous = self.sources.get(key)
        if previous and previous != receipt:
            raise ValueError('retained source changed during export')
        self.sources[key] = receipt
        if raw is not None:
            self.cache[key] = raw
            self.cache_bytes += len(raw)
            while self.cache_bytes > 24 * 1024 * 1024 and len(self.cache) > 1:
                _, old = self.cache.popitem(last=False)
                self.cache_bytes -= len(old)
        return raw

    def source(self, original):
        path = original.get('path', original.get('source_path'))
        expected = original.get('sha256', original.get('source_sha256'))
        if not path or not expected:
            return None
        self.original(path, expected)
        return self.sources[(path, expected)]

    def quote(self, proof, defaults=None):
        proof = {**(defaults or {}), **proof}
        path = proof.get('path', proof.get('source_path'))
        expected = proof.get('sha256', proof.get('source_sha256'))
        quote = proof.get('quote', proof.get('excerpt'))
        if not path or not expected or not isinstance(quote, str) or not quote:
            return None
        raw = self.original(path, expected)
        quote_sha = sha(quote.encode('utf-8'))
        key = (path, expected, quote_sha)
        check = {'source_path': path, 'source_sha256': expected, 'quote_sha256': quote_sha,
                 'state': 'source_unavailable', 'semantic_support_verified': False, 'runtime_tested': False}
        if raw is not None:
            try:
                text = raw.decode('utf-8')
                start = text.find(quote)
                count = text.count(quote)
                char_end = start + len(quote) if start >= 0 else None
                byte_start = len(text[:start].encode('utf-8')) if start >= 0 else None
                byte_end = byte_start + len(quote.encode('utf-8')) if byte_start is not None else None
                check.update(literal_count=count, character_start=start if start >= 0 else None,
                             character_end=char_end, byte_start=byte_start, byte_end=byte_end,
                             state='match' if count == 1 and self.sources[(path, expected)]['state'] == 'match'
                             else 'literal_not_unique' if count > 1 else 'mismatch')
                comparisons = {}
                for source_key, actual_value in (('start', start), ('end', char_end), ('character_start', start),
                                                 ('character_end', char_end), ('byte_start', byte_start), ('byte_end', byte_end)):
                    if source_key in proof:
                        comparisons[source_key] = proof[source_key] == actual_value
                check['supplied_offsets_match'] = all(comparisons.values())
                check['start_match'] = all(value for key_, value in comparisons.items() if key_ in {'start', 'character_start'})
                check['end_match'] = all(value for key_, value in comparisons.items() if key_ in {'end', 'character_end'})
                check['offset_checks'] = comparisons
                if not check['supplied_offsets_match']:
                    check['state'] = 'offset_mismatch'
            except UnicodeError:
                check['state'] = 'non_utf8_source'
        previous = self.quotes.get(key)
        if previous and previous['state'] != check['state']:
            raise ValueError('contradictory quote/offset checks for retained evidence')
        self.quotes[key] = check
        return check

    def result(self, result):
        checks = []
        for field in ('evidence', 'additional_evidence'):
            for index, evidence in enumerate(result.get(field, [])):
                check = self.quote(evidence)
                if check:
                    checks.append({**check, 'field': field, 'index': index})
        for observation in result.get('publication_observations', []):
            if observation.get('feed_path') and observation.get('feed_sha256'):
                self.source({'path': observation['feed_path'], 'sha256': observation['feed_sha256']})
        return checks


def technical_fingerprint(result):
    clean = {'purpose': ' '.join(str(result.get('purpose') or '').split())}
    for field in ('inputs', 'outputs', 'human_work', 'custom_glue', 'limits'):
        clean[field] = [' '.join(str(value).split()) for value in result.get(field, [])]
    clean['evidence'] = sorted([{'path': evidence.get('path', evidence.get('source_path')),
        'sha256': evidence.get('sha256', evidence.get('source_sha256')), 'source_url': evidence.get('source_url'),
        'quote': evidence.get('quote', evidence.get('excerpt'))} for field in ('evidence', 'additional_evidence')
        for evidence in result.get(field, [])], key=json_text)
    return object_sha(clean)


def wrapper(path):
    raw = Path(path).read_bytes()
    omitted = []
    doc = sanitize(json.loads(raw), omitted)
    return {'path': str(path), 'sha256': sha(raw), 'bytes': len(raw), 'document': doc,
            'exported_document_sha256': object_sha(doc), 'excluded_fields': sorted(set(omitted))}


def main():
    global BASE, OUT, FINAL, SECOND
    parser = argparse.ArgumentParser(description="Export the frozen November 19 repository findings without restarting acquisition or mapping.")
    parser.add_argument("--discovery-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    BASE, OUT = args.discovery_root.resolve(), args.output.resolve()
    FINAL, SECOND = BASE / RUNS[-1], BASE / RUNS[1]
    if OUT == BASE or any(OUT.is_relative_to(BASE / cohort) for cohort in RUNS):
        raise ValueError("export output must be separate from all original cohorts")
    OUT.mkdir(parents=True, exist_ok=True)
    began = datetime.now(timezone.utc).isoformat()
    checks = Checks()
    export = {'schema': 'cite_refinery.repository_refresh_export.v1', 'observed_at': began,
              'records': [], 'cohorts': [], 'identity_reviews': [], 'census_reviews': [],
              'handoff_documents': [], 'handoff_interfaces': [], 'gallery_records': [], 'published_records': []}
    queue_by_id = {}
    cohort_ids = set()
    for cohort in RUNS:
        path = BASE / cohort / 'mapping.sqlite3'
        before = database_files(path)
        connection = connect(path)
        metadata = {key: parsed(value) for key, value in connection.execute('SELECT key,value FROM metadata')}
        content_digest, row_count, states = hashlib.sha256(), 0, Counter()
        cursor = connection.execute('SELECT catalog_id,ordinal,project_json,status,source_json,source_sha256,reason,result_json,result_sha256,worker,updated_at FROM projects ORDER BY ordinal')
        for values in cursor:
            cid, ordinal, project_blob, status, source_blob, source_sha, reason, result_blob, result_sha, worker, at = values
            if cid in cohort_ids:
                raise ValueError('mapping cohorts repeat a discovery identity')
            cohort_ids.add(cid)
            original_row_sha = object_sha(list(values))
            content_digest.update((original_row_sha + '\n').encode())
            project, original = json.loads(project_blob), json.loads(source_blob) if source_blob else None
            result = json.loads(result_blob) if result_blob else None
            omitted = {'project': [], 'source': [], 'result': []}
            record = {'cohort': cohort, 'catalog_id': cid, 'ordinal': ordinal,
                      'project': select(project, PROJECT_FIELDS, omitted['project']), 'status': status,
                      'source': select(original, SOURCE_FIELDS, omitted['source']), 'source_sha256': source_sha,
                      'result': select(result, RESULT_FIELDS, omitted['result']), 'result_sha256': result_sha,
                      'reason': reason, 'worker': worker, 'updated_at': at,
                      'original_row_sha256': original_row_sha,
                      'original_project_json_sha256': sha(project_blob.encode()),
                      'original_source_json_sha256': sha(source_blob.encode()) if source_blob else None,
                      'original_result_json_sha256': sha(result_blob.encode()) if result_blob else None,
                      'excluded_fields': omitted, 'source_check': checks.source(original or {}),
                      'quote_checks': checks.result(result or {})}
            record['result_hash_matches'] = result_sha == record['original_result_json_sha256'] if result_blob else None
            record['technical_fingerprint_sha256'] = technical_fingerprint(result) if result else None
            export['records'].append(record)
            queue_by_id[cid] = record
            states[status] += 1
            row_count += 1
        connection.close()
        after = database_files(path)
        if before != after:
            raise ValueError('queue database/WAL bytes changed during read-only export')
        export['cohorts'].append({'cohort': cohort, 'path': str(path), 'source_files': before,
            'database_files_unchanged': True, 'records': row_count, 'status_counts': dict(states),
            'ordered_original_row_hashes_sha256': content_digest.hexdigest(),
            'metadata': {key: metadata[key] for key in ('schema', 'cohort_path', 'cohort_sha256', 'created_at', 'source_archive', 'target_count') if key in metadata},
            'catalog_id_set_sha256': object_sha(sorted(r['catalog_id'] for r in export['records'] if r['cohort'] == cohort))})
        print('EXPORTED_COHORT', cohort, row_count, dict(states), flush=True)

    # Preserve every published catalogue row and any technical interpretation
    # that is not identical to its latest accepted queue record.
    published = (BASE / 'signals-20pct-20261118/catalog/current.sqlite3').resolve()
    before = database_files(published)
    connection = connect(published)
    metadata = {key: parsed(value) for key, value in connection.execute('SELECT key,value FROM metadata')}
    ledger, counts, published_hashes = [], Counter(), hashlib.sha256()
    for cid, state, payload_blob in connection.execute('SELECT catalog_id,review_state,payload FROM projects ORDER BY ordinal'):
        payload = json.loads(payload_blob)
        payload_sha = sha(payload_blob.encode())
        published_hashes.update((cid + ':' + payload_sha + '\n').encode())
        queue = queue_by_id.get(cid)
        source_receipts = []
        for original in payload.get('original_sources', []):
            omitted = []
            receipt = select(original, SOURCE_FIELDS | {'source_url'}, omitted)
            receipt['source_check'] = checks.source(original)
            receipt['excluded_fields'] = omitted
            source_receipts.append(receipt)
        interpretations = []
        for index, result in enumerate(payload.get('workflow_contributions', [])):
            fingerprint = technical_fingerprint(result)
            matched = bool(queue and queue['status'] == 'mapped' and queue['technical_fingerprint_sha256'] == fingerprint)
            decision = 'identical_technical_content_in_queue' if matched else 'published_only_or_different_technical_content'
            interpretations.append({'index': index, 'technical_fingerprint_sha256': fingerprint,
                'original_contribution_sha256': object_sha(result), 'disposition': decision,
                'queue_result_sha256': queue['result_sha256'] if matched else None})
            counts[decision] += 1
            if not matched:
                omitted = []
                record = {'catalog_id': cid, 'published_index': index, 'status': state,
                          'project': {key: payload[key] for key in ('catalog_id', 'slug', 'url', 'description', 'topics', 'keywords') if key in payload},
                          'result': select(result, RESULT_FIELDS, omitted),
                          'original_payload_sha256': payload_sha, 'original_result_sha256': object_sha(result),
                          'technical_fingerprint_sha256': fingerprint, 'quote_checks': checks.result(result),
                          'source_receipts': source_receipts, 'excluded_fields': omitted,
                          'reason': 'no_accepted_queue_record' if not queue or queue['status'] != 'mapped' else 'differs_from_current_queue_technical_content',
                          'repository_record': cid.startswith('github:')}
                export['published_records'].append(record)
        ledger.append({'catalog_id': cid, 'review_state': state, 'original_payload_sha256': payload_sha,
                       'source_receipts': source_receipts, 'interpretations': interpretations})
    connection.close()
    after = database_files(published)
    if before != after:
        raise ValueError('published catalogue changed during export')
    export['published_catalog'] = {'path': str(published), 'source_files': before, 'database_files_unchanged': True,
        'project_records': len(ledger), 'catalog_id_set_sha256': object_sha(sorted(r['catalog_id'] for r in ledger)),
        'ordered_payload_hashes_sha256': published_hashes.hexdigest(), 'interpretation_accounting': dict(counts),
        'metadata': {key: sanitize(metadata[key]) for key in ('schema', 'built_at', 'source_dataset', 'input_receipts', 'coverage') if key in metadata},
        'records': ledger}
    print('EXPORTED_PUBLISHED', len(ledger), dict(counts), 'extras', len(export['published_records']), flush=True)

    # Raw reviewed decisions plus an explicitly derived, hash-bound groups view
    # for the second cohort. Proposed plans remain source documents, not verdicts.
    identity_paths = [SECOND / 'reviews/luna-identity-review.json', SECOND / 'reviews/singleton-native-reuse-review.json',
        SECOND / 'reviews/canonical-representative-selection-overrides.json', SECOND / 'reviews/final-native-verification.json',
        FINAL / 'reviews/canonical-native-reviewed-resolutions.json']
    for path in identity_paths:
        export['identity_reviews'].append(wrapper(path))
    native_raw = read_json(SECOND / 'actual-all-native-bindings.json')
    bindings = {key: {field: row[field] for field in ('node_id', 'source_refs') if field in row}
                for key, row in native_raw['modules'].items() if key.startswith('github:')}
    export['native_identity_bindings'] = {**file_receipt(SECOND / 'actual-all-native-bindings.json'),
        'project_id': native_raw['project_id'], 'modules': bindings,
        'excluded_fields': ['nonrepository_modules', 'module.statement', 'cluster_ids'], 'native_graph_mutated': False}
    review = read_json(SECOND / 'reviews/luna-identity-review.json')
    groups = []
    for case in review['reviewed_cases']:
        canonical = case.get('evidence_summary', {}).get('canonical_repository_id')
        entries = case.get('source_entries', [])
        if not canonical or not entries or any(entry.get('resolved_canonical_id_from_captured_html_url') != canonical for entry in entries):
            continue
        ids = sorted({entry['catalog_id'] for entry in entries})
        witnesses = []
        for entry in entries:
            check = checks.source({'source_path': entry['source_path'], 'source_sha256': entry['source_sha256']})
            witnesses.append({'catalog_id': entry['catalog_id'], 'path': entry['source_path'], 'sha256': entry['source_sha256'],
                              'captured_html_url': entry['html_url_at_capture'], 'source_check': check})
        groups.append({'canonical_id': canonical, 'catalog_ids': ids, 'incumbent_bindings': {rid: bindings[rid] for rid in ids if rid in bindings},
                       'preserved_contexts': {entry['catalog_id']: {'resolved_canonical_id': canonical,
                           'captured_html_url': entry['html_url_at_capture']} for entry in entries},
                       'source_witnesses': witnesses, 'reason': case['identity_disposition'],
                       'native_merge_performed': False, 'original_review_case': case['case_number']})
    if len(groups) != 53:
        raise ValueError('second-cohort reviewed canonical collision count changed')
    singleton = read_json(SECOND / 'reviews/singleton-native-reuse-review.json')
    for row in singleton['rows']:
        ids = sorted({row['catalog_id'], row['existing_native_catalog_id']})
        groups.append({'canonical_id': row['resolved_canonical_id'], 'catalog_ids': ids,
                       'incumbent_bindings': {rid: bindings[rid] for rid in ids if rid in bindings},
                       'preserved_contexts': {row['catalog_id']: {'resolved_canonical_id': row['resolved_canonical_id'],
                           'captured_html_url': row['captured_html_url']}}, 'reason': row['decision'],
                       'native_merge_performed': False, 'singleton_review': True})
    derived = {'schema': 'cite_refinery.repository_reviewed_identity_projection.v1', 'reviewed_by': review['reviewer'],
               'reviewed_at': review.get('status_snapshot_read_at'), 'groups': groups,
               'source_documents': [file_receipt(SECOND / 'reviews/luna-identity-review.json'),
                                    file_receipt(SECOND / 'reviews/singleton-native-reuse-review.json'),
                                    file_receipt(SECOND / 'actual-all-native-bindings.json')],
               'boundary': 'Projects are annotated with reviewed captured identity; existing native nodes and bindings remain unchanged.'}
    derived_path = OUT / 'normalized-reviewed-identities.json'
    derived_path.write_text(json_text(derived) + '\n', encoding='utf-8')
    export['identity_reviews'].append(wrapper(derived_path))
    for group in export['identity_reviews'][4]['document']['groups']:
        for source in group.get('source_witnesses', []):
            checks.source(source)

    # All census decisions remain accounted, including rejected and withheld ones.
    census_path = FINAL / 'source-artifact-census/reviewed-passages.jsonl'
    census_rows, withheld, census_count = [], 0, Counter()
    with census_path.open(encoding='utf-8') as stream:
        for line in stream:
            original = json.loads(line)
            row = sanitize(original)
            row['original_record_sha256'] = object_sha(original)
            census_count[row['decision']] += 1
            hidden = bool(row.get('content_withheld') or row['decision'] == 'restricted')
            checks.source({'source_path': row['source_path'], 'source_sha256': row['source_sha256']})
            if hidden:
                withheld += 1
                row['content_withheld'] = True
                for field in ('approved_evidence', 'census_evidence', 'reviewed_context'):
                    if isinstance(row.get(field), dict):
                        row[field].pop('quote', None)
                row['export_exclusion_reason'] = 'Existing content-withheld decision preserved; no withheld text reconstructed or exported.'
            else:
                row['export_quote_checks'] = [check for field in ('approved_evidence', 'census_evidence', 'reviewed_context')
                    if isinstance(row.get(field), dict) and (check := checks.quote(row[field], {'source_path': row['source_path'], 'source_sha256': row['source_sha256']}))]
            census_rows.append(row)
    export['census_reviews'].append({**file_receipt(census_path), 'document': {'schema': 'cite_refinery.repository_census_export.v1', 'reviews': census_rows},
        'original_row_count': len(census_rows), 'withheld_content_rows': withheld, 'excluded_fields': ['buyer_validated', 'withheld quote text']})
    export['census_audit'] = wrapper(FINAL / 'source-artifact-census/review-audit.json')
    print('EXPORTED_CENSUS', len(census_rows), dict(census_count), 'withheld', withheld, flush=True)

    current = read_json(FINAL / 'artifact-handoff-index/CURRENT.json')
    handoff_path = Path(current['json_path'])
    if file_sha(handoff_path) != current['checksums']['handoffs.json']:
        raise ValueError('handoff JSON differs from current checkpoint receipt')
    handoff = wrapper(handoff_path)
    export['handoff_documents'].append(handoff)
    export['handoff_checkpoint'] = sanitize(current)
    connection = connect(Path(current['sqlite_path']))
    for cid, fmt, direction, evidence_blob, profile_blob in connection.execute('SELECT i.catalog_id,i.format,i.direction,i.evidence,p.payload FROM interfaces i JOIN profiles p USING(catalog_id) ORDER BY i.catalog_id,i.format,i.direction'):
        evidence, profile = json.loads(evidence_blob), sanitize(json.loads(profile_blob))
        proof = checks.quote(evidence)
        export['handoff_interfaces'].append({'catalog_id': cid, 'format': fmt, 'direction': direction,
            'evidence': sanitize(evidence), 'profile': profile, 'evidence_check': proof,
            'original_evidence_json_sha256': sha(evidence_blob.encode()), 'original_profile_json_sha256': sha(profile_blob.encode())})
    connection.close()
    for group in handoff['document']['format_groups']:
        for pair in group['representative_pairs']:
            for end in ('producer', 'consumer'):
                checks.quote(pair[end]['interface_evidence'])
    export['handoff_checkpoint']['export_accounting'] = {'qualified_interfaces_exported': len(export['handoff_interfaces']),
        'explicit_examples_exported': sum(len(group['representative_pairs']) for group in handoff['document']['format_groups']),
        'potential_pairs_are_not_materialized_as_tested_or_qualified_links': True}

    gallery_path = FINAL / 'workflow-index/gallery.sqlite3'
    before = database_files(gallery_path)
    connection = connect(gallery_path)
    gallery_counts = Counter()
    for identity, origin, kind, payload_blob in connection.execute('SELECT id,origin,kind,payload FROM jobs ORDER BY id'):
        payload = json.loads(payload_blob)
        fields = {'input', 'output', 'steps', 'sources', 'boundary', 'human_gates', 'workflow_tested'}
        projection = sanitize({key: value for key, value in payload.items() if key in fields})
        export['gallery_records'].append({'id': identity, 'origin': origin, 'kind': kind,
            'original_payload_sha256': sha(payload_blob.encode()), 'technical_projection': projection,
            'authority': 'workflow_context_only; no_independent_repository_capability_admission',
            'excluded_fields': sorted(set(payload) - fields), 'workflow_tested': payload.get('workflow_tested', False)})
        gallery_counts[(origin, kind)] += 1
    connection.close()
    if before != database_files(gallery_path):
        raise ValueError('gallery changed during export')
    export['gallery_accounting'] = {'source_files': before, 'database_files_unchanged': True,
        'rows': len(export['gallery_records']), 'counts': [{'origin': origin, 'kind': kind, 'count': count} for (origin, kind), count in sorted(gallery_counts.items())],
        'boundary': 'All gallery rows accounted; technical workflow annotations retained as context and not promoted to capability claims.'}

    stop_path = FINAL / 'STOPPED-RUN.json'
    stop = read_json(stop_path)
    allowed = ('at', 'automatic_resume', 'state', 'native_graph_promoted', 'observer_running', 'units', 'cohort_size', 'cohort_states', 'source_capture_counts')
    export['stop'] = {**file_receipt(stop_path), 'document': {key: stop[key] for key in allowed if key in stop},
                      'excluded_fields': sorted(set(stop) - set(allowed)), 'services_queried_read_only': {}}
    for unit in stop.get('units', {}):
        process = subprocess.run(['systemctl', '--user', 'show', unit, '--property=ActiveState,UnitFileState,SubState', '--no-pager'],
                                 capture_output=True, text=True, timeout=10, check=False)
        export['stop']['services_queried_read_only'][unit] = {'returncode': process.returncode,
            'properties': dict(line.split('=', 1) for line in process.stdout.splitlines() if '=' in line)}

    export['source_checks'] = sorted(checks.sources.values(), key=lambda row: (row['path'], str(row['expected_sha256'])))
    export['evidence_checks'] = sorted(checks.quotes.values(), key=lambda row: (row['source_path'], row['source_sha256'], row['quote_sha256']))
    export['integrity'] = {'source_check_counts': dict(Counter(row['state'] for row in export['source_checks'])),
        'quote_check_counts': dict(Counter(row['state'] for row in export['evidence_checks'])),
        'result_hash_counts': dict(Counter(str(row['result_hash_matches']) for row in export['records'])),
        'completed_at': datetime.now(timezone.utc).isoformat(), 'source_programs_executed': False,
        'mapping_restarted': False, 'remote_project_or_service_mutations': False,
        'output_scope': str(OUT), 'exporter_sha256': file_sha(Path(__file__))}
    path = OUT / 'repository_refresh_export.json'
    with path.open('w', encoding='utf-8') as stream:
        json.dump(export, stream, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        stream.write('\n')
    compressed = OUT / 'repository_refresh_export.json.gz'
    with path.open('rb') as source, compressed.open('wb') as target:
        with gzip.GzipFile(filename='', fileobj=target, mode='wb', mtime=0, compresslevel=6) as gz:
            while chunk := source.read(1024 * 1024):
                gz.write(chunk)
    encoded = base64.b64encode(compressed.read_bytes()).decode('ascii')
    chunk_size = 300000
    chunk_records = []
    for index, offset in enumerate(range(0, len(encoded), chunk_size)):
        part = encoded[offset:offset + chunk_size]
        name = 'transfer-%03d.b64' % index
        (OUT / name).write_text(part, encoding='ascii')
        chunk_records.append({'name': name, 'characters': len(part), 'sha256': sha(part.encode())})
    summary = {'schema': 'cite_refinery.repository_refresh_export_receipt.v1', 'observed_at': began,
        'json': file_receipt(path), 'gzip': file_receipt(compressed), 'base64_characters': len(encoded),
        'chunks': chunk_records, 'record_count': len(export['records']),
        'status_counts': dict(Counter(row['status'] for row in export['records'])),
        'published_projects': len(ledger), 'published_interpretation_accounting': dict(counts),
        'published_records': len(export['published_records']), 'identity_review_documents': len(export['identity_reviews']),
        'normalized_second_identity_groups': len(groups), 'final_identity_groups': len(export['identity_reviews'][4]['document']['groups']),
        'census_reviews': len(census_rows), 'census_status_counts': dict(census_count), 'withheld_census_rows': withheld,
        'handoff_interfaces': len(export['handoff_interfaces']), 'handoff_explicit_examples': sum(len(g['representative_pairs']) for g in handoff['document']['format_groups']),
        'gallery_records': len(export['gallery_records']), 'integrity': export['integrity'],
        'source_check_count': len(export['source_checks']), 'evidence_check_count': len(export['evidence_checks'])}
    (OUT / 'export_receipt.json').write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print('EXPORT_COMPLETE', json.dumps({key: value for key, value in summary.items() if key != 'chunks'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
