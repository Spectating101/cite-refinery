"""Frozen primary article evidence, provenance, independent benchmark gates."""
from __future__ import annotations
import copy,csv,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from cite_refinery.investigation_controller import InvestigationController
from test_investigation_controller_v1 import StubReasoner,MODULES,SOURCES
from cite_refinery.fulltext_audit import parse_article,anuradhapura_audit,fulltext_source
from cite_refinery.research_data_audit import audit_published_dog_repo
from cite_refinery.adjudication_benchmark import make_judge_prompt,score_benchmark

F=Path(__file__).resolve().parents[1]/'research_materials/runtime_trials/fulltext_dog_20261020'

def load(name):return json.loads((F/name).read_text())

class SourceAndBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier=load('method_excerpts_and_tables.json')
        cls.audit=load('fulltext_audit.json')
        cls.test_cases=load('benchmark_cases.json')['cases']

    def test_fulltext_access_is_a_bounded_pmc_endpoint(self):
        with self.assertRaises(ValueError):fulltext_source('https://localhost/metadata')
        url,data=fulltext_source('PMC13500148',fetch=lambda u:b'<article><body><sec/></body></article>')
        self.assertTrue(url.startswith('https://www.ebi.ac.uk/europepmc/webservices/rest/'))
        self.assertLess(len(data),100)

    def test_tables_and_methods_from_actual_deposited_article(self):
        tables={t['id']:t for t in self.dossier['selected_tables']}
        self.assertEqual(set(tables),{'T3','T6B','T6C'})
        self.assertEqual(len(tables['T6C']['rows'])-1,6)
        rows=lambda t,*terms:next(row for row in tables[t]['rows'][1:] if row[:len(terms)]==list(terms))
        self.assertEqual(rows('T3','Total')[1],'1.03')
        self.assertEqual(rows('T3','Total')[3],'0.55488235')
        self.assertEqual(rows('T6B','1','Male')[6],'0.835')
        self.assertEqual(rows('T6C','Male','1')[4],'0.038*')
        self.assertEqual(rows('T6C','Female','3')[4],'0.0003***')
        self.assertFalse(self.audit['checks']['multiplicity_sensitivity']['zone_1_male_below_threshold'])
        self.assertTrue(self.audit['checks']['multiplicity_sensitivity']['zone_3_female_below_threshold'])
        self.assertEqual(self.audit['source_status'],'full_text_examined_not_independently_replicated')

    def test_reconstructed_jats_parser_supports_local_offline_replication(self):
        root=ET.Element('article');front=ET.SubElement(root,'front')
        meta=ET.SubElement(front,'article-meta');ident=ET.SubElement(meta,'article-id',{'pub-id-type':'doi'})
        ident.text=self.dossier['doi'];title=ET.SubElement(meta,'article-title');title.text=self.dossier['title']
        abstract=ET.SubElement(meta,'abstract');p=ET.SubElement(abstract,'p')
        p.text='The number of free-roaming dogs requiring sterilization declined from 1,368 in 2021 to 484 in 2025.'
        body=ET.SubElement(root,'body')
        for sec in self.dossier['methods_sections']:
            section=ET.SubElement(body,'sec');heading=ET.SubElement(section,'title');heading.text=sec['heading']
            para=ET.SubElement(section,'p');para.text=sec['excerpt']
        for t in self.dossier['selected_tables']:
            wrapper=ET.SubElement(body,'table-wrap',{'id':t['id']});cap=ET.SubElement(wrapper,'caption')
            cap.text=t['caption'];table=ET.SubElement(wrapper,'table')
            for i,row in enumerate(t['rows']):
                tr=ET.SubElement(table,'tr')
                for x in row:ET.SubElement(tr,'th' if i==0 else 'td').text=x
        raw=ET.tostring(root,encoding='utf-8')
        doc=parse_article(raw,'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13500148/fullTextXML')
        checked=anuradhapura_audit(doc)
        self.assertEqual(checked['checks']['total_count_trend']['p_value'],'0.55488235')
        self.assertEqual(checked['checks']['zone_1_male_simple_prepost']['p_value'],'0.835')
        self.assertEqual(checked['checks']['zone_1_male_buffer_interaction']['p_value'],'0.038')
        self.assertEqual(checked['dataset_manifest'][0]['availability'],'Corresponding author on request')

    def test_investigator_optional_fulltext_enrichment_retains_parent_provenance(self):
        scholar=dict(SOURCES['EPMC-123456789012'],pmcid='PMC13500148')
        official=dict(SOURCES['OFFICIAL-987654321012'])
        enriched={'id':'JATS-verified','url':'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13500148/fullTextXML',
                  'text':'Detailed published statistical methods using explicit repeated effort offsets in negative binomial sampling models.',
                  'parent_source_url':scholar['url'],'same_study_as_parent':True,
                  'source_scope':'Same publication, not independent replication',
                  'origin_type':'scholarly_fulltext_excerpt_unverified'}
        with TemporaryDirectory() as folder:
            controller=InvestigationController(folder,reasoner=StubReasoner(),
              academic_search=lambda query,*,limit:[scholar],
              official_search=lambda query,*,limit:[official])
            start=controller.start('Why do dog population estimates fail to measure intervention impacts?',MODULES,
                                   fulltext_enrichment=True)
            controller.step(start['id'])
            with patch('cite_refinery.fulltext_audit.enrich_academic_abstract_with_fulltext',return_value=enriched) as lookup:
                state=controller.step(start['id'])
            self.assertEqual(state['stage'],'reason')
            self.assertTrue(lookup.called)
            self.assertEqual(len(state['rounds'][0]['sources']),3)
            e=next(x for x in state['rounds'][0]['sources'] if x['id']=='JATS-verified')
            self.assertEqual(e['parent_source_url'],scholar['url'])
            self.assertTrue(e['same_study_as_parent'])

    def test_gold_cases_are_source_grounded_and_hidden_from_model(self):
        self.assertEqual(len(self.test_cases),21)
        self.assertEqual(len(set(c['id'] for c in self.test_cases)),len(self.test_cases))
        self.assertTrue(all(len(c['evidence'])>15 and len(c['gold_reason'])>15 for c in self.test_cases))
        prompt=make_judge_prompt(self.test_cases)
        self.assertNotIn('gold_reason',prompt)
        self.assertNotIn('"expected"',prompt)
        self.assertIn('B16',prompt)

    def test_benchmark_exact_output_and_false_positive_penalties(self):
        perfect={'predictions':[{'id':c['id'],'label':c['expected'],
             'rationale':'This answer follows the explicit source, estimation scope, and reported table result.'}
             for c in self.test_cases]}
        score=score_benchmark(self.test_cases,perfect)
        self.assertEqual(score['accuracy'],1)
        self.assertEqual(score['false_positive_entailment_count'],0)
        distorted=copy.deepcopy(perfect)
        item=next(p for p in distorted['predictions'] if p['id']=='B02')
        item['label']='entailed'
        score2=score_benchmark(self.test_cases,distorted)
        self.assertEqual(score2['false_positive_entailment_count'],1)
        self.assertLess(score2['accuracy'],1)
        with self.assertRaises(ValueError):score_benchmark(self.test_cases,{'predictions':perfect['predictions'][:-1]})

    def test_comparator_public_data_provenance_is_not_original_data(self):
        manifest=load('reproducibility_manifest.json')
        self.assertEqual(manifest['raw_identified_dogs'],235)
        self.assertEqual(manifest['raw_sighting_events'],567)
        self.assertEqual(manifest['population_estimate_rows'],40)
        self.assertEqual(manifest['invalid_estimate_intervals'],0)
        self.assertFalse(manifest['posterior_refitted'])
        self.assertIn('Italy',manifest['location_and_period'])
        self.assertIn('not Anuradhapura Sri Lanka',manifest['location_and_period'])
        self.assertIn('R/01_Bayesian_PCRD_model.R',manifest['files_sha256'])

if __name__=='__main__':unittest.main()
