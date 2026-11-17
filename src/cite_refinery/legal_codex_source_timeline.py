"""017: source-bound judicial chronologies; never silently made into operational logs.

The reader checks exact publisher bytes and paragraph hashes. Curated English
labels remain analyst interpretations. Judgment dates, recounted event dates,
source capture times and officials' first-known times are separate fields.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET

SCHEMA = 'legal_codex.judicial_timeline.v1'
SOURCE_PINS = {
    'district_2025': ('ECLI:NL:RBGEL:2025:1418','2025-02-24',
        'ef921c14b3b16839a80576f10060980d16f981b0de802eebaf75acf7f88fb45c'),
    'appeal_2026': ('ECLI:NL:RVS:2026:1753','2026-03-25',
        'ec95e84a24c592bbece23f336fdbc17043720e9c353d3f84932d5c0e86cd6357'),
    'comparator_2021': ('ECLI:NL:RVS:2021:1729','2021-08-04',
        '8f2fb3abd047cde8bd61616e2b45474422895a733647ccd3433aa2b6cc6c173e'),
}
CASE_SOURCES = {
    'benefits_2023': {'district_2025','appeal_2026'},
    'child_budget_2014': {'comparator_2021'},
}
METHOD = 'judicial-reconstruction-017-v1'
D = 'http://purl.org/dc/terms/'
ROLES = {'reported_procedural_event','court_finding','party_submission','court_order'}
HEX = re.compile(r'[a-f0-9]{64}\Z')


def normalize(value):
    return re.sub(r'\s+', ' ', value).strip()


def digest(value):
    data = value if isinstance(value, bytes) else json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(',',':')).encode()
    return hashlib.sha256(data).hexdigest()


def read_xml(raw, ecli):
    if not isinstance(raw, bytes) or not 40 < len(raw) <= 1024*1024:
        raise ValueError('source outside byte budget')
    text = raw.decode('utf-8-sig')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('XML entity declarations rejected')
    root = ET.fromstring(raw)
    if ecli not in [x.text for x in root.iter('{'+D+'}identifier')]:
        raise ValueError('ECLI identity mismatch')
    bodies = [x for x in root.iter() if x.tag.rsplit('}',1)[-1]=='uitspraak']
    if len(bodies)!=1:
        raise ValueError('one judicial ruling body required')
    body=bodies[0]
    full=normalize(' '.join(body.itertext()))
    paragraphs={f'p{i:04d}':normalize(' '.join(p.itertext()))
                for i,p in enumerate([x for x in body.iter()
                    if x.tag.rsplit('}',1)[-1]=='para'],1)}
    relations=[]
    for element in root.iter('{'+D+'}relation'):
        relations.extend(v for k,v in element.attrib.items()
                         if k.rsplit('}',1)[-1]=='resourceIdentifier')
    return {'text':full,'paragraphs':paragraphs,'relations':relations,
            'dates':[x.text for x in root.iter('{'+D+'}date')],
            'publication_metadata':[x.text for x in root.iter('{'+D+'}issued')]}


def load_sources(folder):
    """Read-only snapshot recheck; neither legal certification nor an external signature."""
    root=Path(folder)
    receipt=json.loads((root/'receipt.json').read_text(encoding='utf-8'))
    if receipt.get('schema')!='legal_codex.judicial_capture_017.v1':
        raise ValueError('wrong acquisition receipt')
    entries=receipt.get('attempts',[])
    ids=[s.get('source_id') for s in entries]
    if len(ids)!=len(set(ids)) or set(ids)!=set(SOURCE_PINS):
        raise ValueError('missing or duplicate source receipts')
    sources={}
    for row in entries:
        sid=row['source_id'];ecli,decided,pinned=SOURCE_PINS[sid]
        expected_url='https://data.rechtspraak.nl/uitspraken/content?Id='+ecli
        if (row.get('status')!='captured_and_reextracted' or row.get('source_url')!=expected_url
            or row.get('tls_hostname_verified') is not True
            or row.get('source_kind')!='published_judgment'
            or row.get('is_original_operational_log') is not False
            or row.get('legal_authenticity_certified') is not False):
            raise ValueError('source provenance or evidence tier mismatch')
        stamp=datetime.fromisoformat(row['attempted_at'].replace('Z','+00:00'))
        if stamp.tzinfo is None:raise ValueError('capture timestamp timezone missing')
        path=root/(sid+'.xml')
        if path.is_symlink():raise ValueError('source symlink refused')
        raw=path.read_bytes()
        if digest(raw)!=pinned or row.get('raw_sha256')!=pinned:
            raise ValueError('source snapshot changed: review and version update required')
        parsed=read_xml(raw,ecli)
        if decided not in parsed['dates'] or digest(parsed['text'].encode())!=row.get('text_sha256'):
            raise ValueError('source date or text extraction mismatch')
        sources[sid]={**parsed,'source_id':sid,'ecli':ecli,'decided_on':decided,
            'source_url':expected_url,'captured_at':row['attempted_at'],
            'raw_sha256':pinned,'text_sha256':row['text_sha256'],'_raw_bytes':raw}
    if (SOURCE_PINS['district_2025'][0] not in sources['appeal_2026']['relations'] or
        SOURCE_PINS['appeal_2026'][0] not in sources['district_2025']['relations']):
        raise ValueError('official same-proceeding relationship not established')
    return sources


def validate(bundle, sources):
    if (not isinstance(bundle,dict) or set(bundle)!={'schema','mode','method','facts','case_ids'}
        or bundle['schema']!=SCHEMA or bundle['mode']!='judicial_reconstruction'
        or bundle['method']!=METHOD or set(bundle['case_ids'])!=set(CASE_SOURCES)
        or len(bundle['case_ids'])!=len(CASE_SOURCES)):
        raise ValueError('unsupported timeline mode or method')
    if set(sources)!=set(SOURCE_PINS):raise ValueError('three verified snapshots required')
    for sid,src in sources.items():
        ecli,decided,pin=SOURCE_PINS[sid]
        raw=src.get('_raw_bytes')
        if not isinstance(raw,bytes) or digest(raw)!=pin:
            raise ValueError('source bytes required; receipt flags alone are not evidence')
        canonical=read_xml(raw,ecli)
        if any(src.get(k)!=canonical[k] for k in canonical):
            raise ValueError('source text or relation differs from original bytes')
        if (src.get('ecli')!=ecli or src.get('decided_on')!=decided or
            src.get('source_url')!='https://data.rechtspraak.nl/uitspraken/content?Id='+ecli or
            src.get('raw_sha256')!=pin or src.get('text_sha256')!=digest(canonical['text'].encode())):
            raise ValueError('source metadata mismatch')
    seen=set()
    fields={'id','case_id','source_id','paragraph_id','paragraph_sha256','day',
            'day_basis','date_token','role','summary','first_known_at','first_known_actor',
            'money_effect'}
    if not isinstance(bundle['facts'],list) or not bundle['facts']:
        raise ValueError('nonempty facts required')
    for f in bundle['facts']:
        if not isinstance(f,dict) or set(f)!=fields:raise ValueError('fact schema mismatch')
        if not re.fullmatch('[a-z][a-z0-9_]{2,70}',str(f['id'])) or f['id'] in seen:
            raise ValueError('duplicate or invalid fact identity')
        seen.add(f['id'])
        if f['case_id'] not in CASE_SOURCES or f['source_id'] not in CASE_SOURCES[f['case_id']]:
            raise ValueError('cross-case evidence transplant')
        src=sources[f['source_id']]
        quote=src['paragraphs'].get(f['paragraph_id'])
        if not quote or digest(quote.encode())!=f['paragraph_sha256']:
            raise ValueError('paragraph anchor mismatch')
        day=date.fromisoformat(f['day'])
        if day>date.fromisoformat(src['decided_on']):raise ValueError('event after cited judgment')
        if f['day_basis']=='exact_date_in_text':
            if not f['date_token'] or f['date_token'] not in quote:
                raise ValueError('event date lacks exact source anchor')
            months={'januari':1,'februari':2,'maart':3,'april':4,'mei':5,'juni':6,
                    'juli':7,'augustus':8,'september':9,'oktober':10,'november':11,'december':12}
            parts=f['date_token'].split()
            if len(parts)!=3 or date(int(parts[2]),months.get(parts[1],0),int(parts[0]))!=day:
                raise ValueError('ISO event date and Dutch source date disagree')
        elif f['day_basis']=='judgment_date':
            if f['day']!=src['decided_on'] or f['date_token'] is not None:
                raise ValueError('court observation cannot be backdated')
        else:raise ValueError('unsupported date precision')
        pinned_roles={'phone_contact_claim':'party_submission','agency_argument_recorded':'party_submission',
            'district_hearing_breach':'court_finding','appeal_hearing_ground_rejected':'court_finding',
            'appeal_missing_agency_form':'court_finding','appeal_zero_recovery':'court_order',
            'appeal_other_parts_upheld':'court_order','district_recovery_upheld':'court_order',
            'comparator_recovery_upheld':'court_order'}
        if f['id'] in pinned_roles and f['role']!=pinned_roles[f['id']]:
            raise ValueError('party submission or court role cannot be promoted')
        operative_anchors={'district_hearing_breach':('district_2025','p0037'),
            'appeal_hearing_ground_rejected':('appeal_2026','p0035'),
            'appeal_missing_agency_form':('appeal_2026','p0046'),
            'appeal_zero_recovery':('appeal_2026','p0057'),
            'appeal_other_parts_upheld':('appeal_2026','p0059'),
            'district_recovery_upheld':('district_2025','p0060'),
            'comparator_recovery_upheld':('comparator_2021','p0045')}
        if f['id'] in operative_anchors and (f['source_id'],f['paragraph_id'])!=operative_anchors[f['id']]:
            raise ValueError('operative or disconfirming source anchor changed')
        if f['role'] not in ROLES or not isinstance(f['summary'],str) or len(f['summary'])<25:
            raise ValueError('unreviewed fact role/summary invalid')
        if f['first_known_at'] is not None or f['first_known_actor'] is not None:
            raise ValueError('judgments do not establish operational first-known timestamps')
        if f['money_effect'] not in {None,'recovery_order','court_ordered_zero_recovery'}:
            raise ValueError('cash refund/payment not established by these sources')
    return True


def build(bundle, sources):
    validate(bundle,sources)
    facts=[]
    for f in sorted(bundle['facts'],key=lambda x:(x['day'],x['id'])):
        src=sources[f['source_id']];quote=src['paragraphs'][f['paragraph_id']]
        facts.append({**deepcopy(f),'source_ecli':src['ecli'], 'source_url':src['source_url'],
            'source_decided_on':src['decided_on'],'source_captured_at':src['captured_at'],
            'source_raw_sha256':src['raw_sha256'],'source_quote':quote,
            'evidence_tier':'published_judicial_account',
            'native_language':'nl','summary_language':'en',
            'independent_legal_translation_reviewed':False,
            'is_operational_log_entry':False})
    by_id={f['id']:f for f in facts}
    required={'district_hearing_breach','appeal_hearing_ground_rejected',
              'appeal_missing_agency_form','appeal_zero_recovery','appeal_other_parts_upheld',
              'district_recovery_upheld','comparator_recovery_upheld','original_recovery'}
    if not required.issubset(by_id):raise ValueError('disconfirming/operative findings must not be omitted')
    return {'schema':'legal_codex.judicial_timeline_result.v1',
        'mode':'judicial_reconstruction','fact_count':len(facts),'facts':facts,
        'source_count':len(sources),'case_count':len(CASE_SOURCES),
        'official_same_case_link':{'from':SOURCE_PINS['district_2025'][0],
            'to':SOURCE_PINS['appeal_2026'][0],'basis':'reciprocal_official_ECLI_metadata',
            'relationship':'appeal_partly_reverses_recovery_not_all_holdings'},
        'ground_distinctions':[
            {'issue':'hearing_duty','finding':'breach_found_but_no_separate_appellate_relief',
             'fact_ids':['district_hearing_breach','appeal_hearing_ground_rejected']},
            {'issue':'agency_record_uncertainty_and_proportionality',
             'finding':'case_specific_recovery_waiver',
             'fact_ids':['appeal_missing_agency_form','appeal_zero_recovery']},
            {'issue':'benefit_reassessment','finding':'otherwise_upheld',
             'fact_ids':['appeal_other_parts_upheld']},
            {'issue':'other_case_2021','finding':'recovery_upheld_not_automatic_waiver',
             'fact_ids':['comparator_recovery_upheld']}],
        'operational_replay_admission':{'allowed':False,
            'missing':['contemporaneous decision logs','actor-specific first-known times',
                       'authenticated source-system event identity','actual execution/collection records'],
            'published_judgments_are_not_operational_logs':True},
        'court_waiver_is_not_cash_refund':True,'observed_prevention_established':False,
        'original_operational_logs_obtained':0,'real_action_executed':False,
        'input_sha256':digest(bundle),'publication_authorized':False}


def as_of(report, case_id, checkpoint):
    """Show retrospective history without pretending it was known at a past checkpoint."""
    if report.get('mode')!='judicial_reconstruction' or case_id not in CASE_SOURCES:
        raise ValueError('wrong evidence tier/case')
    day=date.fromisoformat(checkpoint)
    rows=[f for f in report['facts'] if f['case_id']==case_id]
    return {'case_id':case_id,'checkpoint':checkpoint,
        'retrospectively_dated_events_by_checkpoint':[f['id'] for f in rows if date.fromisoformat(f['day'])<=day],
        'findings_reported_only_by_later_judgments':[f['id'] for f in rows
            if date.fromisoformat(f['source_decided_on'])>day],
        'operational_evidence_available_at_checkpoint':None,
        'why_unknown':'Judicial recollection dates are not actor-specific evidence-receipt timestamps.',
        'may_drive_016_operational_replay':False}


def to_operational_replay(*_args, **_kwargs):
    raise ValueError('Admission refused: judicial accounts cannot be converted into authenticated operational logs')


def semantic_packet(bundle,sources,result):
    if result!=build(bundle,sources):raise ValueError('stale/fabricated timeline result')
    nodes=[];edges=[]
    for sid,s in sources.items():
        nodes.append({'key':sid,'kind':'source','layer':'neutral','statement':s['ecli'],
                      'source_refs':[s['source_url']]})
    for f in result['facts']:
        nodes.append({'key':f['id'],'kind':'observation','layer':'neutral','statement':f['summary'],
            'source_refs':[f['source_url']], 'provenance':{
                'source_paragraph':f['paragraph_id'],'source_sha256':f['source_raw_sha256'],
                'event_day':f['day'],'court_report_day':f['source_decided_on'],
                'operational_first_known_at':None,'is_operational_log':False}})
        edges.append({'source':f['source_id'],'target':f['id'],
                      'relation':'REPORTS_JUDICIAL_CHRONOLOGY','status':'candidate'})
    edges.append({'source':'district_2025','target':'appeal_2026',
                  'relation':'REVIEWED_IN_LATER_APPEAL','status':'candidate'})
    return {'schema':'cite_refinery.semantic_graph.v1','source_system':'judicial-chronology-017',
            'clusters':[],'nodes':nodes,'edges':edges}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture');p.add_argument('--fixture-output');p.add_argument('--evidence-dir',required=True)
    p.add_argument('--output',required=True);p.add_argument('--packet')
    a=p.parse_args(argv);sources=load_sources(a.evidence_dir)
    from .legal_codex_source_timeline_catalogue import make_fixture
    bundle=json.loads(Path(a.fixture).read_text(encoding='utf-8')) if a.fixture else make_fixture(sources)
    result=build(bundle,sources)
    if a.fixture_output:Path(a.fixture_output).write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if a.packet:Path(a.packet).write_text(json.dumps(semantic_packet(bundle,sources,result),indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'source_snapshots':len(sources),'source_anchored_facts':result['fact_count'],
                     'operational_logs':0,'operational_replay_admitted':False}))


if __name__=='__main__':main()
