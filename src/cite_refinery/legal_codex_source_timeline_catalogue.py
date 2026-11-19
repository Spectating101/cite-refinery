"""017 analyst-authored labels and paragraph selection, not automatic legal inference."""
from .legal_codex_source_timeline import digest

# id, source, paragraph, event day, literal date token, attributed role, monetary effect, English label.
SPECS = (
('assisted_application','district_2025','p0030','2023-04-12','12 april 2023','reported_procedural_event',None,'The court recounts an in-person, staff-assisted application for rent and health benefits.'),
('advance_decision','district_2025','p0030','2023-05-24','24 mei 2023','reported_procedural_event',None,'The court recounts benefit advances calculated using estimated annual income.'),
('rent_advance_revision','district_2025','p0030','2023-06-23','23 juni 2023','reported_procedural_event',None,'The court recounts a revision to the rent advance; other advances stayed unchanged.'),
('advance_unchanged','district_2025','p0030','2023-10-25','25 oktober 2023','reported_procedural_event',None,'The court recounts a further decision leaving the advances unchanged.'),
('original_recovery','appeal_2026','p0013','2024-01-05','5 januari 2024','reported_procedural_event','recovery_order','The court recounts revised advances and recovery demands of EUR 1,301, 818 and 371 (EUR 2,490 combined), not proof of collection.'),
('phone_contact_claim','district_2025','p0035','2024-02-28','28 februari 2024','party_submission',None,'The claimant argued that she had not waived a hearing during the telephone contact; this entry preserves a party submission, not an authenticated call log.'),
('objection_rejected','appeal_2026','p0014','2024-03-18','18 maart 2024','reported_procedural_event',None,'The court recounts rejection of the administrative objection.'),
('district_hearing','district_2025','p0021','2025-01-10','10 januari 2025','reported_procedural_event',None,'The district court records its hearing with the claimant and agency representatives.'),
('district_hearing_breach','district_2025','p0037','2025-02-24',None,'court_finding',None,'The district court found a hearing-duty breach but passed it under Article 6:22; it did not grant recovery relief on that ground.'),
('agency_argument_recorded','district_2025','p0047','2025-02-24',None,'party_submission',None,'The judgment records the agency position that the staff role had been considered, with limited reasoning; this is an attributed position.'),
('district_input_uncertainty','district_2025','p0049','2025-02-24',None,'court_finding',None,'The district court recorded uncertainty about the precise application inputs and responsibility, but did not find exceptional circumstances requiring mitigation.'),
('district_recovery_upheld','district_2025','p0060','2025-02-24',None,'court_order',None,'The district court dismissed the appeal. This is an actual first-instance outcome, later partly reversed.'),
('appeal_hearing','appeal_2026','p0019','2026-02-13','13 februari 2026','reported_procedural_event',None,'The appellate judgment records its hearing date; this is not a complete evidentiary receipt log.'),
('appeal_hearing_ground_rejected','appeal_2026','p0035','2026-03-25',None,'court_finding',None,'The appellate court agreed that the hearing-duty defect could be passed; this defect was not a separate basis for the recovery waiver.'),
('appeal_missing_agency_form','appeal_2026','p0046','2026-03-25',None,'court_finding',None,'The court found the agency could not produce the application form and had no substantive visit note; responsibility for the input could not be established. The records do not establish when agency staff first knew the form was unavailable.'),
('appeal_zero_recovery','appeal_2026','p0057','2026-03-25',None,'court_order','court_ordered_zero_recovery','The operative order reduced the recovery amount by 100 percent to zero; it does not prove any refund was paid.'),
('appeal_other_parts_upheld','appeal_2026','p0059','2026-03-25',None,'court_order',None,'The appellate court upheld the district judgment for the remainder: no wholesale reversal of the benefit reassessment.'),
('comparator_recovery_decision','comparator_2021','p0021','2018-07-17','17 juli 2018','reported_procedural_event','recovery_order','In the distinct child-budget case, the judgment recounts a recovery decision following revised asset information.'),
('comparator_entitlement_nil','comparator_2021','p0012','2018-07-21','21 juli 2018','reported_procedural_event',None,'The separate case included a decision setting child-budget entitlement to nil.'),
('comparator_objection','comparator_2021','p0013','2018-09-04','4 september 2018','reported_procedural_event',None,'The court recounts rejection of the administrative objection in the separate case.'),
('comparator_district','comparator_2021','p0014','2019-10-11','11 oktober 2019','reported_procedural_event',None,'The appellate court recounts dismissal in the separate Rotterdam district proceedings.'),
('comparator_hearing','comparator_2021','p0017','2021-06-18','18 juni 2021','reported_procedural_event',None,'The separate appellate court hearing occurred on this date.'),
('comparator_proportionality_reasoning','comparator_2021','p0039','2021-08-04',None,'court_finding',None,'The court found no demonstrated special circumstances justifying mitigation in the different asset-threshold case.'),
('comparator_recovery_upheld','comparator_2021','p0045','2021-08-04',None,'court_order',None,'The operative decision confirmed the lower judgment in the comparator case; it did not grant a waiver.'),
)

def make_fixture(sources):
    facts=[]
    for ident,sid,pid,day,token,role,effect,summary in SPECS:
        quote=sources[sid]['paragraphs'][pid]
        facts.append({'id':ident,'case_id':'child_budget_2014' if sid=='comparator_2021' else 'benefits_2023',
            'source_id':sid,'paragraph_id':pid,'paragraph_sha256':digest(quote.encode()),
            'day':day,'day_basis':'exact_date_in_text' if token else 'judgment_date',
            'date_token':token,'role':role,'summary':summary,'first_known_at':None,
            'first_known_actor':None,'money_effect':effect})
    return {'schema':'legal_codex.judicial_timeline.v1','mode':'judicial_reconstruction',
        'method':'judicial-reconstruction-017-v1','case_ids':['benefits_2023','child_budget_2014'],'facts':facts}
