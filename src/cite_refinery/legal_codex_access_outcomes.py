"""019: source-bound access outcomes and discovered citation links.

Outcome labels are curated legal readings, not automatically adjudicated facts.
Citation extraction is automatic; a mention is not applicability, implementation,
causation or verified disclosure. Core snapshots are separate from failed leads.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re

SOURCE_PINS = {
 'hospital_2024': ('07ec228478be9ac33af309aca898b0985431d743645c7ace82ef655f7b384a88','2024-08-26','healthcare'),
 'hospital_2026': ('5aa98b1a7c7c07aeb43fc5177233fc14b1a465f13466911a0132dfbeda7ba1ae','2026-09-30','healthcare'),
 'staff_identity_2025': ('f7c4048e7dffabfc112e33106474c6b00e0fad3ee20f3534f6873f17ea2162c7','2025-07-16','public_administration'),
 'contact_center_2026': ('c60d07c96460348536924e3aaa8430996e8cf0323448f342812a8212dd82cc78','2026-06-01','institutional_advice'),
}
# The policy site's HTML wrapper varies between captures while every extracted
# block is unchanged. Preserve each raw receipt, and separately pin the complete
# extracted document. A changed substantive text still requires manual review.
POLICY_TEXT_PIN='899eaa5676b97f48d54b80ec9ae12b7ced3ac2e7649b2937b68187f457615ef7'
# Reviewed source-specific selections. Test counts measure code, not interpretation accuracy.
ANNOTATIONS = (
 ('hospital_2024','p0113','court_reasoning','staff_identity','roles_can_suffice',
  'The court accepted role descriptions without employee names for this access request and rejected a blanket demand for identities.'),
 ('hospital_2024','p0141','operative_order','access','log_overviews_ordered',
  'The hospital was ordered to provide intelligible log overviews within one month, respecting others rights; later delivery is not proved by the order.'),
 ('hospital_2024','p0143','operative_order','enforcement','conditional_penalty_ordered',
  'A conditional penalty of EUR 100 per day, capped at EUR 1,000 per separate order, was imposed; no payment or accrual is verified here.'),
 ('hospital_2026','p0057','court_records_claimant_confirmation','delivery','prior_logs_received_as_recorded',
  'The judgment records the claimant confirming receipt of log overviews on 7 September 2026; possession of those private files is not claimed by this project.'),
 ('hospital_2026','p0059','court_reasoning','format','requested_standard_not_required_on_this_basis',
  'The court did not treat Article 15 alone as a right to the requested NEN 7513-format overview in this proceeding.'),
 ('hospital_2026','p0067','court_records_claimant_confirmation','delivery','medical_copy_received_as_recorded',
  'The claimant confirmed receipt of the medical-file copy; the court treated that part of the access request as fulfilled.'),
 ('hospital_2026','p0100','operative_order','intelligibility','specific_data_and_purpose_explanation_ordered',
  'The hospital was ordered to explain which personal data staff had consulted and for what purposes; prior receipt of an overview did not satisfy this part.'),
 ('hospital_2026','p0102','operative_order','staff_identity','specification_subject_to_privacy_ordered',
  'The court ordered further specification of the staff responsible for logged activities where not already done, with protection of staff and third-party rights.'),
 ('hospital_2026','p0091','court_reasoning','enforcement','requested_penalty_not_imposed',
  'The court declined the requested conditional penalty in light of the hospital assurance of compliance; this is not proof of subsequent performance.'),
 ('staff_identity_2025','p0035','court_assessment_based_on_record','traceability','earlier_access_not_reconstructable',
  'The court recorded that no logging data were available for the earlier period and limited its identity analysis to the later period; this does not prove intentional deletion.'),
 ('staff_identity_2025','p0038','court_reasoning','staff_identity','employee_names_not_necessary_in_this_case',
  'The court found the identities of instructed employees unnecessary in this case; knowing the controller and number of staff sufficed for the stated damages route.'),
 ('staff_identity_2025','p0051','operative_order','staff_identity','lower_identity_disclosure_requirement_reversed',
  'The appellate court reversed the lower judgment only insofar as it required disclosure of individual employee identities.'),
 ('contact_center_2026','p0011','published_advisory_status','implementation','procurement_not_yet_awarded_at_report',
  'At the publication of this 2026 advice, procurement was described as in dialogue and not yet awarded. This does not certify any 2023 logging implementation or current November deployment.'),
)
DASHES=str.maketrans({c:'-' for c in '\u2010\u2011\u2012\u2013\u2014\u2212'})
REFERENCE=re.compile(r'ECLI:[A-Z]{2}:[A-Z0-9]+:\d{4}:[A-Z0-9]+|\bC\s*-\s*\d{1,4}/\d{2}\b')


def digest(value):
 raw=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
 return hashlib.sha256(raw).hexdigest()


def _capture_module():
 path=Path(__file__).resolve().parents[2]/'scripts/legal_codex_capture_019.py'
 spec=importlib.util.spec_from_file_location('legal_codex_fixed_capture_019',path)
 if spec is None or spec.loader is None:raise ValueError('capture/parser implementation missing')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module


def load_sources(folder):
 root=Path(folder);capture=_capture_module()
 receipt=json.loads((root/'receipt.json').read_text(encoding='utf-8'))
 if receipt.get('schema')!='legal_codex.cross_case_sources_019.v1':raise ValueError('wrong source receipt')
 rows=receipt.get('sources',[])
 if not isinstance(rows,list) or len({r.get('source_id') for r in rows})!=len(rows):raise ValueError('duplicate or malformed source receipt')
 registry={r['source_id']:r for r in rows};result={}
 if not set(SOURCE_PINS).issubset(registry):raise ValueError('required curated source omitted')
 for sid,(pin,decided,sector) in SOURCE_PINS.items():
  row=registry[sid];url,fmt,ident=capture.SOURCES[sid]
  if (row.get('status')!='captured_and_reextracted' or row.get('url')!=url or row.get('final_url')!=url
      or row.get('tls_hostname_verified') is not True):
   raise ValueError('source identity/status mismatch: '+sid)
  when=datetime.fromisoformat(row['attempted_at'].replace('Z','+00:00'))
  if when.tzinfo is None:raise ValueError('capture timezone missing')
  path=root/(sid+'.'+fmt)
  if path.is_symlink():raise ValueError('source symlink rejected')
  raw=path.read_bytes();actual_hash=digest(raw)
  if actual_hash!=row.get('raw_sha256'):raise ValueError('capture receipt/body hash mismatch')
  if fmt=='xml' and actual_hash!=pin:
   raise ValueError('judicial snapshot changed; explicit re-review required')
  doc=capture.extract(raw,fmt,ident)
  if fmt=='html' and digest(doc)!=POLICY_TEXT_PIN:
   raise ValueError('policy source text changed; explicit re-review required')
  if fmt=='xml' and decided not in doc['metadata']['decision_dates']:raise ValueError('judgment date mismatch')
  saved=json.loads((root/(sid+'.json')).read_text(encoding='utf-8'))
  if saved!=doc:raise ValueError('saved extraction differs from source bytes')
  result[sid]={**doc,'source_url':url,'source_id':sid,'raw_sha256':actual_hash,'date':decided,
               'date_kind':'decision_date' if fmt=='xml' else 'publication_date',
               'sector':sector,'captured_at':row['attempted_at'],
               'raw_matches_initial_snapshot':actual_hash==pin,
               'version_check':'exact_xml_bytes' if fmt=='xml' else 'complete_extracted_policy_document'}
 return result,receipt


def discover_references(blocks):
 """Literal reference extraction. Do NOT repair a plausible but wrong case ID."""
 hits=[]
 for b in blocks:
  original=b['text'];normalized=original.translate(DASHES)
  for m in REFERENCE.finditer(normalized):
   token=re.sub(r'\s+','',m.group())
   hits.append({'reference':token,'block_id':b['id'],'block_sha256':digest(original.encode()),
                'relation':'EXPLICIT_REFERENCE_ONLY','legal_applicability_inferred':False})
 return hits


def build(folder):
 sources,receipt=load_sources(folder);observations=[];references=[]
 for sid,s in sources.items():
  if s['format']=='xml':
   for hit in discover_references(s['blocks']):references.append({'source_id':sid,**hit})
 for n,(sid,bid,role,dimension,status,label) in enumerate(ANNOTATIONS,1):
  source=sources[sid];block=next((b for b in source['blocks'] if b['id']==bid),None)
  if block is None or not block['text']:raise ValueError('selected evidence block missing')
  observations.append({'id':f'observation_{n:02d}','source_id':sid,'source_identity':source['identity'],
   'source_url':source['source_url'],'source_date':source['date'],'source_date_kind':source['date_kind'],
   'publication_values':source['metadata'].get('publication_values',[]),
   'paragraph_id':bid,'paragraph_sha256':block['sha256'],'source_quote':block['text'],
   'source_language':'nl','label_language':'en','label':label,'evidence_role':role,
   'dimension':dimension,'outcome_status':status,'analyst_interpretation_independently_reviewed':False,
   'subsequent_compliance_verified':False,'claimant_records_acquired':False})
 target_ids={s['identity']:sid for sid,s in sources.items() if s['format']=='xml'}
 links=[]
 for h in references:
  target=target_ids.get(h['reference'])
  if target and target!=h['source_id']:
   links.append({'from_source':h['source_id'],'to_source':target,'reference':h['reference'],
                 'source_block':h['block_id'],'relationship':'literal_judicial_citation',
                 'same_proceeding_proven':False,'causal_effect_proven':False})
 statuses=[{'source_id':r['source_id'],'status':r['status'],'detail':r.get('detail')}
           for r in receipt['sources']]
 return {'schema':'legal_codex.access_outcomes_019.v1','as_of':'2026-11-18',
  'curated_judgments':3,'captured_core_sources':len(sources),'source_status':statuses,
  'source_versions':[{'source_id':s['source_id'],'raw_sha256':s['raw_sha256'],
                     'raw_matches_initial_snapshot':s['raw_matches_initial_snapshot'],
                     'version_check':s['version_check']} for s in sources.values()],
  'observations':observations,'discovered_reference_mentions':references,'cross_case_citations':links,
  'unresolved_literal_references':[h for h in references if h['reference']=='ECLI:EU:C:2023:50'],
  'rule_scope':'Shared EU data-access law; not automatic transplantation to Indonesia.',
  'selection':'Purposefully selected discovery cases; not a representative effectiveness sample.',
  'observed_prevention_established':False,'subsequent_order_execution_verified':False,
  'private_medical_or_tax_logs_obtained':0,'staff_identity_or_guilt_inferred':False,
  'requests_submitted':0,'publication_authorized':False}


def admission(result):
 """Legal orders and reported receipts are not this project's private operational logs."""
 if result.get('schema')!='legal_codex.access_outcomes_019.v1':raise ValueError('wrong evidence tier')
 return {'operational_replay_allowed':False,'missing':['lawful case-specific original records',
     'record version and authentic event provenance','actor-specific availability timestamps',
     'evidence of execution of the particular outstanding order'],
     'reason':'Published judgments can report receipt while our project still possesses no underlying logs.'}


