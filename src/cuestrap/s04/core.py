"""Typed construction model for the S04 semantic contract.

Pydantic owns transport shape, local identity rules, and deterministic
serialization. Cross-object semantic admissibility remains a CUE concern.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, model_validator

SafeID = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")]
Digest = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
RelativePath = Annotated[str, StringConstraints(min_length=1), AfterValidator(lambda value: _validate_relative_path(value))]
NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
FactValue: TypeAlias = bool | int | float | str


class S04Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    def cue_data(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True, mode="json")


class AuthorityRole(StrEnum):
    SEMANTIC = "semantic-authority"
    PACKAGE_DECLARER = "package-declarer"
    RAW_OBSERVER = "raw-observer"


class AuthoritySourceKind(StrEnum):
    CUE_MODULE = "cue-module"
    PROBLEM_PACKAGE = "problem-package"
    NATIVE_RUNNER = "native-runner"
    PROCESS_RUNNER = "process-runner"


class AuthoritySource(S04Model):
    kind: AuthoritySourceKind
    locator: NonEmptyString
    revision: NonEmptyString
    digest: Digest


class AuthorityBinding(S04Model):
    authority_id: SafeID = Field(alias="authorityID")
    role: AuthorityRole
    source: AuthoritySource


class InlineSubjectSource(S04Model):
    kind: Literal["inline"]
    expression: NonEmptyString


class PathSubjectSource(S04Model):
    kind: Literal["path"]
    path: RelativePath
    digest: Digest


SubjectSource: TypeAlias = Annotated[
    InlineSubjectSource | PathSubjectSource,
    Field(discriminator="kind"),
]


class SubjectSpec(S04Model):
    subject_id: SafeID = Field(alias="subjectID")
    language: Literal["cue"] = "cue"
    source: SubjectSource
    media_type: Literal["application/cue"] = Field(alias="mediaType", default="application/cue")


class FileIdentity(S04Model):
    path: RelativePath
    digest: Digest


class MaterializedSubjectIdentity(S04Model):
    materialization_id: SafeID = Field(alias="materializationID")
    realization_id: SafeID = Field(alias="realizationID")
    subject_id: SafeID = Field(alias="subjectID")
    materialization_digest: Digest = Field(alias="materializationDigest")
    files: dict[SafeID, FileIdentity]


class SubjectRef(S04Model):
    subject_id: SafeID = Field(alias="subjectID")
    materialization_id: SafeID | None = Field(alias="materializationID", default=None)


class UnifyOperation(S04Model):
    operation_id: SafeID = Field(alias="operationID")
    kind: Literal["unify"]
    left: SubjectRef
    right: SubjectRef
    direction: Literal["symmetric"] = "symmetric"
    produces: list[SafeID] = Field(min_length=1)


class SubsumesOperation(S04Model):
    operation_id: SafeID = Field(alias="operationID")
    kind: Literal["subsumes"]
    left: SubjectRef
    right: SubjectRef
    direction: Literal["left-to-right", "right-to-left"]
    produces: list[SafeID] = Field(min_length=1)


class ValidateOperation(S04Model):
    operation_id: SafeID = Field(alias="operationID")
    kind: Literal["validate"]
    left: SubjectRef
    direction: Literal["subject-only"] = "subject-only"
    produces: list[SafeID] = Field(min_length=1)


PrimitiveOperation: TypeAlias = Annotated[
    UnifyOperation | SubsumesOperation | ValidateOperation,
    Field(discriminator="kind"),
]


class OperationPlan(S04Model):
    plan_id: SafeID = Field(alias="planID")
    operations: list[PrimitiveOperation] = Field(min_length=1)


class SemanticClaim(S04Model):
    claim_id: SafeID = Field(alias="claimID")
    authority_id: SafeID = Field(alias="authorityID")
    predicate: SafeID
    operands: list[SubjectRef] = Field(min_length=1)
    value: FactValue


class ExpectedFact(S04Model):
    fact_id: SafeID = Field(alias="factID")
    claim_id: SafeID = Field(alias="claimID")
    authority_id: SafeID = Field(alias="authorityID")
    predicate: SafeID
    expected_value: FactValue = Field(alias="expectedValue")


class ObservationFact(S04Model):
    fact_id: SafeID = Field(alias="factID")
    observation_id: SafeID = Field(alias="observationID")
    predicate: SafeID
    observed_value: FactValue = Field(alias="observedValue")
    source_record_digest: Digest = Field(alias="sourceRecordDigest")


class NormalizationRule(S04Model):
    rule_id: SafeID = Field(alias="ruleID")
    observation_fact_id: SafeID = Field(alias="observationFactID")
    normalized_fact_id: SafeID = Field(alias="normalizedFactID")
    normalized_predicate: SafeID = Field(alias="normalizedPredicate")


class ComparisonOperator(StrEnum):
    EQUALS = "equals"
    NOT_EQUALS = "not-equals"


class ComparisonRule(S04Model):
    rule_id: SafeID = Field(alias="ruleID")
    expected_fact_id: SafeID = Field(alias="expectedFactID")
    normalized_fact_id: SafeID = Field(alias="normalizedFactID")
    operator: ComparisonOperator
    result_predicate: SafeID = Field(alias="resultPredicate")


class PrimitiveOperationKind(StrEnum):
    UNIFY = "unify"
    SUBSUMES = "subsumes"
    VALIDATE = "validate"


class BackendCapabilityRequirement(S04Model):
    capability_id: SafeID = Field(alias="capabilityID")
    operation_kinds: list[PrimitiveOperationKind] = Field(alias="operationKinds", min_length=1)
    required: Literal[True] = True


class SemanticOutcome(StrEnum):
    SATISFIED = "satisfied"
    REJECTED = "rejected"
    INDETERMINATE = "indeterminate"


class OutcomeConstraint(S04Model):
    permitted: list[SemanticOutcome] = Field(min_length=1)
    required: SemanticOutcome | None = None

    @model_validator(mode="after")
    def required_is_permitted(self) -> "OutcomeConstraint":
        if self.required is not None and self.required not in self.permitted:
            raise ValueError("required outcome must be permitted")
        if len(set(self.permitted)) != len(self.permitted):
            raise ValueError("permitted outcomes must be unique")
        return self


class RealizationCase(S04Model):
    case_id: SafeID = Field(alias="caseID")
    group_id: SafeID = Field(alias="groupID")
    plan_id: SafeID = Field(alias="planID")
    subject_ids: list[SafeID] = Field(alias="subjectIDs", min_length=1)
    expected_fact_ids: list[SafeID] = Field(alias="expectedFactIDs", min_length=1)
    normalization_rule_ids: list[SafeID] = Field(alias="normalizationRuleIDs", min_length=1)
    comparison_rule_ids: list[SafeID] = Field(alias="comparisonRuleIDs", min_length=1)
    required_capability_ids: list[SafeID] = Field(alias="requiredCapabilityIDs", min_length=1)
    outcome_constraint: OutcomeConstraint = Field(alias="outcomeConstraint")

    @model_validator(mode="after")
    def lists_are_unique(self) -> "RealizationCase":
        for name in (
            "subject_ids",
            "expected_fact_ids",
            "normalization_rule_ids",
            "comparison_rule_ids",
            "required_capability_ids",
        ):
            values = getattr(self, name)
            if len(set(values)) != len(values):
                raise ValueError(f"{name} must contain unique IDs")
        return self


class EvaluatorIdentity(S04Model):
    cue_revision: Literal["806821e40fae070318600a264d311517e596353b"] = Field(alias="cueRevision")
    language_version: Literal["v0.18.0"] = Field(alias="languageVersion")
    relation_id: Literal["s04.derive-semantic-judgement.v0"] = Field(alias="relationID")
    facade_digest: Digest = Field(alias="facadeDigest")


class Diagnostic(S04Model):
    code: SafeID
    message: NonEmptyString
    path: RelativePath | None = None


class ObservationState(StrEnum):
    FACTS_OBSERVED = "facts-observed"
    TRANSPORT_FAILURE = "transport-failure"
    CAPABILITY_ABSENT = "capability-absent"
    INVALID_OBSERVATION = "invalid-observation"


class ObservationRecord(S04Model):
    schema_: Literal["s04.observation-record.v0"] = Field(alias="schema")
    observation_id: SafeID = Field(alias="observationID")
    case_id: SafeID = Field(alias="caseID")
    observer_authority_id: SafeID = Field(alias="observerAuthorityID")
    source_record_digest: Digest = Field(alias="sourceRecordDigest")
    state: ObservationState
    facts: dict[SafeID, ObservationFact]
    diagnostics: list[Diagnostic] | None = None

    @model_validator(mode="after")
    def bind_facts_and_state(self) -> "ObservationRecord":
        _keys_match_ids(self.facts, "fact_id", "facts")
        for fact in self.facts.values():
            if fact.observation_id != self.observation_id:
                raise ValueError("observation fact must reference its enclosing observation")
            if fact.source_record_digest != self.source_record_digest:
                raise ValueError("observation fact must preserve sourceRecordDigest")
        if self.state == ObservationState.FACTS_OBSERVED:
            if not self.facts:
                raise ValueError("facts-observed requires facts")
        else:
            if self.facts:
                raise ValueError("non-fact observation states forbid facts")
            if not self.diagnostics:
                raise ValueError("non-fact observation states require diagnostics")
        return self


class JudgementIngress(S04Model):
    request_id: SafeID = Field(alias="requestID")
    judgement_id: SafeID = Field(alias="judgementID")
    derivation_input_digest: Digest = Field(alias="derivationInputDigest")
    evaluator: EvaluatorIdentity
    realization_digest: Digest = Field(alias="realizationDigest")
    case_id: SafeID = Field(alias="caseID")
    semantic_authority_id: SafeID = Field(alias="semanticAuthorityID")
    package_digest: Digest = Field(alias="packageDigest")
    candidate_digest: Digest = Field(alias="candidateDigest")
    observation: ObservationRecord
    normalized_fact_set_id: SafeID = Field(alias="normalizedFactSetID")
    normalized_fact_set_digest: Digest = Field(alias="normalizedFactSetDigest")
    normalization_rule_set_digest: Digest = Field(alias="normalizationRuleSetDigest")
    comparison_rule_set_digest: Digest = Field(alias="comparisonRuleSetDigest")
    normalization_rule_ids: list[SafeID] = Field(alias="normalizationRuleIDs", min_length=1)
    comparison_rule_ids: list[SafeID] = Field(alias="comparisonRuleIDs", min_length=1)


class CueRealization(S04Model):
    schema_: Literal["s04.cue-realization.v0"] = Field(alias="schema")
    realization_id: SafeID = Field(alias="realizationID")
    title: NonEmptyString
    description: NonEmptyString | None = None
    authorities: dict[SafeID, AuthorityBinding]
    subjects: dict[SafeID, SubjectSpec]
    materializations: dict[SafeID, MaterializedSubjectIdentity]
    claims: dict[SafeID, SemanticClaim]
    expected_facts: dict[SafeID, ExpectedFact] = Field(alias="expectedFacts")
    normalization_rules: dict[SafeID, NormalizationRule] = Field(alias="normalizationRules")
    comparison_rules: dict[SafeID, ComparisonRule] = Field(alias="comparisonRules")
    capability_requirements: dict[SafeID, BackendCapabilityRequirement] = Field(alias="capabilityRequirements")
    plans: dict[SafeID, OperationPlan]
    cases: dict[SafeID, RealizationCase]

    @model_validator(mode="after")
    def map_keys_bind_object_ids(self) -> "CueRealization":
        for mapping, field_name, label in (
            (self.authorities, "authority_id", "authorities"),
            (self.subjects, "subject_id", "subjects"),
            (self.materializations, "materialization_id", "materializations"),
            (self.claims, "claim_id", "claims"),
            (self.expected_facts, "fact_id", "expectedFacts"),
            (self.normalization_rules, "rule_id", "normalizationRules"),
            (self.comparison_rules, "rule_id", "comparisonRules"),
            (self.capability_requirements, "capability_id", "capabilityRequirements"),
            (self.plans, "plan_id", "plans"),
            (self.cases, "case_id", "cases"),
        ):
            _keys_match_ids(mapping, field_name, label)
        for materialization in self.materializations.values():
            if materialization.realization_id != self.realization_id:
                raise ValueError("materialization realizationID must match realizationID")
        return self


class CueRealizationArtifact(S04Model):
    digest: Digest
    realization: CueRealization

class JudgementBundle(S04Model):
    realization: CueRealization
    ingress: JudgementIngress


def _validate_relative_path(value: str) -> str:
    if value.startswith("/") or ".." in value.split("/"):
        raise ValueError("path must remain relative and may not contain '..'")
    return value


def _keys_match_ids(mapping: dict[str, Any], field_name: str, label: str) -> None:
    for key, value in mapping.items():
        if getattr(value, field_name) != key:
            raise ValueError(f"{label} key {key!r} does not match {field_name}")
