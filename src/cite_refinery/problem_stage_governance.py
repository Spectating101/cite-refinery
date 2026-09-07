from __future__ import annotations

from dataclasses import dataclass, field

from .problem_governance import GateKind, GateStatus, InterventionEnvelope
from .problem_stages import (
    AuthorityLevel,
    ProblemStage,
    SYSTEM_PUBLIC_GOOD,
    StageProfile,
)


@dataclass(slots=True)
class StageGovernanceAlignment:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def align_stage_and_governance(profile: StageProfile, envelope: InterventionEnvelope) -> StageGovernanceAlignment:
    """Check that stage semantics and intervention governance tell one story.

    This does not merge the two extensions. It only prevents contradictory
    classifications from silently crossing the Design/Test/Deploy boundary.
    """

    errors: list[str] = []
    warnings: list[str] = []

    if profile.problem_id != envelope.problem_id:
        errors.append("problem_id mismatch between stage profile and governance envelope")
    if profile.subproblem_id != envelope.subproblem_id:
        errors.append("subproblem_id mismatch between stage profile and governance envelope")

    intervention_stages = {ProblemStage.DESIGN, ProblemStage.BUILD, ProblemStage.TEST, ProblemStage.DEPLOY}
    if profile.stage not in intervention_stages:
        warnings.append(f"governance envelope attached to {profile.stage.value} stage; verify that a concrete intervention already exists")

    if profile.stage in {ProblemStage.DESIGN, ProblemStage.TEST, ProblemStage.DEPLOY} and SYSTEM_PUBLIC_GOOD not in profile.system_routes:
        warnings.append(f"{profile.stage.value} stage does not route to Public-Good despite having an intervention envelope")

    professional = envelope.gate(GateKind.PROFESSIONAL)
    if profile.authority_level == AuthorityLevel.QUALIFIED:
        if professional is None or professional.status != GateStatus.SATISFIED:
            errors.append("qualified stage requires a satisfied professional governance gate")

    if profile.stage == ProblemStage.TEST:
        readiness = envelope.readiness("test")
        if not readiness.ready:
            errors.extend(f"test governance: {item}" for item in readiness.blockers)

    if profile.stage == ProblemStage.DEPLOY:
        if profile.authority_level != AuthorityLevel.INSTITUTIONAL:
            errors.append("deploy stage requires institutional stage authority")
        readiness = envelope.readiness("deploy")
        if not readiness.ready:
            errors.extend(f"deploy governance: {item}" for item in readiness.blockers)

    if profile.stage == ProblemStage.BUILD and envelope.readiness("review").ready is False:
        warnings.append("build is attached to an intervention envelope that is not yet review-ready; prototype capability must not be interpreted as intervention validity")

    return StageGovernanceAlignment(valid=not errors, errors=errors, warnings=warnings)
