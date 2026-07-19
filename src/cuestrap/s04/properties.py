"""Executable S04 assertion catalog and controlled graph mutations."""
from __future__ import annotations

from copy import deepcopy
from enum import StrEnum
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict


class AssertionLayer(StrEnum):
    PYDANTIC = "pydantic"
    CUE = "cue"
    HYPOTHESIS = "hypothesis"


class ObjectAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    assertion_id: str
    object_kind: str
    layer: AssertionLayer
    statement: str
    property_family: Literal["shape", "identity", "coherence", "publication", "metamorphic"]


OBJECT_ASSERTIONS: tuple[ObjectAssertion, ...] = tuple(
    ObjectAssertion(**item)
    for item in (
        {"assertion_id": "authority.role-source-shape", "object_kind": "AuthorityBinding", "layer": "pydantic", "statement": "authority role and source envelope are closed and typed", "property_family": "shape"},
        {"assertion_id": "subject.ref-identity", "object_kind": "SubjectRef", "layer": "cue", "statement": "subject and optional materialization references resolve and agree", "property_family": "identity"},
        {"assertion_id": "operation.discriminated-shape", "object_kind": "PrimitiveOperation", "layer": "pydantic", "statement": "operation kind determines direction and operand arity", "property_family": "shape"},
        {"assertion_id": "plan.case-subject-locality", "object_kind": "OperationPlan", "layer": "cue", "statement": "every selected plan operand belongs to the selecting case subject set", "property_family": "coherence"},
        {"assertion_id": "plan.fact-production-locality", "object_kind": "OperationPlan", "layer": "cue", "statement": "every case normalization input is produced by its selected plan", "property_family": "coherence"},
        {"assertion_id": "claim.expected-value-preservation", "object_kind": "ExpectedFact", "layer": "cue", "statement": "expected facts preserve claim authority, predicate, and value", "property_family": "coherence"},
        {"assertion_id": "normalization.case-selection", "object_kind": "NormalizationRule", "layer": "cue", "statement": "case comparison inputs arise from normalization rules selected by that case", "property_family": "coherence"},
        {"assertion_id": "comparison.expected-fact-selection", "object_kind": "ComparisonRule", "layer": "cue", "statement": "case comparison rules reference expected facts selected by that case", "property_family": "coherence"},
        {"assertion_id": "capability.operation-coverage", "object_kind": "BackendCapabilityRequirement", "layer": "cue", "statement": "every selected plan operation kind is covered by a selected required capability", "property_family": "coherence"},
        {"assertion_id": "observation.envelope-binding", "object_kind": "ObservationRecord", "layer": "pydantic", "statement": "facts preserve enclosing observation identity and digest", "property_family": "identity"},
        {"assertion_id": "judgement.hidden-proof-publication", "object_kind": "JudgementDerivation", "layer": "cue", "statement": "judgement publication forces all authority, case, rule-list, integrity, and outcome checks", "property_family": "publication"},
        {"assertion_id": "projection.total-proof-publication", "object_kind": "S04PPFProjectionDerivation", "layer": "cue", "statement": "projection publication forces totality, membership, role, validator, and realization integrity checks", "property_family": "publication"},
        {"assertion_id": "contract.proof-publication", "object_kind": "QualifiedS04ConsumerProfileContract", "layer": "cue", "statement": "contract publication forces realization equality and the qualified projection proof", "property_family": "publication"},
        {"assertion_id": "graph.unrelated-extension-invariance", "object_kind": "CueRealization", "layer": "hypothesis", "statement": "adding unrelated valid graph members does not change a selected case judgement", "property_family": "metamorphic"},
    )
)


class JudgementMutation(StrEnum):
    WRONG_SEMANTIC_AUTHORITY_ROLE = "wrong-semantic-authority-role"
    WRONG_OBSERVER_AUTHORITY_ROLE = "wrong-observer-authority-role"
    OBSERVATION_CASE_MISMATCH = "observation-case-mismatch"
    NORMALIZATION_RULE_LIST_MISMATCH = "normalization-rule-list-mismatch"
    COMPARISON_RULE_LIST_MISMATCH = "comparison-rule-list-mismatch"


