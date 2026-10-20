"""Generate a bounded article audit + diagnostic set from a local JATS XML copy."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from cite_refinery.fulltext_audit import parse_article,anuradhapura_audit,compact_dossier

URL='https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13500148/fullTextXML'

def benchmark_cases(dossier, audit):
    t={x['id']:x for x in dossier['tables']}
    row=lambda key,*prefix: next(r for r in t[key]['rows'][1:] if r[:len(prefix)]==list(prefix))
    total=row('T3','Total');simple=row('T6B','1','Male')
    male=row('T6C','Male','1');female=row('T6C','Female','3')
    lim=next(s['text'] for s in dossier['sections'] if s['title']=='STUDY LIMITATIONS')
    disc=next(s['text'] for s in dossier['sections'] if s['title']=='DISCUSSION')
    avail=next(s['text'] for s in dossier['sections'] if s['title']=='DATA AVAILABILITY')
    note=lambda x:' '.join(x.split())
    buf=['Table 6C, columns Sex, Zone, coefficient, IRR, p, 95% CI']
    def T(key,row):return f'Published {key}: '+json.dumps(row,ensure_ascii=False)
    scope='Reported number of free-roaming dogs requiring sterilization declined from 1,368 in 2021 to 484 in 2025.'
    cases=[]
    def add(id,claim,evidence,expected,why):cases.append({'id':id,'claim':claim,'evidence':evidence,'expected':expected,'gold_reason':why})
    add('B01','The authors report 1,368 dogs requiring sterilization in 2021 versus 484 in 2025.',scope,'entailed','Directly reported eligibility-specific endpoints, not independent replication.')
    add('B02','The total number of all free-roaming dogs in Anuradhapura fell from 1,368 to 484.',scope,'overreach','Only dogs needing sterilization, not total abundance, are counted in the quoted statistic.')
    add('B03','The annual effort-adjusted total dog catch rate declined significantly at p < 0.05.',T('T3',total),'contradicted','Total IRR is 1.03 (increasing) and p=0.55488235.')
    add('B04','The reported effort-adjusted total dog count trend was not statistically significant.',T('T3',total),'entailed','Table T3 total p >0.05.')
    add('B05','The zone 1 male simple pre/post comparison was statistically significant.',T('T6B',simple),'contradicted','Table T6B zone 1 male pre/post p=0.835.')
    add('B06','The reported buffer-interaction coefficient for zone 1 male dogs has p=0.038.',T('T6C',male),'entailed','Table T6C explicitly reports p=0.038.')
    add('B07','The zone 1 male buffer coefficient proves the buffer reduced human rabies deaths.',T('T6C',male),'overreach','An association in dog catches cannot establish human rabies mortality effects.')
    add('B08','The zone 3 female buffer-interaction p-value is 0.0003.',T('T6C',female),'entailed','Table T6C gives p=0.0003 for zone 3 female.')
    add('B09','The article says supplementary data can be requested from the corresponding author.',note(avail)[:350],'entailed','The data availability section explicitly says upon request.')
    add('B10','Complete individual dog-level data are freely downloadable within the article.',note(avail)[:350],'contradicted','The paper directs the reader to request supplementary data, not an openly available file.')
    add('B11','The authors conducted systematic community-wide dog abundance surveys.',note(lim)[:550],'contradicted','Authors explicitly report being unable to conduct systematic community dog surveys.')
    bites=next((x for x in dossier['sections'] if x['title']=='STUDY LIMITATIONS'),None)
    relevant=next((p for p in bites['paragraphs'] if 'dog bites' in p.lower()),'')
    add('B12','The article acknowledges incomplete local dog-bite, PEP and rabies-case data.',relevant[:650],'entailed','Study limitations explicitly say the locality-specific data are incomplete.')
    add('B13','The researchers precisely quantified the direct effect of CNVR on local human rabies incidence.',relevant[-700:],'contradicted','Limitations state the direct contribution could not be quantified accurately.')
    add('B14','If the six Table 6C sex-by-zone p-values were tested at Bonferroni 0.05/6, the male zone 1 p=0.038 would be below that threshold.',f'Table T6C contains 6 sex/zone tests; zone 1 male p=0.038; illustrative Bonferroni threshold 0.05/6={1/120:.6f}.','contradicted','0.038 > 0.008333, conditional on illustrative correction.')
    add('B15','If the six Table 6C sex-by-zone p-values were tested at Bonferroni 0.05/6, the female zone 3 p=0.0003 would meet that threshold.',f'Table T6C contains 6 sex/zone tests; zone 3 female p=0.0003; illustrative Bonferroni threshold 0.05/6={1/120:.6f}.','entailed','0.0003 < 0.008333, conditional on illustrative correction.')
    add('B16','T6B p=0.835 and T6C p=0.038 cannot both be correct, since they estimate exactly the same effect.',f'Simple pre/post male zone1: {T("T6B",simple)}. Buffer-interaction male zone1: {T("T6C",male)}. These are separately titled estimates.','overreach','Different pre/post and buffer-interaction estimands do not have to agree in significance.')
    add('B17','The 235 identified dogs in the Smith et al. Italy/Ukraine open repository are the raw dog-level observations underlying the Anuradhapura study.',f'Original study: Anuradhapura, Sri Lanka, 2021–2025. Separate comparator: 235 uniquely identified dogs in Pescara Italy and Lviv Ukraine, survey 2018–2019, DOI 10.1371/journal.pone.0266636.','contradicted','Different geography, period, publication and data provenance.')
    add('B18','The original study directly measured the causal impact of CNVR on region-specific dog-bite and PEP outcomes.',relevant[-650:],'contradicted','Authors say inadequate direct local public-health data prevent accurately quantifying the intervention contribution.')
    effort=next((p for x in dossier['sections'] for p in x['paragraphs'] if 'intentionally implemented by project management' in p),'')
    if not effort:raise ValueError('Missing author statement on endogenous effort adjustment')
    add('B19','The paper reports that decreased catching days were partly a management response to perceived decreases in dogs.',effort[:850],'entailed','Discussion explains effort was altered in response to apparent count decline; offset interpretation should be examined.')
    add('B20','Refitting the inaccessible dog-level captures with a different effort specification would reverse the zone 1 male buffer coefficient.',f'Original dog-level data are available only upon author request. Table 6C male zone 1 buffer association p=0.038 and IRR=0.9955. No refitted alternative model results are supplied.','unresolved','Direction under an unperformed model refit is unknown; neither support nor contradiction is available.')
    add('B21','An unrelated field team later replicated the Anuradhapura zone 1 male buffer result using a controlled independent population survey.',f'Table 6C contains the original study’s zone 1 male interaction p=0.038; no independent replication source is included in this excerpt.','unresolved','A later replication cannot be established or ruled out using only this source evidence.')
    return {'schema':'cite_refinery.adjudication_benchmark.v1','source_doi':dossier['doi'],
            'source_sha256':dossier['source_sha256'],'gold_annotation':'curated_source_anchored_not_independent_human_gold',
            'cases':cases}

def main():
    p=argparse.ArgumentParser();p.add_argument('--xml',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();d=parse_article(a.xml.read_bytes(),URL);a.out.mkdir(parents=True,exist_ok=True)
    objects={'fulltext_audit.json':anuradhapura_audit(d),
             'method_excerpts_and_tables.json':compact_dossier(d),
             'benchmark_cases.json':benchmark_cases(d,anuradhapura_audit(d))}
    for name,data in objects.items():
        (a.out/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
        print('WROTE',name)
if __name__=='__main__':main()
