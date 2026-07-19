"""Typed PPF projection and contract construction objects."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from .core import CueRealization, CueRealizationArtifact, Digest, NonEmptyString, RelativePath, S04Model, SafeID, _keys_match_ids

class PPFExecutionLimits(S04Model):
    time_limit: float = Field(alias="time_limit", gt=0)
    memory: int = Field(gt=0)
    output: int = Field(gt=0)
    validation_time: float = Field(alias="validation_time", gt=0)
    validation_memory: int = Field(alias="validation_memory", gt=0)
    validation_output: int = Field(alias="validation_output", gt=0)


class PPFProblemMetadata(S04Model):
    problem_format_version: Literal["2025-09"] = Field(alias="problem_format_version")
    type: Literal["pass-fail"] = "pass-fail"
    name: NonEmptyString
    uuid: NonEmptyString
    limits: PPFExecutionLimits


class PPFPackagePaths(S04Model):
    problem_config: Literal["problem.yaml"] = Field(alias="problemConfig", default="problem.yaml")
    statement: RelativePath
    secret_data_root: Literal["data/secret"] = Field(alias="secretDataRoot", default="data/secret")
    submissions_root: Literal["submissions"] = Field(alias="submissionsRoot", default="submissions")
    input_validators_root: Literal["input_validators"] = Field(alias="inputValidatorsRoot", default="input_validators")
    judge_entrypoint: RelativePath = Field(alias="judgeEntrypoint")
    raw_observation_root: RelativePath = Field(alias="rawObservationRoot")
    normalized_fact_root: RelativePath = Field(alias="normalizedFactRoot")
    comparison_root: RelativePath = Field(alias="comparisonRoot")
    judgement_root: RelativePath = Field(alias="judgementRoot")


class PPFCaseGroup(S04Model):
    group_id: SafeID = Field(alias="groupID")
    case_ids: list[SafeID] = Field(alias="caseIDs", min_length=1)


class PPFCase(S04Model):
    case_id: SafeID = Field(alias="caseID")
    group_id: SafeID = Field(alias="groupID")
    input_path: RelativePath = Field(alias="inputPath")
    answer_path: RelativePath = Field(alias="answerPath")
    evidence_path: RelativePath = Field(alias="evidencePath")


class PPFCandidate(S04Model):
    candidate_id: SafeID = Field(alias="candidateID")
    source_path: RelativePath = Field(alias="sourcePath")
    expectation: Literal["accepted", "rejected"]
    evidence_path: RelativePath = Field(alias="evidencePath")


class PPFValidator(S04Model):
    validator_id: SafeID = Field(alias="validatorID")
    kind: Literal["s04-independent-judge"] = "s04-independent-judge"
    entrypoint: RelativePath
    semantic_authority_id: SafeID = Field(alias="semanticAuthorityID")
    observation_input_root: RelativePath = Field(alias="observationInputRoot")
    judgement_output_root: RelativePath = Field(alias="judgementOutputRoot")


class PPFEvidenceRequirement(S04Model):
    evidence_id: SafeID = Field(alias="evidenceID")
    kind: Literal[
        "package-identity",
        "candidate-identity",
        "raw-observation",
        "normalized-fact",
        "comparison-result",
        "semantic-judgement",
    ]
    path: RelativePath
    durable: Literal[True] = True


class MinimalPPFPackage(S04Model):
    schema_: Literal["s04.minimal-ppf-package.v0"] = Field(alias="schema")
    profile_id: Literal["s04.kattis-ppf-minimal.v0"] = Field(alias="profileID")
    source_spec_version: Literal["2025-09"] = Field(alias="sourceSpecVersion")
    conformance: Literal["profile-only"] = "profile-only"
    package_id: SafeID = Field(alias="packageID")
    package_directory: Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+$")] = Field(alias="packageDirectory")
    package_digest: Digest = Field(alias="packageDigest")
    metadata: PPFProblemMetadata
    paths: PPFPackagePaths
    validator: PPFValidator
    groups: dict[SafeID, PPFCaseGroup]
    cases: dict[SafeID, PPFCase]
    candidates: dict[SafeID, PPFCandidate]
    evidence_requirements: dict[SafeID, PPFEvidenceRequirement] = Field(alias="evidenceRequirements")

    @model_validator(mode="after")
    def bind_maps_and_paths(self) -> "MinimalPPFPackage":
        _keys_match_ids(self.groups, "group_id", "groups")
        _keys_match_ids(self.cases, "case_id", "cases")
        _keys_match_ids(self.candidates, "candidate_id", "candidates")
        _keys_match_ids(self.evidence_requirements, "evidence_id", "evidenceRequirements")
        if self.validator.entrypoint != self.paths.judge_entrypoint:
            raise ValueError("validator entrypoint must match package paths")
        if self.validator.observation_input_root != self.paths.raw_observation_root:
            raise ValueError("validator observation root must match package paths")
        if self.validator.judgement_output_root != self.paths.judgement_root:
            raise ValueError("validator judgement root must match package paths")
        return self


class S04PPFProjectionRequest(S04Model):
    projection_id: SafeID = Field(alias="projectionID")
    projection_digest: Digest = Field(alias="projectionDigest")
    semantic_authority_id: SafeID = Field(alias="semanticAuthorityID")
    package_declarer_authority_id: SafeID = Field(alias="packageDeclarerAuthorityID")
    raw_observer_authority_ids: list[SafeID] = Field(alias="rawObserverAuthorityIDs", min_length=1)
    case_map: dict[SafeID, SafeID] = Field(alias="caseMap")


class CaseProjectionBinding(S04Model):
    binding_id: SafeID = Field(alias="bindingID")
    realization_case_id: SafeID = Field(alias="realizationCaseID")
    package_case_id: SafeID = Field(alias="packageCaseID")


class AuthorityProjection(S04Model):
    semantic_authority_id: SafeID = Field(alias="semanticAuthorityID")
    package_declarer_authority_id: SafeID = Field(alias="packageDeclarerAuthorityID")
    raw_observer_authority_ids: list[SafeID] = Field(alias="rawObserverAuthorityIDs", min_length=1)


class S04PPFProjection(S04Model):
    schema_: Literal["s04.ppf-projection.v0"] = Field(alias="schema")
    projection_id: SafeID = Field(alias="projectionID")
    projection_digest: Digest = Field(alias="projectionDigest")
    realization_id: SafeID = Field(alias="realizationID")
    realization_digest: Digest = Field(alias="realizationDigest")
    package_id: SafeID = Field(alias="packageID")
    package_digest: Digest = Field(alias="packageDigest")
    authorities: AuthorityProjection
    case_bindings: dict[SafeID, CaseProjectionBinding] = Field(alias="caseBindings")
    judgement_vocabulary: Literal["s04.semantic-outcome.v0"] = Field(
        alias="judgementVocabulary", default="s04.semantic-outcome.v0"
    )

    @model_validator(mode="after")
    def bind_case_map_keys(self) -> "S04PPFProjection":
        _keys_match_ids(self.case_bindings, "binding_id", "caseBindings")
        return self


class S04ConsumerProfileContract(S04Model):
    schema_: Literal["s04.consumer-profile-contract.v0"] = Field(alias="schema")
    contract_id: SafeID = Field(alias="contractID")
    contract_digest: Digest = Field(alias="contractDigest")
    realization: CueRealization
    package: MinimalPPFPackage
    projection: S04PPFProjection


class ProjectionBundle(S04Model):
    realization_artifact: CueRealizationArtifact = Field(alias="realizationArtifact")
    package: MinimalPPFPackage
    request: S04PPFProjectionRequest


class QualifiedContractBundle(S04Model):
    candidate_contract: S04ConsumerProfileContract = Field(alias="candidateContract")
    realization_artifact: CueRealizationArtifact = Field(alias="realizationArtifact")
    projection_request: S04PPFProjectionRequest = Field(alias="projectionRequest")