class CaseCoherenceMutation(StrEnum):
    PLAN_SUBJECT_OUTSIDE_CASE = "plan-subject-outside-case"
    NORMALIZATION_INPUT_NOT_PRODUCED = "normalization-input-not-produced"
    COMPARISON_EXPECTED_FACT_OUTSIDE_CASE = "comparison-expected-fact-outside-case"
    COMPARISON_NORMALIZED_FACT_OUTSIDE_CASE = "comparison-normalized-fact-outside-case"
    OPERATION_KIND_NOT_COVERED = "operation-kind-not-covered"


class ProjectionMutation(StrEnum):
    WRONG_SEMANTIC_AUTHORITY_ROLE = "wrong-semantic-authority-role"
    WRONG_PACKAGE_DECLARER_ROLE = "wrong-package-declarer-role"
    WRONG_RAW_OBSERVER_ROLE = "wrong-raw-observer-role"
    MISSING_REALIZATION_CASE = "missing-realization-case"
    FOREIGN_REALIZATION_CASE = "foreign-realization-case"
    MISSING_PACKAGE_TARGET = "missing-package-target"
    VALIDATOR_AUTHORITY_MISMATCH = "validator-authority-mismatch"


class ContractMutation(StrEnum):
    REALIZATION_MISMATCH = "realization-mismatch"
    PROJECTION_MISMATCH = "projection-mismatch"


MutationFunction = Callable[[dict[str, Any]], dict[str, Any]]


def mutate_judgement(value: dict[str, Any], mutation: JudgementMutation) -> dict[str, Any]:
    result = deepcopy(value)
    realization = result["realization"]
    ingress = result["ingress"]
    if mutation == JudgementMutation.WRONG_SEMANTIC_AUTHORITY_ROLE:
        authority_id = ingress["semanticAuthorityID"]
        realization["authorities"][authority_id]["role"] = "package-declarer"
    elif mutation == JudgementMutation.WRONG_OBSERVER_AUTHORITY_ROLE:
        authority_id = ingress["observation"]["observerAuthorityID"]
        realization["authorities"][authority_id]["role"] = "package-declarer"
    elif mutation == JudgementMutation.OBSERVATION_CASE_MISMATCH:
        ingress["observation"]["caseID"] = "foreign-case"
    elif mutation == JudgementMutation.NORMALIZATION_RULE_LIST_MISMATCH:
        case = realization["cases"][ingress["caseID"]]
        existing_id = case["normalizationRuleIDs"][0]
        alternate_id = "alternate-normalization"
        alternate = deepcopy(realization["normalizationRules"][existing_id])
        alternate["ruleID"] = alternate_id
        realization["normalizationRules"][alternate_id] = alternate
        ingress["normalizationRuleIDs"] = [alternate_id]
    elif mutation == JudgementMutation.COMPARISON_RULE_LIST_MISMATCH:
        case = realization["cases"][ingress["caseID"]]
        existing_id = case["comparisonRuleIDs"][0]
        alternate_id = "alternate-comparison"
        alternate = deepcopy(realization["comparisonRules"][existing_id])
        alternate["ruleID"] = alternate_id
        realization["comparisonRules"][alternate_id] = alternate
        ingress["comparisonRuleIDs"] = [alternate_id]
    else:
        raise AssertionError(mutation)
    return result