def semantic_packet(folder,result):
 if result!=build(folder):raise ValueError('modified or stale outcome report refused')
 sources,_=load_sources(folder);nodes=[];edges=[]
 for sid,s in sources.items():
  nodes.append({'key':sid,'kind':'source','layer':'neutral','statement':s['identity'],
                'source_refs':[s['source_url']]})
 for row in result['observations']:
  nodes.append({'key':row['id'],'kind':'observation','layer':'neutral','statement':row['label'],
    'source_refs':[row['source_url']], 'provenance':{'role':row['evidence_role'],
     'outcome_scope':row['dimension'],'paragraph_sha256':row['paragraph_sha256'],
     'execution_verified':False,'independent_legal_review':False}})
  edges.append({'source':row['source_id'],'target':row['id'],
                'relation':'REPORTS_SCOPED_ACCESS_OUTCOME','status':'candidate'})
 unique={(r['from_source'],r['to_source']) for r in result['cross_case_citations']}
 for before,after in sorted(unique):
  edges.append({'source':before,'target':after,'relation':'EXPLICITLY_CITES_OTHER_DECISION',
                'status':'candidate','provenance':{'same_case':False,'causation_established':False}})
 return {'schema':'cite_refinery.semantic_graph.v1','source_system':'access-outcomes-019',
         'clusters':[],'nodes':nodes,'edges':edges}


def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence-dir',required=True)
 p.add_argument('--output',required=True);p.add_argument('--packet');args=p.parse_args(argv)
 result=build(args.evidence_dir)
 Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 if args.packet:Path(args.packet).write_text(json.dumps(semantic_packet(args.evidence_dir,result),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print(json.dumps({'core_source_snapshots':result['captured_core_sources'],
   'curated_outcome_observations':len(result['observations']),
   'literal_citation_mentions':len(result['discovered_reference_mentions']),
   'private_original_logs_obtained':0,'subsequent_execution_verified':False}))
if __name__=='__main__':main()
