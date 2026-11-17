"""018: original-record recovery plan, not a dossier access or submission service.
Public descriptions locate possible records; they do not prove record survival
or authorize access. Outputs are unsent drafts, with no live submission API.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path

DPIA='https://informatiepuntkinderopvangtoeslag.rijksoverheid.nl/publicaties/9ebc0f244fb97cc58dbe3fb626e92a82/183622021-24-11-geb-interactieve-dienstverlening-v101pdfpdf.pdf'
PRIVACY='https://www.belastingdienst.nl/wps/wcm/connect/nl/toeslagen/content/privacyverklaring-toeslagen'
PORTAL='https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/prive/toeslagen/hoe_werken_toeslagen/mijn-toeslagen/hoe-werkt-mijn-toeslagen'
WOO='https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/prive/toeslagen/hoe_werken_toeslagen/ik_wil_informatie_over_toeslagen/ik_wil_vragen_om_informatie_openbaar_te_maken'
LOGS='https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62021CJ0579'
COPIES='https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62021CJ0487'
MINISTER='https://zoek.officielebekendmakingen.nl/kst-36708-28.html'
SOURCES={
 'dpia_2021':{'url':DPIA,'version_date':'2021-11-24','tier':'institutional_design_assessment'},
 'privacy':{'url':PRIVACY,'version_date':None,'tier':'current_public_policy'},
 'portal':{'url':PORTAL,'version_date':None,'tier':'current_public_policy'},
 'woo':{'url':WOO,'version_date':None,'tier':'current_access_guidance'},
 'cjeu_logs':{'url':LOGS,'version_date':'2023-06-22','tier':'EU_access_law_interpretation'},
 'cjeu_copies':{'url':COPIES,'version_date':'2023-05-04','tier':'EU_access_law_interpretation'},
 'ministerial_2025':{'url':MINISTER,'version_date':'2025-07-14','tier':'ministerial_account_of_access_routes'},
}
TARGETS=(
 {'id':'application_versions','record':'Original 12 April 2023 application and income-field version history',
  'location':'Benefit source-system owner, separate from the interaction platform',
  'source_ids':['dpia_2021','cjeu_copies','ministerial_2025'],
  'route':'subject_access_or_procedural_file','scope':'personal',
  'question':'Which source document and field values were submitted, by which channel, and what changed before the January 2024 decision?',
  'required':['original field values and versions','event timestamps with timezone','source-system identifiers','link to decision input version'],
  'limit':'Interaction notes are not a substitute for the application itself.'},
 {'id':'desk_appointment','record':'Desk appointment/attendance metadata for 12 April 2023',
  'location':'JCC desk platform is named in the 2021 assessment; case deployment unverified',
  'source_ids':['dpia_2021'], 'route':'subject_access','scope':'personal',
  'question':'Does a preserved appointment/attendance event exist, and can it be linked lawfully to the application interaction?',
  'required':['contact or appointment identifier','channel','actual event time','retention and migration history'],
  'limit':'Attendance alone does not establish what was entered or who caused an error.'},
 {'id':'contact_history','record':'KCH contact history, notes and analytical-store copy',
  'location':'Customer-contact history (KCH), transfer notes/Frobo where relevant, and analytical environment',
  'source_ids':['dpia_2021','cjeu_copies'], 'route':'subject_access','scope':'personal',
  'question':'Were the interaction records searched in both the user-facing system and analytical environment?',
  'required':['original note and edit history','contact identifier','source and migration dates','search scope and result'],
  'limit':'The 2021 retention description is not proof of record survival or a current statutory retention deadline.'},
 {'id':'consultation_audit','record':'Dates and purposes of consultations of personal data',
  'location':'Access/audit-log owner; distinguish ordinary interaction logging from access monitoring',
  'source_ids':['dpia_2021','cjeu_logs'], 'route':'subject_access','scope':'personal',
  'question':'What access events can be disclosed under Article 15, and what did the historical logging actually record?',
  'required':['event date and purpose','data/version or object consulted if available','historical logging coverage','role-based identifiers where lawfully releasable'],
  'limit':'An access event does not prove comprehension or first knowledge; employee names are not automatically disclosable.'},
 {'id':'objection_hearing','record':'28 February 2024 contact and hearing invitation/waiver record',
  'location':'Objection case-file owner; phone recording only if the relevant channel recorded and retained it',
  'source_ids':['privacy','ministerial_2025','dpia_2021'], 'route':'procedural_file_or_subject_access','scope':'personal',
  'question':'What contemporaneous record establishes what was offered, said and agreed during objection handling?',
  'required':['invitation and response','actual note or available recording','call-channel identification','record creation date'],
  'limit':'The current BelastingTelefoon 90-day rule cannot be assigned automatically to this objection call.'},
 {'id':'decision_inputs','record':'Original January/March 2024 decisions and input/approval trail',
  'location':'Dienst Toeslagen source system and corresponding procedural case file',
  'source_ids':['portal','ministerial_2025','cjeu_copies'], 'route':'subject_access_or_procedural_file','scope':'personal',
  'question':'Which evidence version was used at each decision, and when was it available to the decision process?',
  'required':['original decision','input snapshot','decision and notification times','review/approval provenance'],
  'limit':'Portal correspondence can locate decisions but is not a complete original event log.'},
 {'id':'execution_ledger','record':'Collection, offset, cancellation and refund postings after the court decision',
  'location':'Toeslagen payment/recovery administration; claimant-side statements only with consent',
  'source_ids':['portal','privacy'], 'route':'subject_access','scope':'personal',
  'question':'Was anything collected, later cancelled, offset or returned, independently of what the court ordered?',
  'required':['posting type and time','amount/currency','case and transaction links','reversal or settlement reference'],
  'limit':'Zero recovery ordered is not proof of refund, and a portal payment total is not necessarily a refund ledger.'},
 {'id':'historical_control_documents','record':'Historical system mapping, retention, migration and logging implementation documents',
  'location':'Dienst Toeslagen/KI&S policy and records-management owners',
  'source_ids':['dpia_2021','woo'], 'route':'public_policy_woo','scope':'nonpersonal',
  'question':'Which systems and controls were deployed in April 2023 and January/March 2024, rather than merely planned?',
  'required':['dated implementation/acceptance records','historical retention schedule and scope','data migration/deletion procedure','nonpersonal search methodology'],
  'limit':'A planned 31 December 2023 logging measure is not evidence of implementation by that date.'},
)

def digest(x):
 return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def search_plan(*, requester='external_researcher'):
 """Select a draft route; no interface verifies or accepts a claimant mandate."""
 if requester!='external_researcher':
  raise ValueError('No authenticated representation adapter; do not assert claimant authority')
 records=[]
 for target in TARGETS:
  records.append({**deepcopy(target),
   'source_urls':[SOURCES[s]['url'] for s in target['source_ids']],
   'draft_status':'UNSENT',
   'access_gate':'claimant_or_verified_representative_required' if target['scope']=='personal' else 'public_policy_request_draft_only',
   'original_obtained':False,'record_survival':'unknown',
   'operational_first_known_at':None,'independent_legal_review':'pending'})
 return {'schema':'legal_codex.original_record_plan_018.v1','as_of':'2026-11-18',
  'requester':requester,'case_reference':'ECLI:NL:RBGEL:2025:1418 -> ECLI:NL:RVS:2026:1753',
  'targets':records,'claimant_identified':False,'claimant_originals_obtained':0,
  'private_portals_accessed':0,'requests_submitted':0,'operational_replay_admitted':False,
  'catalogue_sha256':digest(TARGETS),'publication_authorized':False}

def retention_lead(*, record_class, source_version='2021-11-24', event_day='2023-04-12'):
 """Report what the historical policy suggests searching, not record existence."""
 if source_version!='2021-11-24':raise ValueError('Unreviewed retention-policy version')
 date.fromisoformat(event_day)
 if record_class=='contact_history':
  windows={'user_system':'2 years described','analytical_environment':'7 years described'}
  targets=['user_system','analytical_environment','migration_and_deletion_audit']
 elif record_class=='interaction_data':
  windows={'interaction_records':'7 years after end of contact year described'}
  targets=['interaction_records','retention_scope_and_actual_implementation']
 elif record_class=='benefit_application':
  windows={'source_system':'not specified by this interaction assessment'}
  targets=['benefit_source_system_owner','applicable_source_system_retention_schedule']
 else:raise ValueError('Record category not covered by this historical assessment')
 return {'record_class':record_class,'source_version':source_version,'event_day':event_day,
  'described_windows':windows,'candidate_search_locations':targets,
  'actual_record_exists':None,'actual_deletion_date':None,'retained_until_guaranteed':None,
  'historical_implementation_verified':False}

def classify_observation(*, kind, record_id, observed_at):
 """Refusal, failed search, plans and court orders are not destruction or payments."""
 allowed={'not_found_in_frontend','search_returned_no_match','access_refused',
          'retention_policy_found','control_planned','consultation_date_reported',
          'court_order_found','public_policy_found'}
 if kind not in allowed:raise ValueError('Unverified original or unsupported observation type')
 if record_id not in {r['id'] for r in TARGETS}:raise ValueError('Unknown target record')
 date.fromisoformat(observed_at)
 actions={
  'not_found_in_frontend':'check_analytical_or_archive_locations_and_search_scope',
  'search_returned_no_match':'obtain_dated_search_scope_and_coverage_explanation',
  'access_refused':'record_legal_basis_and_review_route_not_record_absence',
  'retention_policy_found':'verify_historical_scope_and_actual_retention',
  'control_planned':'seek_dated_implementation_evidence',
  'consultation_date_reported':'seek_object_version_and_decision_link_not_infer_understanding',
  'court_order_found':'seek_separate_execution_entries',
  'public_policy_found':'retain_as_location_lead_not_individual_evidence'}
 return {'record_id':record_id,'observation':kind,'observed_at':observed_at,
  'next_evidence_step':actions[kind],'record_destroyed':None,'actor_first_known_at':None,
  'refund_paid':None,'operational_replay_admitted':False}

def admission_assessment(evidence):
 """018 locates possible retrieval routes; no real-log importer exists here."""
 if not isinstance(evidence,list):raise ValueError('Evidence list required')
 kinds={e.get('kind') for e in evidence if isinstance(e,dict)}
 if len(evidence)!=sum(isinstance(e,dict) for e in evidence):raise ValueError('Malformed evidence')
 allowed={'published_judgment','public_policy','access_right','location_lead','request_draft','search_response'}
 if not kinds.issubset(allowed):raise ValueError('Original operational import requires separate authorized verifier')
 return {'admitted':False,'received_evidence_tiers':sorted(kinds),
  'missing':['lawfully obtained case-specific original bytes','authenticated system/event provenance',
             'contemporaneous actor-specific knowledge timestamps','execution outcome records'],
  'public_sources_do_not_establish_case_record_survival':True}

def semantic_packet(result):
 if result!=search_plan():raise ValueError('Edited or promoted record plan refused')
 nodes=[];edges=[]
 for sid,s in SOURCES.items():
  nodes.append({'key':'access-source-'+sid,'kind':'source','layer':'neutral',
   'statement':s['tier'],'source_refs':[s['url']]})
 for target in result['targets']:
  nodes.append({'key':'record-target-'+target['id'],'kind':'concept','layer':'neutral',
   'statement':target['record'],'source_refs':target['source_urls'],
   'provenance':{'status':'unacquired_target','access_gate':target['access_gate'],'knowledge_time':None}})
  for sid in target['source_ids']:
   edges.append({'source':'access-source-'+sid,'target':'record-target-'+target['id'],
    'relation':'SUGGESTS_RECORD_LOCATION_OR_ACCESS_ROUTE','status':'candidate'})
 return {'schema':'cite_refinery.semantic_graph.v1','source_system':'record-recovery-018',
  'clusters':[],'nodes':nodes,'edges':edges}

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--packet')
 args=p.parse_args(argv);result=search_plan()
 Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 if args.packet:Path(args.packet).write_text(json.dumps(semantic_packet(result),indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'record_targets':len(result['targets']),'claimant_originals_obtained':0,'requests_submitted':0}))
if __name__=='__main__':main()
