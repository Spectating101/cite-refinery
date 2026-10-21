"""Internal arbitrage reconnaissance from the existing three-layer atlas.

This is a read-only DERIVED VIEW, not a fourth conceptual graph layer.
Only exact, already recorded edges connect Practical/Academic/Implementation.
Source-scope executable defect leads are separate from atlas paths unless
the original problem identity was explicitly validated.

Optional financial scenarios are conditional buyer-supplied assumptions, NEVER
claimed sale prices, executable trading strategies or earned returns.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
import json

SCHEMA="cite_refinery.internal_arbitrage_map.v1"
ECON_SCHEMA="cite_refinery.internal_arbitrage_scenarios.v1"
ATLAS_SCHEMA="cite_refinery.three_layer_atlas_projection.v1"
ROUTES_SCHEMA="cite_refinery.operator_conversion_gate.v1"

def _canonical_hash(obj):
    return sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()

def _decimal(value,field):
    if isinstance(value,bool) or value is None or isinstance(value,(list,dict)):
        raise ValueError(f"{field}: explicit finite nonnegative number required")
    try: x=Decimal(str(value))
    except (ValueError,TypeError,InvalidOperation) as exc:
        raise ValueError(f"{field}: invalid numeric assumption") from exc
    if not x.is_finite() or x<0 or x>Decimal("100000000000"):
        raise ValueError(f"{field}: out of bounds")
    return x

def _money(value):
    return str(value.quantize(Decimal("0.01")))

_FIELDS={
    "purchase_price","success_sale_price","success_probability",
    "success_sale_fees","failure_recovery_value","failure_disposal_cost",
    "inbound_shipping","materials","labor_hours","labor_hourly_cost",
    "outbound_shipping","storage","tax_and_compliance","contingency",
}
def scenario_economics(scenario):
    """A bilateral resale/repair trade model with explicit failure-path costs."""
    if not isinstance(scenario,dict) or set(scenario)!={"id","type","currency","basis",
            "upstream_reference","downstream_reference","assumptions"}:
        raise ValueError("Scenario must disclose complete sources and assumptions")
    if scenario["type"] not in {"used_electronics_repair_resale","part_out_salvage",
                               "general_acquire_rework_resell"}:
        raise ValueError("Unknown self-arbitrage trading strategy")
    if scenario["currency"] not in {"TWD","USD"} or scenario["basis"] not in {
        "hypothetical","observed_quotes_unverified"
    }:
        raise ValueError("Currency or price-evidence basis missing")
    if not isinstance(scenario["id"],str) or not (4<=len(scenario["id"])<=90):
        raise ValueError("Invalid scenario ID")
    for source in ("upstream_reference","downstream_reference"):
        val=scenario[source]
        if not isinstance(val,str) or len(val.strip())<12 or len(val)>500:
            raise ValueError(f"{source}: evidence locator or explicit unresolved note required")
    a=scenario["assumptions"]
    if not isinstance(a,dict) or set(a)!=_FIELDS:
        raise ValueError("Missing success/failure cost path or unexplained scenario field")
    v={k:_decimal(a[k],k) for k in _FIELDS}
    probability=v["success_probability"]
    if probability>1:raise ValueError("Success probability must be 0..1, not percentage points")
    # No probability-independent "sale price" optimism. The economic value of
    # the failed attempt must be priced as its own branch of the decision tree.
    success=v["success_sale_price"]-v["success_sale_fees"]-v["outbound_shipping"]
    failure=v["failure_recovery_value"]-v["failure_disposal_cost"]
    common=(v["inbound_shipping"]+v["materials"]+
            v["labor_hours"]*v["labor_hourly_cost"]+
            v["storage"]+v["tax_and_compliance"]+v["contingency"])
    expected_realization=probability*success+(1-probability)*failure
    max_bid=expected_realization-common
    net=max_bid-v["purchase_price"]
    return {
        "id":scenario["id"],"type":scenario["type"],"currency":scenario["currency"],
        "basis":scenario["basis"],"upstream_reference":scenario["upstream_reference"],
        "downstream_reference":scenario["downstream_reference"],
        "quoted_or_assumed_inputs_not_verified":True,
        "success_probability":str(probability),
        "success_branch_before_common_costs":_money(success),
        "failure_branch_before_common_costs":_money(failure),
        "shared_costs_including_labor_and_contingency":_money(common),
        "expected_realization_before_purchase_and_common_costs":_money(expected_realization),
        "conditional_expected_net_after_all_modelled_costs":_money(net),
        "conditional_break_even_purchase_price":_money(max_bid),
        "positive_expected_net_under_assumptions":net>0,
        "positive_realized_spread_verified":False,
        "available_inventory_verified":False,
        "actual_buyer_verified":False,
        "risk_of_model_misspecification":"Unmodeled returns, condition selection, currency changes, buyer defaults, unsold holding risk and opportunity costs can eliminate the modeled spread.",
        "decision":"RESEARCH_MORE_AND_VERIFY_QUOTES" if net>0 else "DO_NOT_BUY_AT_MODELED_PRICE",
    }

def build(atlas,operator_routes,scenarios=None,owner_targets=None):
    if (not isinstance(atlas,dict) or atlas.get("schema")!=ATLAS_SCHEMA or
        atlas.get("layers")!=["practical","academic","implementation"] or
        not isinstance(operator_routes,dict) or operator_routes.get("schema")!=ROUTES_SCHEMA):
        raise ValueError("Requires the original three-layer atlas and typed operator gate")
    if not isinstance(atlas.get("problem_views"),dict) or not isinstance(atlas.get("nodes"),list) or not isinstance(atlas.get("edges"),list):
        raise ValueError("Atlas lacks typed nodes/edges/views")
    nodes={x["id"]:x for x in atlas["nodes"]}
    if len(nodes)!=len(atlas["nodes"]) or any(x["layer"] not in atlas["layers"] for x in nodes.values()):
        raise ValueError("Duplicate or fourth-layer node")
    edges={(e["from"],e["to"]):e for e in atlas["edges"]}
    if len(edges)!=len(atlas["edges"]):
        raise ValueError("Ambiguous or duplicated graph edge identities")
    ranked=[]
    for root,view in atlas["problem_views"].items():
        if root not in nodes or nodes[root]["layer"]!="practical" or view.get("root")!=root:
            raise ValueError("Problem-view identity must match the practical graph node")
        mids=view.get("academic_nodes",[])
        impls=view.get("implementation_links",[])
        if not isinstance(mids,list) or not isinstance(impls,list):
            raise ValueError("Wrong view coverage")
        for mid in mids:
            if mid not in nodes or nodes[mid]["layer"]!="academic" or (root,mid) not in edges:
                raise ValueError("Academic node must be connected by an existing typed edge")
        for impl in impls:
            ident=impl["id"]
            if ident not in nodes or nodes[ident]["layer"]!="implementation":
                raise ValueError("Implementation listing must refer to an actual typed node")
            if not any((mid,ident) in edges for mid in mids) and (root,ident) not in edges:
                raise ValueError("No source-backed implementation path for stated problem")
        if view.get("end_to_end_validated") is not False or view.get("buyer_validated") is not False:
            raise ValueError("Existing atlas cannot self-elevate buyer or full solution status")
        three_layers=bool(mids and impls)
        institution=root.startswith("ted:")
        # Priority is a QUEUE for cheapest next evidence test, NOT an ROI
        # or economic profitability score. Stable and interpretable categories.
        group=("tri_layer_candidate_needs_falsification" if three_layers
               else "institutional_requirement_unmatched_or_partial" if institution
               else "problem_with_missing_source_family")
        if three_layers:
            next_test=("Verify problem prevalence and actual buyer/beneficiary constraints, "
                       "then test the exact component against a field-derived acceptance case")
        elif institution:
            next_test=("Recheck tender lifecycle, scope, bidder qualification and practical "
                       "requirements; never assume funding is accessible or a component fits")
        else:
            next_test=("Acquire the missing independent mechanism or implementation source "
                       "without inventing a lexical/semantic link")
        ranked.append({
            "id":root,
            "practical_summary":nodes[root]["statement"],
            "academic_refs":list(mids),
            "implementation_refs":[x["id"] for x in impls],
            "source_edge_statuses":[
                edges[(root,mid)]["status"] for mid in mids
            ]+[x.get("status","unverified") for x in impls],
            "complete_three_layer_representation":three_layers,
            "confirmed_problem_impact":False,
            "scientific_entailment_accepted":False,
            "verified_solution_fit":False,
            "confirmed_price_cost_spread":False,
            "route":"research_or_self_execution_hypothesis_not_commercial_conversion",
            "investigation_queue":group,
            "next_evidence_test":next_test,
        })
    ranked.sort(key=lambda x:(
        0 if x["complete_three_layer_representation"] else
        1 if x["id"].startswith("ted:") else 2,x["id"]))
    if not isinstance(operator_routes.get("rows"),list):
        raise ValueError("Missing operator case evidence")
    technical=[]
    seen=set()
    for entry in operator_routes["rows"]:
        if entry["id"] in seen:raise ValueError("Duplicate operator lead")
        seen.add(entry["id"])
        tech=entry["technical"]
        if (entry.get("buyer_verified") is not False or
            entry.get("commercial_unit_economics_verified") is not False or
            entry.get("paid_work_order_verified") is not False or
            tech.get("deployed_fit_verified") is not False):
            raise ValueError("Operator lead asserted unsupported revenue or market validation")
        now_next=entry["next_evidence_test"]
        if entry["route"]=="run_full_Rails_model_and_precision_policy_tests":
            now_next="Original Ruby helper regression already reproduced. Next run full Rails/ActiveRecord model and real invoice/quantity conversion tests under original project dependencies."
        elif entry["route"]=="wire_region_and_zoom_settings_then_test_full_map":
            now_next="Original CoffeeScript/Karma regression already reproduced. Next wire admin/instance region bounds and verify whole UI map viewport, dateline, country zoom and real records."
        technical.append({
            "id":entry["id"],"repository":entry["repository"],
            "practical_claim":entry["practical"],
            "academic_hypothesis":entry["academic"],
            "implementation_claim":entry["implementation"],
            "technical_status":tech["status"],
            "source_commit":tech["checked_source_sha"],
            "recommended_route":entry["route"],
            "limitation":tech["scope"],
            "rights_status":("blocked_for_reuse_pending_license_review" if
                             "license" in entry["route"] else
                             "third_party_license_and_use_require_separate_review"),
            "evidence_critical_advantage":"Source-scoped defect reproduction" if
                  tech.get("synthetic_result_reproduced") or
                  tech.get("source_app_component_runtime_verified")
                  else "Unverified",
            "economic_spread_verified":False,
            "market_or_operator_demand_confirmed":False,
            "owner_capture_hypotheses":[
                "Use knowledge internally to avoid a wrong engineering/bid decision",
                "Build an independently authorized integration or functional improvement",
                "Package reusable testing/reliability expertise if actual operator demand is measured",
            ],
            "next_evidence_test":now_next,
            "do_not_join_to_atlas_by_repo_name_alone":True,
        })
    technical.sort(key=lambda x:(0 if x["technical_status"].startswith("original_scoped") else
                                 1 if "scratch_only" in x["technical_status"] else 2,x["id"]))
    scenarios=scenarios or {"schema":ECON_SCHEMA,"items":[]}
    if not isinstance(scenarios,dict) or set(scenarios)!={"schema","items"} or scenarios["schema"]!=ECON_SCHEMA or not isinstance(scenarios["items"],list) or len(scenarios["items"])>10:
        raise ValueError("Only up to ten explicit user economics scenarios")
    financial=[scenario_economics(x) for x in scenarios["items"]]
    if len({x["id"] for x in financial})!=len(financial):
        raise ValueError("Duplicate economic scenario ID")
    owner_targets=owner_targets or {"schema":"cite_refinery.owner_arbitrage_hypotheses.v1","targets":[]}
    if (not isinstance(owner_targets,dict) or
        set(owner_targets)!={"schema","targets"} or
        owner_targets["schema"]!="cite_refinery.owner_arbitrage_hypotheses.v1" or
        not isinstance(owner_targets["targets"],list) or
        len(owner_targets["targets"])>10):
        raise ValueError("Owner opportunity themes require explicit provisional data schema")
    owner=[]
    known_practical=set(atlas["problem_views"])
    known_tech={x["id"] for x in technical}
    ids=set()
    for target in owner_targets["targets"]:
        if not isinstance(target,dict) or set(target)!={
            "id","strategy","geography","capture_method","owner_thesis",
            "linked_practical_ids","linked_test_case_ids",
            "first_falsification","evidence_status"
        }:
            raise ValueError("Every personal arbitrage hypothesis requires an explicit test and origin")
        if target["id"] in ids or not isinstance(target["id"],str) or len(target["id"])<5:
            raise ValueError("Repeated or invalid owner hypothesis")
        ids.add(target["id"])
        for field in ("strategy","geography","capture_method","owner_thesis","first_falsification"):
            if not isinstance(target[field],str) or not 15<=len(target[field].strip())<=650:
                raise ValueError("Owner thesis/capture/falsification must be substantive")
        if target["evidence_status"]!="user_strategy_hypothesis_not_market_verified":
            raise ValueError("User capture aspirations cannot be promoted to verified market demand")
        practical=target["linked_practical_ids"]
        tests=target["linked_test_case_ids"]
        if not isinstance(practical,list) or not isinstance(tests,list) or (
            len(set(practical))!=len(practical) or len(set(tests))!=len(tests)
        ) or not set(practical)<=known_practical or not set(tests)<=known_tech:
            raise ValueError("Owner overlay points only at exact existing evidence IDs")
        owner.append({**target,
            "links_are_references_not_new_cross_layer_edges":True,
            "inventory_or_demand_verified":False,
            "profitable_spread_verified":False,
            "permission_and_execution_unverified":True})
    return {
        "schema":SCHEMA,
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "input_sha256":{"three_layer_atlas":_canonical_hash(atlas),
                        "technical_operator_gate":_canonical_hash(operator_routes),
                        "financial_scenarios":_canonical_hash(scenarios),
                        "owner_strategy_hypotheses":_canonical_hash(owner_targets)},
        "conceptual_layers":["practical","academic","implementation"],
        "arbitrage_is_an_overlay_not_a_fourth_graph_layer":True,
        "atlas_problem_views":ranked,
        "independent_technical_repair_leads":technical,
        "conditional_asset_spread_scenarios":financial,
        "owner_hypothesis_watchlist":owner,
        "coverage":{
            "atlas_problem_views":len(ranked),
            "full_three_layer_candidate_views":sum(x["complete_three_layer_representation"] for x in ranked),
            "tested_technical_repair_leads":len(technical),
            "modeled_asset_spreads":len(financial),
            "user_strategy_priorities":len(owner),
            "verified_profitable_arbitrage":0,
            "verified_buyers_or_customers":0,
            "validated_impactful_field_integrations":0,
        },
        "owner_priority":"Map broadly, then test source-verifiable executable advantages and fill missing price/cost/capture evidence before committing capital.",
        "anti_claims":[
            "A matched graph path is not market inefficiency or a profitable spread",
            "A public procurement listing is not a contract awarded to us or evidence of bidder eligibility",
            "A repaired synthetic component is not a ready commercial product",
            "No third-party code exploitation, license clearance or deployment permission implied",
            "Financial scenarios require real condition-matched buy/sell quotes and complete failure costs",
            "Do not claim buyer demand or commercialization merely from OSS issue existence",
        ],
        "research_holdout_touched":False,
        "graph_authority_promoted":False,
        "executed_trade_or_order":False,
        "limitation":"Read-only internal lead map from existing non-exhaustive source atlas, operator repairs and optional self-supplied economic assumptions. No live price search, independent buyer verification or trade execution.",
    }

def markdown(result):
    if result.get("schema")!=SCHEMA:raise ValueError("Unknown internal arbitrage schema")
    coverage=result["coverage"]
    lines=["# Cite–Refinery | Internal arbitrage reconnaissance","",
        f"**Coverage:** {coverage['atlas_problem_views']} practical views; "
        f"{coverage['full_three_layer_candidate_views']} paths with all three layers represented; "
        f"{coverage['tested_technical_repair_leads']} independently tracked technical leads; "
        f"{coverage['modeled_asset_spreads']} conditional asset-spread scenarios.","",
        "**Confirmed profitable arbitrage: 0.** None of the leads has verified purchase/sale "
        "spread, customer, deployed intervention, or commercial conversion. "
        "The map orders *what to investigate*, not estimated profit.","",
        "## Three-layer exploration queue","",
        "| Practical lead | Academic refs | Implementation refs | What is known |",
        "|---|---:|---:|---|"]
    for row in result["atlas_problem_views"]:
        lines.append("| "+row["id"].replace("|","/")+" | "+str(len(row["academic_refs"]))+
                     " | "+str(len(row["implementation_refs"]))+" | "+
                     row["investigation_queue"]+" |")
    lines.extend(["","## Technical lead watchlist — kept separate from graph paths","",
                  "Technical bug evidence is not market demand. These leads are NOT joined to "
                  "unrelated academic graphs merely because a repository name recurs.","",
                  "| Source-backed component | Evidence scope | Required next move |",
                  "|---|---|---|"])
    for x in result["independent_technical_repair_leads"]:
        lines.append("| "+x["repository"]+" | "+x["technical_status"]+
                     " | "+x["next_evidence_test"].replace("|","/")+" |")
    lines.extend(["","## Our own capture hypotheses (NOT automatically new graph edges)",""])
    if result["owner_hypothesis_watchlist"]:
        for x in result["owner_hypothesis_watchlist"]:
            lines.extend([
                "### "+x["strategy"],"",
                "**Where:** "+x["geography"],
                "",
                "**Potential owner advantage:** "+x["owner_thesis"],
                "",
                "**How we might capture it:** "+x["capture_method"],
                "",
                "**First disconfirmation:** "+x["first_falsification"],
                "",
                "**Evidence connections:** Practical IDs "+(", ".join(x["linked_practical_ids"]) or "NONE")+"; technical cases "+(", ".join(x["linked_test_case_ids"]) or "NONE")+".",
                "**Status:** Unverified internal strategy. Links are references, NOT added graph relationships.",
                "",
            ])
    else:
        lines.append("No owner prioritization strategy is supplied; internal candidate mapping remains broad.")
    lines.extend(["","## Asset purchase / repair / resale calculator (conditional)",""])
    if result["conditional_asset_spread_scenarios"]:
        lines.extend(["| Scenario | Currency | Conditional net | Break-even purchase price | Action |",
                      "|---|---|---:|---:|---|"])
        for x in result["conditional_asset_spread_scenarios"]:
            lines.append("| "+x["id"]+" | "+x["currency"]+" | "+
                         x["conditional_expected_net_after_all_modelled_costs"]+" | "+
                         x["conditional_break_even_purchase_price"]+" | "+x["decision"]+" |")
    else:
        lines.append("No actual purchase, success probability, resale, loss-path or cost "
                     "inputs have been supplied. The system correctly abstains from forecasting profit.")
    lines.extend(["","## First verification gates for our own value capture","",
        "1. **Technical asymmetry:** replicate a neglected defect with source identity and a negative test.",
        "2. **Acquisition / price asymmetry:** obtain contemporaneous, condition-matched buy and *realized* sell prices; include shipping, repair labor, platform fees, tax, defects and failure recovery.",
        "3. **Permission / access:** verify rights, available inventory, delivery channel, bidder eligibility and legal constraints.",
        "4. **Capture:** prove that we can personally exploit the difference through an authorized product, repair/resale transaction, avoided cost or justified integration.",
        "5. **Falsify quickly:** reject leads lacking executable fit, clear unit economics or access rather than using model enthusiasm as evidence.",
        "",
        "**This is our internal arbitrage atlas, not a fourth conceptual layer, "
        "paid consulting forecast, execution bot or verified financial valuation.**",""])
    return "\n".join(lines)
