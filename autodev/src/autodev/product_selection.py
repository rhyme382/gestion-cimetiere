"""Feature selection with stable ordering and Git dependency verification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autodev.git_tools import GitError, is_ancestor
from autodev.product_incidents import IncidentRepeatability, IncidentScope, IncidentSeverity, ProductIncident
from autodev.product_plan import Feature, ProductPlan


class ProductSelectionError(RuntimeError):
    """Error during feature selection."""


class DependencyIncident(ProductIncident):
    """Incident related to feature dependencies."""

    def __init__(self, code: str, reason: str, feature_id: str | None = None):
        evidence = [reason]
        if feature_id:
            evidence.append(f"Feature: {feature_id}")
        super().__init__(
            code=code,
            severity=IncidentSeverity.HIGH,
            scope=IncidentScope.DEPENDENCY,
            proofs=evidence,
            repeatability=IncidentRepeatability.ALWAYS,
            recommended_action=f"Investigate dependency state: {reason}",
            retryable=False,
            deferrable=False,
            correctable_under_supervision=True,
            terminal=False,
            title=f"Dependency incident: {code}",
            description=reason,
        )


@dataclass(frozen=True)
class SelectionResult:
    """Result of feature selection."""

    selected_feature: Feature | None
    eligible_features: list[Feature]
    ineligible_features: list[Feature]
    incidents: list[ProductIncident]
    rationale: str


def verify_dependency_integration(
    repo_root: Path,
    feature: Feature,
    plan: ProductPlan,
    product_base_commit: str,
    integrated_commits: dict[str, str],
) -> tuple[bool, list[ProductIncident]]:
    """
    Verify that all dependencies of a feature are integrated via Git ancestry.

    Args:
        repo_root: Repository root path
        feature: Feature to verify dependencies for
        plan: Product plan containing all features
        product_base_commit: Current product base commit
        integrated_commits: Mapping of feature_id to integrated commit hash

    Returns:
        Tuple of (all_dependencies_satisfied, incidents_list)
    """
    incidents: list[ProductIncident] = []

    if not feature.depends_on:
        return True, incidents

    features_by_id = {f.feature_id: f for f in plan.features}
    all_satisfied = True

    for dep_feature_id in feature.depends_on:
        if dep_feature_id not in features_by_id:
            incident = DependencyIncident(
                code="UNKNOWN_DEPENDENCY",
                reason=f"Feature '{feature.feature_id}' depends on unknown feature '{dep_feature_id}'",
                feature_id=feature.feature_id,
            )
            incidents.append(incident)
            all_satisfied = False
            continue

        if dep_feature_id not in integrated_commits:
            incident = DependencyIncident(
                code="DEPENDENCY_NOT_INTEGRATED",
                reason=f"Feature '{feature.feature_id}' depends on '{dep_feature_id}' which has no integrated commit",
                feature_id=feature.feature_id,
            )
            incidents.append(incident)
            all_satisfied = False
            continue

        dep_commit = integrated_commits[dep_feature_id]
        try:
            is_ancestor_result = is_ancestor(repo_root, dep_commit, product_base_commit)
        except GitError as exc:
            incident = DependencyIncident(
                code="GIT_ANCESTOR_CHECK_FAILED",
                reason=f"Failed to verify Git ancestry for dependency '{dep_feature_id}': {exc}",
                feature_id=feature.feature_id,
            )
            incidents.append(incident)
            all_satisfied = False
            continue

        if not is_ancestor_result:
            incident = DependencyIncident(
                code="DEPENDENCY_COMMIT_NOT_ANCESTOR",
                reason=(
                    f"Feature '{feature.feature_id}' depends on '{dep_feature_id}' "
                    f"(commit {dep_commit[:8]}...), but this commit is not an ancestor "
                    f"of the current product base ({product_base_commit[:8]}...)"
                ),
                feature_id=feature.feature_id,
            )
            incidents.append(incident)
            all_satisfied = False

    return all_satisfied, incidents


def _calculate_dependency_depth(feature_id: str, plan: ProductPlan, memo: dict[str, int]) -> int:
    """
    Calculate the dependency depth of a feature.

    A feature with no dependencies has depth 0.
    A feature's depth is 1 + max depth of its dependencies.

    Args:
        feature_id: Feature to calculate depth for
        plan: Product plan containing all features
        memo: Memoization cache for depths

    Returns:
        Dependency depth (0 for no dependencies, higher for dependent features)
    """
    if feature_id in memo:
        return memo[feature_id]

    features_by_id = {f.feature_id: f for f in plan.features}
    feature = features_by_id.get(feature_id)

    if not feature or not feature.depends_on:
        depth = 0
    else:
        max_dep_depth = 0
        for dep_id in feature.depends_on:
            if dep_id in features_by_id:
                dep_depth = _calculate_dependency_depth(dep_id, plan, memo)
                max_dep_depth = max(max_dep_depth, dep_depth)
        depth = max_dep_depth + 1

    memo[feature_id] = depth
    return depth


def select_next_feature(
    plan: ProductPlan,
    product_base_commit: str,
    repo_root: Path,
    feature_statuses: dict[str, dict[str, Any]],
    integrated_commits: dict[str, str],
) -> SelectionResult:
    """
    Select the next feature to process based on stable ordering.

    Selection order: dependencies satisfied -> dependency depth (ascending) -> priority (high to low) -> feature_id (alphabetical).

    Args:
        plan: Product plan with features to select from
        product_base_commit: Current product base commit for Git ancestor verification
        repo_root: Repository root for Git operations
        feature_statuses: Mapping of feature_id to status dict with 'status' key
        integrated_commits: Mapping of feature_id to integrated commit hash

    Returns:
        SelectionResult with selected feature and diagnostic information
    """
    incidents: list[ProductIncident] = []
    eligible: list[Feature] = []
    ineligible: list[Feature] = []

    for feature in plan.features:
        # Check if feature was already completed
        feature_status = feature_statuses.get(feature.feature_id, {})
        status = feature_status.get("status", "NOT_STARTED")

        if status == "COMPLETED":
            incident = ProductIncident(
                code="FEATURE_ALREADY_COMPLETED",
                severity=IncidentSeverity.HIGH,
                scope=IncidentScope.DEPENDENCY,
                proofs=[f"Feature '{feature.feature_id}' has status COMPLETED"],
                repeatability=IncidentRepeatability.ALWAYS,
                recommended_action="Do not relaunch completed features",
                retryable=False,
                deferrable=False,
                correctable_under_supervision=True,
                terminal=False,
                title=f"Completed feature would be relaunched: {feature.feature_id}",
                description=f"Feature '{feature.feature_id}' is already completed and should not be relaunched",
            )
            incidents.append(incident)
            ineligible.append(feature)
            continue

        # Check for incoherence: feature already integrated but not marked COMPLETED
        if feature.feature_id in integrated_commits and status != "COMPLETED":
            incident = ProductIncident(
                code="FEATURE_INCOHERENT_STATUS",
                severity=IncidentSeverity.HIGH,
                scope=IncidentScope.DEPENDENCY,
                proofs=[
                    f"Feature '{feature.feature_id}' has integrated commit but status is '{status}'",
                    f"Integrated commit: {integrated_commits[feature.feature_id][:8]}...",
                ],
                repeatability=IncidentRepeatability.ALWAYS,
                recommended_action="Mark feature as COMPLETED or investigate Git state",
                retryable=False,
                deferrable=False,
                correctable_under_supervision=True,
                terminal=False,
                title=f"Incoherent feature state: {feature.feature_id}",
                description=(
                    f"Feature '{feature.feature_id}' has an integrated commit in the product base "
                    f"but is not marked as COMPLETED. This indicates an incoherent state that should not be relaunched."
                ),
            )
            incidents.append(incident)
            ineligible.append(feature)
            continue

        # Verify dependencies
        deps_satisfied, dep_incidents = verify_dependency_integration(
            repo_root=repo_root,
            feature=feature,
            plan=plan,
            product_base_commit=product_base_commit,
            integrated_commits=integrated_commits,
        )
        incidents.extend(dep_incidents)

        if not deps_satisfied:
            ineligible.append(feature)
            continue

        eligible.append(feature)

    # Calculate dependency depths for sorting
    depth_memo: dict[str, int] = {}
    for feature in eligible:
        _calculate_dependency_depth(feature.feature_id, plan, depth_memo)

    # Sort eligible features: dependency depth (ascending), priority (descending), then feature_id (ascending)
    eligible.sort(key=lambda f: (depth_memo.get(f.feature_id, 0), -f.priority, f.feature_id))

    selected = eligible[0] if eligible else None
    rationale = _build_selection_rationale(selected, eligible, ineligible, incidents)

    return SelectionResult(
        selected_feature=selected,
        eligible_features=eligible,
        ineligible_features=ineligible,
        incidents=incidents,
        rationale=rationale,
    )


def _build_selection_rationale(
    selected: Feature | None,
    eligible: list[Feature],
    ineligible: list[Feature],
    incidents: list[ProductIncident],
) -> str:
    lines: list[str] = []

    if incidents:
        lines.append(f"Incidents detected: {len(incidents)}")
        for inc in incidents:
            lines.append(f"  - {inc.code}: {inc.description}")
        lines.append("")

    if selected:
        lines.append(f"Selected: {selected.feature_id} (priority={selected.priority})")
        if len(eligible) > 1:
            lines.append(f"Other eligible: {', '.join(f.feature_id for f in eligible[1:])}")
    else:
        lines.append("No feature selected")

    if ineligible:
        lines.append(f"Ineligible: {len(ineligible)} features")

    return "\n".join(lines)
