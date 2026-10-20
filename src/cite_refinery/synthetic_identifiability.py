"""Deterministic synthetic counterexamples for counts-only identifiability.

These are NOT real dogs, not empirical study outcomes and not statistical
power/identification evidence for a named country.
"""
from __future__ import annotations

from fractions import Fraction


def demonstrations():
    # Expected observed sightings C_t = N_t * p_t. Actual headcounts can
    # include repeat sightings; this simple identity is only an abstract
    # first-order observation model, not a fitted capture-recapture process.
    situations=[
        {"scenario":"immigration_or_local_recruitment","n_before":100,"n_after":125,
         "p_before":Fraction(4,5),"p_after":Fraction(4,5),
         "explanation":"True local population rises, detection stays fixed; counts alone cannot tell immigration from local births."},
        {"scenario":"detectability_change_without_population_growth","n_before":100,"n_after":100,
         "p_before":Fraction(4,5),"p_after":Fraction(1,1),
         "explanation":"Population stays fixed, detection increases; the same observed change can arise without arrivals."},
        {"scenario":"higher_base_population_with_changed_detection","n_before":120,"n_after":120,
         "p_before":Fraction(2,3),"p_after":Fraction(5,6),
         "explanation":"A different, unobserved baseline abundance also yields the same count series."},
    ]
    for s in situations:
        s["expected_count_before"]=int(s["n_before"]*s["p_before"])
        s["expected_count_after"]=int(s["n_after"]*s["p_after"])
        s["p_before"]=str(s["p_before"])
        s["p_after"]=str(s["p_after"])
    assert all((s["expected_count_before"],s["expected_count_after"])==(80,100) for s in situations)
    return {"schema":"cite_refinery.synthetic_identifiability_counterexample.v1",
            "observation_model":"expected_unique_sightings = true_abundance * detection_probability",
            "observations":[80,100],"scenarios":situations,
            "implication":"Identical aggregate expected sighting counts do not identify abundance growth or mechanism.",
            "empirical_data_used":False,"causal_effect_estimated":False,
            "boundary":"Arithmetic thought experiment. No field data or actual clinical/rabies measurements."}