def mutate_case_coherence(value: dict[str, Any], mutation: CaseCoherenceMutation) -> dict[str, Any]:
    result = deepcopy(value)
    realization = result["realization"]
    ingress = result["ingress"]
    case = realization["cases"][ingress["caseID"]]
    plan = realization["plans"][case["planID"]]
    operation = plan["operations"][0]
    if mutation == CaseCoherenceMutation.PLAN_SUBJECT_OUTSIDE_CASE:
        case["subjectIDs"] = [operation["left"]["subjectID"]]
    elif mutation == CaseCoherenceMutation.NORMALIZATION_INPUT_NOT_PRODUCED:
        operation["produces"] = ["unrelated-raw"]
    elif mutation == CaseCoherenceMutation.COMPARISON_EXPECTED_FACT_OUTSIDE_CASE:
        existing_id = case["expectedFactIDs"][0]
        unrelated_id = "unrelated-expected"
        realization["expectedFacts"][unrelated_id] = deepcopy(realization["expectedFacts"][existing_id])
        realization["expectedFacts"][unrelated_id]["factID"] = unrelated_id
        comparison_id = case["comparisonRuleIDs"][0]
        realization["comparisonRules"][comparison_id]["expectedFactID"] = unrelated_id
    elif mutation == CaseCoherenceMutation.COMPARISON_NORMALIZED_FACT_OUTSIDE_CASE:
        comparison_id = case["comparisonRuleIDs"][0]
        unrelated_rule_id = "unrelated-normalization"
        existing_rule_id = case["normalizationRuleIDs"][0]
        unrelated = deepcopy(realization["normalizationRules"][existing_rule_id])
        unrelated["ruleID"] = unrelated_rule_id
        unrelated["normalizedFactID"] = "unrelated-normalized"
        realization["normalizationRules"][unrelated_rule_id] = unrelated
        realization["comparisonRules"][comparison_id]["normalizedFactID"] = "unrelated-normalized"
    elif mutation == CaseCoherenceMutation.OPERATION_KIND_NOT_COVERED:
        capability_id = case["requiredCapabilityIDs"][0]
        realization["capabilityRequirements"][capability_id]["operationKinds"] = ["validate"]
    else:
        raise AssertionError(mutation)
    return result


def mutate_projection(value: dict[str, Any], mutation: ProjectionMutation) -> dict[str, Any]:
    result = deepcopy(value)
    realization = result["realizationArtifact"]["realization"]
    package = result["package"]
    request = result["request"]
    if mutation == ProjectionMutation.WRONG_SEMANTIC_AUTHORITY_ROLE:
        realization["authorities"][request["semanticAuthorityID"]]["role"] = "package-declarer"
    elif mutation == ProjectionMutation.WRONG_PACKAGE_DECLARER_ROLE:
        realization["authorities"][request["packageDeclarerAuthorityID"]]["role"] = "raw-observer"
    elif mutation == ProjectionMutation.WRONG_RAW_OBSERVER_ROLE:
        realization["authorities"][request["rawObserverAuthorityIDs"][0]]["role"] = "package-declarer"
    elif mutation == ProjectionMutation.MISSING_REALIZATION_CASE:
        request["caseMap"] = {}
    elif mutation == ProjectionMutation.FOREIGN_REALIZATION_CASE:
        package_case = next(iter(request["caseMap"].values()))
        request["caseMap"] = {"foreign-case": package_case}
    elif mutation == ProjectionMutation.MISSING_PACKAGE_TARGET:
        source_case = next(iter(request["caseMap"]))
        request["caseMap"] = {source_case: "missing-package-case"}
    elif mutation == ProjectionMutation.VALIDATOR_AUTHORITY_MISMATCH:
        package["validator"]["semanticAuthorityID"] = request["packageDeclarerAuthorityID"]
    else:
        raise AssertionError(mutation)
    return result


def mutate_contract(value: dict[str, Any], mutation: ContractMutation) -> dict[str, Any]:
    result = deepcopy(value)
    if mutation == ContractMutation.REALIZATION_MISMATCH:
        result["candidateContract"]["realization"]["title"] = "mismatched realization"
    elif mutation == ContractMutation.PROJECTION_MISMATCH:
        result["candidateContract"]["projection"]["packageID"] = "foreign-package"
    else:
        raise AssertionError(mutation)
    return result
