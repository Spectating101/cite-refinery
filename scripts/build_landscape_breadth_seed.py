"""Generate a deliberately broad, provisional semantic problem landscape.

Source excerpts/abstracts and primary published pages were reviewed at seed
time. This is *not* a systematic census of sectors or a source truth engine.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="cite_refinery.semantic_graph.v1"

# Fields deliberately span very different domains; missing layers remain empty.
FIELDS=[
    ("animal","Animal welfare and roaming-dog management",
      ("observation","Population observability"),("effects","Management feedback")),
    ("privacy","Digital privacy and LLM prompts",
      ("exposure","Sensitive information exposure"),("mitigation","Sanitization limitations")),
    ("energy","Renewable electricity systems",
      ("curtailment","Curtailment and grid constraints"),("flexibility","Power-system flexibility")),
    ("food","Food systems and waste",
      ("households","Household food waste"),("measurement","Waste measurement coverage")),
    ("amr","Antimicrobial resistance",
      ("surveillance","Resistance surveillance completeness"),("action","Health response capacity")),
    ("education","Education access",
      ("exclusion","Children outside schooling"),("learning","Learning access and digital barriers")),
    ("connectivity","Digital connectivity and inclusion",
      ("access","Broadband availability and affordability"),("skills","Digital skills and use")),
    ("water","Water resources and hydrological hazards",
      ("observation","Hydrological monitoring gaps"),("risk","Drought and flood preparedness")),
    ("housing","Housing adequacy and affordability",
      ("adequacy","Adequate housing access"),("measurement","Housing monitoring comparability")),
]
# Key, field, module, layer, type, assertion, source, anchor, relation and bounds.
MATERIALS=[
 ("dog_survey","animal","observation","practical","observation",
  "Taiwan's 2024 official free-roaming-dog population estimate was 141,584; the change from 2022 was described as not statistically significant.",
  "https://animal.moa.gov.tw/Frontend/News/Detail/N0000000001599","animal_observation","CONTEXT_FOR",
  "National periodic sampling, not live local population enumeration or causal intervention evidence."),
 ("dog_method","animal","observation","academic","method",
  "A systematic review documents several methods and assumptions relevant to estimating free-ranging dog populations.",
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC4684217/","animal_observation","RELATED_TO",
  "Methodological relevance only; no estimator executed or tested in this broad seed."),
 ("dog_talea","animal","observation","program","program",
  "Talea provides a documented street-survey recording system; its manual says a sighting record cannot include an individual animal photo.",
  "https://www.icam-coalition.org/talea-user-guide/","animal_observation","RELATED_TO",
  "Provider documentation, not proof of local population estimation or field effectiveness."),
 ("privacy_risk","privacy","exposure","practical","observation",
  "A source-reported concern about sharing sensitive text with cloud language-model services exists in a pinned Refinery evidence package.",
  "https://github.com/Spectating101/refinery/tree/2b03ad20f8ab3d55462adb38852855b940194c94/evidence/cloakpipe-core-20261016","privacy_exposure","CONTEXT_FOR",
  "Reporter concern in documented engineering case, NOT an independently confirmed user data leak."),
 ("privacy_alsa","privacy","mitigation","academic","method",
  "The ALSA paper studies privacy-preserving prompt anonymization with context-sensitive substitution.",
  "https://doi.org/10.1145/3711896.3736840","privacy_mitigation","RELATED_TO",
  "Paper's method not independently replicated or compared against CloakPipe here."),
 ("privacy_cloakpipe","privacy","mitigation","program","implementation",
  "A bounded CloakPipe implementation package reports 27 required passing tests and four broader leakage probes.",
  "https://github.com/Spectating101/refinery/tree/2b03ad20f8ab3d55462adb38852855b940194c94/evidence/cloakpipe-core-20261016","privacy_mitigation","RELATED_TO",
  "Pinned reports only; broader leakage failures preclude general privacy protection claims."),
 ("energy_iea","energy","curtailment","practical","observation",
  "IEA reports growing curtailment in multiple electricity markets as variable renewable generation expands.",
  "https://www.iea.org/reports/renewables-2025/renewable-electricity","energy_curtailment","CONTEXT_FOR",
  "Cross-market synthesis; technical curtailment definitions and periods vary by market."),
 ("energy_flex","energy","flexibility","practical","observation",
  "IEA describes transmission, flexibility and coordinated planning as challenges in integrating growing wind and solar shares.",
  "https://www.iea.org/reports/renewables-2025/executive-summary","energy_flexibility","CONTEXT_FOR",
  "Describes a system issue; no independently tested local remedy linked in this map."),
 ("food_unep","food","households","practical","observation",
  "UNEP estimates 1.05 billion tonnes of household, food-service and retail food waste in 2022.",
  "https://www.unep.org/en/news-and-stories/press-release/world-squanders-over-1-billion-meals-day-un-report","food_households","CONTEXT_FOR",
  "Modelled 2022 global estimate combining sectors; not a 2026 measured time series."),
 ("food_academic","food","households","academic","academic_claim",
  "A systematic review links household food-waste behaviour to multiple contextual and behavioural drivers.",
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC12106936/","food_households","RELATED_TO",
  "Review evidence spans diverse contexts and does not identify a single universally effective intervention."),
 ("food_index","food","measurement","program","program",
  "UNEP's Food Waste Index specifies levels of country-level measurement, distinguishing estimates from direct observations suited to trend tracking.",
  "https://sdgs.unep.org/article/2a5-food-waste-index","food_measurement","RELATED_TO",
  "Index measurement framework, not evidence of reduced food waste."),
 ("amr_who","amr","surveillance","practical","observation",
  "WHO's 2025 surveillance report summarizes bacterial resistance trends from millions of confirmed infections and acknowledges country data-quality variation.",
  "https://www.who.int/publications/i/item/9789240116337/","amr_surveillance","CONTEXT_FOR",
  "Reported surveillance populations and adjusted estimates are not a census of every infection."),
 ("amr_review","amr","surveillance","academic","academic_claim",
  "A scoping review identifies representativeness, incomplete data and reporting bias among antimicrobial-resistance surveillance challenges.",
  "https://link.springer.com/article/10.1186/s12879-023-08585-2","amr_surveillance","RELATED_TO",
  "General surveillance literature, not a validation of every WHO-country data stream."),
 ("amr_glass","amr","surveillance","program","program",
  "WHO GLASS supports standardized country antimicrobial-resistance surveillance and analysis.",
  "https://www.who.int/publications/i/item/9789240116337/","amr_surveillance","RELATED_TO",
  "Operating surveillance program is not evidence of resistance mitigation."),
 ("edu_unesco","education","exclusion","practical","observation",
  "UNESCO's 2026 SDG 4 monitoring reports 273 million children and youth out of school in 2024.",
  "https://www.unesco.org/reports/gem-report/en/2026-monitoring-sdg4","education_exclusion","CONTEXT_FOR",
  "Global estimates revised over time, with coverage limits in crisis settings."),
 ("edu_uis","education","exclusion","program","dataset",
  "UNESCO UIS Data Browser publishes downloadable education participation and out-of-school indicators with metadata.",
  "https://databrowser.uis.unesco.org/browser/EDUCATION/UIS-EducationOPRI/out-of-school","education_exclusion","RELATED_TO",
  "Monitoring data platform; cannot by itself resolve exclusion."),
 ("edu_digital","education","learning","academic","academic_claim",
  "A systematic review of educational digital divide studies describes access, hardware, use and other disparities in learning technology.",
  "https://doi.org/10.1080/15391523.2024.2425442","education_learning","RELATED_TO",
  "Educational digital inequity should not be conflated with all causes of out-of-school status."),
 ("digital_itu","connectivity","access","practical","observation",
  "ITU's 2025 digital-development report estimates 2.2 billion people remain offline, with affordability and quality gaps.",
  "https://www.itu.int/en/ITU-D/Statistics/Pages/facts/default.aspx","connectivity_access","CONTEXT_FOR",
  "Global modeled aggregates, not direct diagnoses of an individual locality."),
 ("digital_review","connectivity","skills","academic","academic_claim",
  "A 2024 systematic integrative review of digital inequity highlights literacy, affordability and access barriers.",
  "https://doi.org/10.1108/DTS-04-2024-0054","connectivity_skills","RELATED_TO",
  "Review emphasizes developed countries; does not transfer automatically worldwide."),
 ("digital_datahub","connectivity","access","program","dataset",
  "ITU DataHub offers country and regional connectivity statistics, including access and affordability indicators.",
  "https://www.itu.int/itu-d/reports/statistics/global-connectivity-report-2025/","connectivity_access","RELATED_TO",
  "Measurement and reporting capability, not proof of universal access."),
 ("water_wmo","water","observation","practical","observation",
  "WMO's 2024 global water report states only about one third of river basins had normal conditions in that year.",
  "https://wmo.int/resources/publication-series/state-of-global-water-resources/state-of-global-water-resources-2024","water_observation","CONTEXT_FOR",
  "One-year status, not continuous local risk prediction or universal station coverage."),
 ("water_hydrosos","water","observation","program","program",
  "WMO HydroSOS supports standardized hydrological status and outlook information and country capacity building.",
  "https://wmo.int/activities/hydrosos","water_observation","RELATED_TO",
  "Described global initiative; deployment coverage and local forecast skill not checked."),
 ("housing_unhabitat","housing","adequacy","practical","observation",
  "UN-Habitat documents inadequate and unaffordable urban housing as a significant global challenge.",
  "https://unhabitat.org/11-1-adequate-housing","housing_adequacy","CONTEXT_FOR",
  "General global indicator framing; no local comparable housing dataset collected yet."),
]
def build():
    clusters=[{"key":"landscape_root","title":"Exploratory cross-field problem landscape","tags":["breadth_first","non_exhaustive"]}]
    nodes=[];edges=[]
    for code,title,*modules in FIELDS:
        clusters.append({"key":code,"title":title,"parent":"landscape_root","tags":["field_seed","unranked"]})
        for subkey,name in modules:
            clusters.append({"key":code+"_"+subkey,"title":name,"parent":code,"tags":["problem_module","discovery_only"]})
            anchor=code+"_"+subkey
            nodes.append({"key":anchor,"statement":"Investigate "+name.lower()+" within "+title.lower()+".","kind":"research_question","layer":"neutral","clusters":[anchor],"tags":["landscape_anchor","not_a_verified_problem_claim"]})
    for key,field,module,layer,kind,statement,url,anchor,relation,boundary in MATERIALS:
        clusters_used=[field,field+"_"+module]
        nodes.append({"key":key,"statement":statement,"kind":kind,"layer":layer,"clusters":clusters_used,
                      "source_refs":[url],"tags":["landscape_seed","source_summary_not_replication"],
                      "provenance":{"review_scope":"published_page_or_abstract","boundary":boundary,"source_reviewed_on":"2026-10-20"}})
        edges.append({"source":key,"relation":relation,"target":anchor,
                      "status":"candidate","evidence_refs":[url],
                      "provenance":{"boundary":"Exploratory topical association; do not infer causal applicability, solution efficacy or completeness. "+boundary}})
    edges.append({"source":"edu_digital","relation":"RELATED_TO","target":"connectivity_skills",
                  "status":"candidate","evidence_refs":["https://doi.org/10.1080/15391523.2024.2425442"],
                  "provenance":{"boundary":"Educational digital access overlaps broader digital inequity; this is not a causal explanation of school nonattendance."}})
    return {"schema":SCHEMA,"source_system":"landscape_discovery_seed_20261020",
            "clusters":clusters,"nodes":nodes,"edges":edges,
            "conversion_metadata":{"status":"EXPLORATORY_UNRANKED","domain_count":len(FIELDS),
              "source_evidence_records":len(MATERIALS),
              "sampling":"Purposive diversity seed, not systematic universe or prevalence estimate",
              "blocked_inference":"No missing category or absent edge implies absence in the world; no program efficacy verified."}}
if __name__=="__main__":
    output=ROOT/"examples/landscape_breadth_seed_v1.json"
    output.write_text(json.dumps(build(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("written",output,len(build()["clusters"]),len(build()["nodes"]),len(build()["edges"]))
