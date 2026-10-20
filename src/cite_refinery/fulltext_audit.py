"""JATS full-text methods/table audit for openly accessible scholarly articles.

Source-level verification, not independent study replication. Remote retrieval
is bound to Europe PMC, with a bounded XML response. Original article content
stays in a local temporary cache, not a committed publication substitute.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation


def _text(node):
    return " ".join(" ".join(node.itertext()).split()) if node is not None else ""


def _cell(row):
    return [_text(c) for c in row if c.tag.rsplit("}",1)[-1] in {"th","td"}]


def fulltext_source(pmcid, fetch=None):
    if not re.fullmatch(r"PMC[0-9]{4,12}",str(pmcid)):
        raise ValueError("Expected a valid PMC accession")
    url=f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    if fetch is None:
        def fetch(u):
            with urllib.request.urlopen(urllib.request.Request(
                    u,headers={"User-Agent":"Cite-Refinery-Research-Audit/1.0"}),timeout=25) as res:
                content=res.read(2_500_001)
                if len(content)>2_500_000:raise ValueError("Full text exceeds source size limit")
                return content
    raw=fetch(url)
    if not isinstance(raw,bytes) or len(raw)>2_500_000:
        raise ValueError("Full text must be bounded XML bytes")
    return url,raw


def parse_article(xml_bytes,source_url):
    """Preserve table and section IDs; do not flatten the whole paper to one blob."""
    root=ET.fromstring(xml_bytes)
    body=root.find(".//body")
    if body is None:raise ValueError("Missing JATS article body")
    doi=""
    for el in root.findall(".//article-id"):
        if el.get("pub-id-type")=="doi":doi=_text(el);break
    title=_text(root.find(".//article-title"))
    if not doi or not title:raise ValueError("Cannot verify JATS metadata")
    sections=[]
    for sec in body.iter("sec"):
        heading=_text(sec.find("title"))
        if not heading:continue
        paragraphs=[]
        for child in sec:
            if child.tag.rsplit("}",1)[-1]=="p" and _text(child):paragraphs.append(_text(child))
        sections.append({"title":heading,"text":"\n\n".join(paragraphs),
                         "paragraphs":paragraphs})
    tables=[]
    for element in root.findall(".//table-wrap"):
        cap=_text(element.find("caption"))
        matrix=[_cell(tr) for tr in element.findall(".//tr")]
        matrix=[row for row in matrix if row]
        tables.append({"id":element.get("id"),"caption":cap,"rows":matrix,
                       "footnotes":[_text(x) for x in element.findall(".//table-wrap-foot//p")]})
    supplement=[]
    for item in root.findall(".//supplementary-material"):
        supplement.append({"id":item.get("id"),"caption":_text(item.find("caption")),
                           "href":item.attrib.get("{http://www.w3.org/1999/xlink}href")})
    abstract=" ".join(_text(a) for a in root.findall(".//front//abstract"))
    return {
        "schema":"cite_refinery.jats_method_dossier.v1",
        "doi":doi,"title":title,"abstract":abstract,
        "source_url":source_url,
        "source_sha256":hashlib.sha256(xml_bytes).hexdigest(),
        "sections":sections,"tables":tables,"supplementary_entries":supplement,
        "source_kind":"peer_reviewed_article_fulltext_publisher_deposited",
        "boundary":"Published author report and tables, not independently collected dog-level raw data.",
    }


def _section(dossier,name):
    matches=[x for x in dossier["sections"] if x["title"].strip().lower()==name.lower()]
    if len(matches)!=1:raise ValueError("Missing or duplicated required section: "+name)
    return matches[0]


def _table(dossier,name):
    matches=[x for x in dossier["tables"] if x["id"]==name]
    if len(matches)!=1:raise ValueError("Missing or duplicated table: "+name)
    return matches[0]


def _row(table,*terms):
    matches=[r for r in table["rows"][1:] if tuple(x.casefold() for x in r[:len(terms)])==
             tuple(x.casefold() for x in terms)]
    if len(matches)!=1:
        raise ValueError(f"Expected a unique row in {table['id']} with prefix {terms}, got {len(matches)}")
    return matches[0]


def _dec(text):
    cleaned=re.sub(r"[^0-9.\-]","",str(text).replace("–","-").replace("−","-").replace("—","-"))
    try:return Decimal(cleaned)
    except InvalidOperation as exc:raise ValueError("Invalid numeric table cell "+str(text)) from exc


def anuradhapura_audit(dossier):
    """Verify reported statements against actual full-text tables.

    Evidence is from the SAME study; this is an internal consistency check,
    NOT a separate experiment, a causal effect or full statistical replication.
    """
    if dossier["doi"]!="10.14202/vetworld.2026.2816-2849":
        raise ValueError("Cannot apply Anuradhapura checks to another paper")
    data_sec=_section(dossier,"DATA AVAILABILITY")
    limits=_section(dossier,"STUDY LIMITATIONS")
    methods=_section(dossier,"Statistical analysis")
    t3=_table(dossier,"T3")
    t6b=_table(dossier,"T6B")
    t6c=_table(dossier,"T6C")
    total=_row(t3,"Total")
    male_prepost=_row(t6b,"1","Male")
    male_buffer=_row(t6c,"Male","1")
    female_buffer=_row(t6c,"Female","3")
    ntests=len(t6c["rows"])-1
    if ntests!=6:raise ValueError("Unexpected buffer subgroup count; verify model specification")
    p_male=_dec(male_buffer[4].rstrip("*"))
    p_female=_dec(female_buffer[4].rstrip("*"))
    p_total=_dec(total[3].rstrip("*"))
    p_prepost=_dec(male_prepost[6].rstrip("*"))
    availability=data_sec["text"]
    matched=re.search(r"free-roaming dogs requiring sterilization declined from\s+1,368\s+in 2021 to\s+484\s+in 2025",dossier["abstract"],re.I)
    if not matched:
        raise ValueError("Published abstract does not substantiate the asserted 2021/2025 counts")
    if "upon request" not in availability.lower():
        raise ValueError("Data availability statement changed; manual reassessment needed")
    method_text=methods["text"]
    notes={
        "published_2021_to_2025_sterilization_need_claim":{
            "reported_values":[1368,484],
            "exact_abstract_quote":matched.group(0),
            "evidence_type":"author_reported_abstract_and_results",
            "internal_check":"Full text and abstract may be compared; original dog-level intake file unavailable in article.",
            "not_supported":"Not a total dog abundance time series or measured human-rabies reduction",
        },
        "total_count_trend":{
            "table":"T3","response":"Total",
            "irr_per_year":str(_dec(total[1])),
            "p_value":str(p_total),
            "confidence_interval":total[2],
            "interpretation":"Effort-adjusted total dog-count trend not conventionally significant in this table.",
        },
        "zone_1_male_simple_prepost":{
            "table":"T6B","pre_rate":male_prepost[2],"post_rate":male_prepost[3],
            "p_value":str(p_prepost),
            "interpretation":"A separate pre/post catch-rate comparison; not the buffer-interaction estimand.",
        },
        "zone_1_male_buffer_interaction":{
            "table":"T6C","irr_per_buffer_dog":male_buffer[3],
            "p_value":str(p_male),"confidence_interval":male_buffer[5],
            "interpretation":"An interaction/association within the reported model, not independent causal verification.",
        },
        "zone_3_female_buffer_interaction":{
            "table":"T6C","irr_per_buffer_dog":female_buffer[3],
            "p_value":str(p_female),"confidence_interval":female_buffer[5],
        },
        "multiplicity_sensitivity":{
            "six_rows_in_table":ntests,
            "illustrative_bonferroni_threshold":"0.05/6",
            "threshold":str(Decimal("0.05")/Decimal(ntests)),
            "zone_1_male_below_threshold":p_male<Decimal("0.05")/Decimal(ntests),
            "zone_3_female_below_threshold":p_female<Decimal("0.05")/Decimal(ntests),
            "boundary":"Illustrative six-comparison sensitivity only; not proof this is the appropriate prespecified inferential family.",
        },
    }
    missing=[
        {"item":"dog-level original survey/capture records",
         "availability":"Corresponding author on request",
         "quote":availability[:350]},
        {"item":"systematic community-wide abundance sample",
         "availability":"Authors acknowledge not collected due to resources",
         "quote":next((p[:450] for p in limits["paragraphs"] if "systematic community dog surveys" in p.lower()),limits["text"][:450])},
        {"item":"geographically matched human bite/PEP/rabies outcome series",
         "availability":"Authors acknowledge insufficient local data",
         "quote":next((p[:600] for p in limits["paragraphs"] if "dog bites" in p.lower()),limits["text"][:600])},
    ]
    # A meaningful methodological issue: effort was adjusted as an offset
    # even though the authors acknowledge effort responded to observed counts.
    acknowledged=[
        {"point":"survey_effort_endogenous_to_perceived_population",
         "method_mentioned":("offset" in method_text and "negative binomial" in method_text.lower()),
         "source_scope":"Methodology describes offset; discussion acknowledges reduction in catching days responded to falling apparent numbers.",
         "not_a_replication":"Cannot re-estimate GLM without raw time/zone/dog records"},
        {"point":"no_direct_impact_on_dog_bite_human_rabies",
         "source_scope":"The study limitation explicitly says effect on bites, PEP and rabies incidence could not be quantified accurately."},
    ]
    return {
        "schema":"cite_refinery.fulltext_claim_audit.v1",
        "doi":dossier["doi"],"source_sha256":dossier["source_sha256"],
        "source_url":dossier["source_url"],"checks":notes,
        "dataset_manifest":missing,"methodological_flags":acknowledged,
        "tables_inspected":["T3","T6B","T6C"],
        "conclusion":"Within-paper source verification achieved; direct raw-data or causal replication unavailable.",
        "source_status":"full_text_examined_not_independently_replicated",
    }


def compact_dossier(dossier,*,headings=("Statistical analysis","STUDY LIMITATIONS","DATA AVAILABILITY"),tables=("T3","T6B","T6C")):
    """Publish just necessary methods excerpts and tables, not the full article."""
    sections=[]
    for name in headings:
        sec=_section(dossier,name)
        source=sec["text"]
        sections.append({"heading":name,"section_digest":hashlib.sha256(source.encode()).hexdigest(),
                         "excerpt":source[:1700]})
    return {
        "doi":dossier["doi"],"title":dossier["title"],"source_url":dossier["source_url"],
        "source_sha256":dossier["source_sha256"],
        "methods_sections":sections,
        "selected_tables":[_table(dossier,key) for key in tables],
        "rights":"Excerpt and data table evidence for review; cite journal and authors",
        "boundary":dossier["boundary"],
    }



def enrich_academic_abstract_with_fulltext(source,*,fetch=None):
    """Extract bounded relevant methods, limitations and JATS table cells.

    This is the SAME DOI as the abstract, not another independent study.
    Original verbatim source paragraphs are kept separate from JATS table-cell
    transcriptions, whose exact cell values are retained with source table IDs.
    """
    if source.get('origin_type')!='scholarly_abstract_lead':return None
    pmcid=source.get('pmcid')
    if not isinstance(pmcid,str) or not re.fullmatch(r'PMC[0-9]{4,12}',pmcid):return None
    url,raw=fulltext_source(pmcid,fetch=fetch)
    doc=parse_article(raw,url)
    concepts={t for t in re.findall(r'[a-z]{4,}',source.get('text','').lower())
              if t not in {'there','their','study','with','from','were','when','this','which',
                           'using','based','years','zone','project','result'}}
    concepts|={'sterilization','rabies','buffer','population','vaccination','catching'}
    mandatory=[]
    for exact in ['Statistical analysis','STUDY LIMITATIONS','DATA AVAILABILITY']:
        sec=next((s for s in doc['sections'] if s['title'].lower()==exact.lower()),None)
        if sec and sec['paragraphs']:
            paras=sec['paragraphs']
            if exact=='STUDY LIMITATIONS':
                survey=next((p for p in paras if 'systematic community dog surveys' in p.lower()),paras[0])
                mandatory.append((exact,survey[:800]))
                bites=next((p for p in paras if 'dog bites' in p.lower()),None)
                if bites and bites!=survey:mandatory.append((exact+' — rabies outcome data',bites[:850]))
            else:
                best=max(paras,key=lambda p:sum(w in p.lower() for w in concepts))
                mandatory.append((exact,best[:1050]))
    paragraphs=[]
    for sec in doc['sections']:
        if sec['title'].lower() not in {'results','discussion','contribution of the buffer zone to controlling the free-roaming dog population within the city',
                                        'influence of the buffer zone on reducing the population within the municipality',
                                        'novel aspects of the study'}:
            continue
        for paragraph in sec['paragraphs']:
            score=sum(w in paragraph.lower() for w in concepts)
            if len(paragraph)>100 and score>=3:
                paragraphs.append((score,sec['title'],paragraph))
    paragraphs.sort(key=lambda item:(-item[0],item[1]))
    output=[];headers=[]
    def append_section(head,text):
        piece=f'JATS section {head}: {text}'
        if piece not in output:
            output.append(piece);headers.append(head)
    for title,paragraph in mandatory:append_section(title,paragraph)
    for _,title,paragraph in paragraphs[:4]:append_section(title,paragraph[:900])
    tbl=[]
    if doc['doi']=='10.14202/vetworld.2026.2816-2849':
        wanted=['T3','T6B','T6C']
    else:
        ranked=sorted(doc['tables'],key=lambda t:-sum(w in t['caption'].lower() for w in concepts))
        wanted=[t['id'] for t in ranked[:2] if t.get('id')]
    for key in wanted:
        table=next((t for t in doc['tables'] if t['id']==key),None)
        if not table:continue
        rows=table['rows'][:12]
        tbl.append('JATS TABLE '+key+' '+table['caption']+':\n'+
                   '\n'.join(' | '.join(row) for row in rows))
    # Budget allocation: 5.5k original passages + 2k numeric table cells.
    body='\n\n'.join(output)[:5500]
    structured='\n\n'.join(tbl)[:1900]
    passage=(body+'\n\n'+structured).strip()
    if len(passage)<150:return None
    return {
        'id':'JATS-'+hashlib.sha256((url+doc['source_sha256']).encode()).hexdigest()[:12],
        'url':url,'text':passage,'title':doc['title'],
        'origin_type':'scholarly_fulltext_excerpt_unverified',
        'source_scope':'Same DOI as original scholarly abstract; bounded JATS method/limitation excerpts and structured table cell transcriptions, NOT independent replication.',
        'parent_source_url':source['url'],'same_study_as_parent':True,
        'doi':doc['doi'],'pmcid':pmcid,
        'retrieval_url':url,'source_record':doc['doi'],
        'passage_sha256':hashlib.sha256(passage.encode()).hexdigest(),
        'full_article_sha256':doc['source_sha256'],
        'excerpt_section_types':headers,'jats_table_ids':wanted,
    }
