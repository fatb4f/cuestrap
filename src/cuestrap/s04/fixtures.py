"""Deterministic valid S04 object graphs used as property-test seeds."""
from __future__ import annotations

from .models import (
    AuthorityBinding,
    AuthorityProjection,
    AuthorityRole,
    AuthoritySource,
    AuthoritySourceKind,
    BackendCapabilityRequirement,
    CaseProjectionBinding,
    ComparisonOperator,
    ComparisonRule,
    CueRealization,
    CueRealizationArtifact,
    EvaluatorIdentity,
    ExpectedFact,
    InlineSubjectSource,
    JudgementBundle,
    JudgementIngress,
    MinimalPPFPackage,
    NormalizationRule,
    ObservationFact,
    ObservationRecord,
    ObservationState,
    OperationPlan,
    OutcomeConstraint,
    PPFCandidate,
    PPFCase,
    PPFCaseGroup,
    PPFEvidenceRequirement,
    PPFExecutionLimits,
    PPFPackagePaths,
    PPFProblemMetadata,
    PPFValidator,
    PrimitiveOperationKind,
    ProjectionBundle,
    QualifiedContractBundle,
    RealizationCase,
    S04ConsumerProfileContract,
    S04PPFProjection,
    S04PPFProjectionRequest,
    SemanticClaim,
    SemanticOutcome,
    SubjectRef,
    SubjectSpec,
    SubsumesOperation,
)

DIGEST = "sha256:" + "a" * 64
CUE_REVISION = "806821e40fae070318600a264d311517e596353b"


def valid_judgement_bundle(prefix: str = "prop", *, observed_value: bool = True) -> JudgementBundle:
    ids = _ids(prefix)
    realization = CueRealization.model_validate(
        {
            "schema": "s04.cue-realization.v0",
            "realizationID": ids["realization"],
            "title": "Generated S04 property witness",
            "authorities": {
                ids["semantic"]: AuthorityBinding(
                    authorityID=ids["semantic"],
                    role=AuthorityRole.SEMANTIC,
                    source=AuthoritySource(
                        kind=AuthoritySourceKind.CUE_MODULE,
                        locator="pattern/s04",
                        revision="v0",
                        digest=DIGEST,
                    ),
                ),
                ids["declarer"]: AuthorityBinding(
                    authorityID=ids["declarer"],
                    role=AuthorityRole.PACKAGE_DECLARER,
                    source=AuthoritySource(
                        kind=AuthoritySourceKind.PROBLEM_PACKAGE,
                        locator="generated-package",
                        revision="v0",
                        digest=DIGEST,
                    ),
                ),
                ids["observer"]: AuthorityBinding(
                    authorityID=ids["observer"],
                    role=AuthorityRole.RAW_OBSERVER,
                    source=AuthoritySource(
                        kind=AuthoritySourceKind.PROCESS_RUNNER,
                        locator="generated-observer",
                        revision="v0",
                        digest=DIGEST,
                    ),
                ),
            },
            "subjects": {
                ids["left"]: SubjectSpec(
                    subjectID=ids["left"],
                    source=InlineSubjectSource(kind="inline", expression="int"),
                ),
                ids["right"]: SubjectSpec(
                    subjectID=ids["right"],
                    source=InlineSubjectSource(kind="inline", expression="1"),
                ),
            },
            "materializations": {},
            "claims": {
                ids["claim"]: SemanticClaim(
                    claimID=ids["claim"],
                    authorityID=ids["semantic"],
                    predicate=ids["predicate"],
                    operands=[SubjectRef(subjectID=ids["left"]), SubjectRef(subjectID=ids["right"])],
                    value=True,
                )
            },
            "expectedFacts": {
                ids["expected"]: ExpectedFact(
                    factID=ids["expected"],
                    claimID=ids["claim"],
                    authorityID=ids["semantic"],
                    predicate=ids["predicate"],
                    expectedValue=True,
                )
            },
            "normalizationRules": {
                ids["normalize"]: NormalizationRule(
                    ruleID=ids["normalize"],
                    observationFactID=ids["raw"],
                    normalizedFactID=ids["normalized"],
                    normalizedPredicate=ids["predicate"],
                )
            },
            "comparisonRules": {
                ids["compare"]: ComparisonRule(
                    ruleID=ids["compare"],
                    expectedFactID=ids["expected"],
                    normalizedFactID=ids["normalized"],
                    operator=ComparisonOperator.EQUALS,
                    resultPredicate=ids["matches"],
                )
            },
            "capabilityRequirements": {
                ids["capability"]: BackendCapabilityRequirement(
                    capabilityID=ids["capability"],
                    operationKinds=[PrimitiveOperationKind.SUBSUMES],
                )
            },
            "plans": {
                ids["plan"]: OperationPlan(
                    planID=ids["plan"],
                    operations=[
                        SubsumesOperation(
                            operationID=ids["operation"],
                            kind="subsumes",
                            left=SubjectRef(subjectID=ids["left"]),
                            right=SubjectRef(subjectID=ids["right"]),
                            direction="left-to-right",
                            produces=[ids["raw"]],
                        )
                    ],
                )
            },
            "cases": {
                ids["case"]: RealizationCase(
                    caseID=ids["case"],
                    groupID=ids["group"],
                    planID=ids["plan"],
                    subjectIDs=[ids["left"], ids["right"]],
                    expectedFactIDs=[ids["expected"]],
                    normalizationRuleIDs=[ids["normalize"]],
                    comparisonRuleIDs=[ids["compare"]],
                    requiredCapabilityIDs=[ids["capability"]],
                    outcomeConstraint=OutcomeConstraint(
                        permitted=[
                            SemanticOutcome.SATISFIED,
                            SemanticOutcome.REJECTED,
                            SemanticOutcome.INDETERMINATE,
                        ]
                    ),
                )
            },
        }
    )
    observation_id = ids["observation"]
    observation = ObservationRecord.model_validate(
        {
            "schema": "s04.observation-record.v0",
            "observationID": observation_id,
            "caseID": ids["case"],
            "observerAuthorityID": ids["observer"],
            "sourceRecordDigest": DIGEST,
            "state": "facts-observed",
            "facts": {
                ids["raw"]: ObservationFact(
                    factID=ids["raw"],
                    observationID=observation_id,
                    predicate=ids["predicate"],
                    observedValue=observed_value,
                    sourceRecordDigest=DIGEST,
                )
            },
        }
    )
    ingress = JudgementIngress.model_validate(
        {
            "requestID": ids["request"],
            "judgementID": ids["judgement"],
            "derivationInputDigest": DIGEST,
            "evaluator": EvaluatorIdentity(
                cueRevision=CUE_REVISION,
                languageVersion="v0.18.0",
                relationID="s04.derive-semantic-judgement.v0",
                facadeDigest=DIGEST,
            ),
            "realizationDigest": DIGEST,
            "caseID": ids["case"],
            "semanticAuthorityID": ids["semantic"],
            "packageDigest": DIGEST,
            "candidateDigest": DIGEST,
            "observation": observation,
            "normalizedFactSetID": ids["factset"],
            "normalizedFactSetDigest": DIGEST,
            "normalizationRuleSetDigest": DIGEST,
            "comparisonRuleSetDigest": DIGEST,
            "normalizationRuleIDs": [ids["normalize"]],
            "comparisonRuleIDs": [ids["compare"]],
        }
    )
    return JudgementBundle(realization=realization, ingress=ingress)


def valid_projection_bundle(prefix: str = "prop") -> ProjectionBundle:
    judgement = valid_judgement_bundle(prefix)
    ids = _ids(prefix)
    package = MinimalPPFPackage.model_validate(
        {
            "schema": "s04.minimal-ppf-package.v0",
            "profileID": "s04.kattis-ppf-minimal.v0",
            "sourceSpecVersion": "2025-09",
            "conformance": "profile-only",
            "packageID": ids["package"],
            "packageDirectory": f"{prefix.replace('-', '')}package",
            "packageDigest": DIGEST,
            "metadata": PPFProblemMetadata(
                problem_format_version="2025-09",
                name="Generated package",
                uuid="11111111-1111-4111-8111-111111111111",
                limits=PPFExecutionLimits(
                    time_limit=1,
                    memory=64,
                    output=64,
                    validation_time=1,
                    validation_memory=64,
                    validation_output=64,
                ),
            ),
            "paths": PPFPackagePaths(
                statement="problem_statement/problem.en.tex",
                judgeEntrypoint="output_validators/judge",
                rawObservationRoot="evidence/raw",
                normalizedFactRoot="evidence/normalized",
                comparisonRoot="evidence/comparison",
                judgementRoot="evidence/judgement",
            ),
            "validator": PPFValidator(
                validatorID=ids["validator"],
                entrypoint="output_validators/judge",
                semanticAuthorityID=ids["semantic"],
                observationInputRoot="evidence/raw",
                judgementOutputRoot="evidence/judgement",
            ),
            "groups": {
                ids["group"]: PPFCaseGroup(groupID=ids["group"], caseIDs=[ids["package_case"]])
            },
            "cases": {
                ids["package_case"]: PPFCase(
                    caseID=ids["package_case"],
                    groupID=ids["group"],
                    inputPath="data/secret/case.in",
                    answerPath="data/secret/case.ans",
                    evidencePath="evidence/cases/case",
                )
            },
            "candidates": {
                ids["candidate"]: PPFCandidate(
                    candidateID=ids["candidate"],
                    sourcePath="submissions/accepted/main.cue",
                    expectation="accepted",
                    evidencePath="evidence/candidates/candidate",
                )
            },
            "evidenceRequirements": {
                ids["evidence"]: PPFEvidenceRequirement(
                    evidenceID=ids["evidence"],
                    kind="semantic-judgement",
                    path="evidence/judgement",
                )
            },
        }
    )
    request = S04PPFProjectionRequest(
        projectionID=ids["projection"],
        projectionDigest=DIGEST,
        semanticAuthorityID=ids["semantic"],
        packageDeclarerAuthorityID=ids["declarer"],
        rawObserverAuthorityIDs=[ids["observer"]],
        caseMap={ids["case"]: ids["package_case"]},
    )
    return ProjectionBundle(
        realizationArtifact=CueRealizationArtifact(digest=DIGEST, realization=judgement.realization),
        package=package,
        request=request,
    )


def valid_qualified_contract_bundle(prefix: str = "prop") -> QualifiedContractBundle:
    projection_bundle = valid_projection_bundle(prefix)
    ids = _ids(prefix)
    realization = projection_bundle.realization_artifact.realization
    projection = S04PPFProjection(
        schema="s04.ppf-projection.v0",
        projectionID=ids["projection"],
        projectionDigest=DIGEST,
        realizationID=ids["realization"],
        realizationDigest=DIGEST,
        packageID=ids["package"],
        packageDigest=DIGEST,
        authorities=AuthorityProjection(
            semanticAuthorityID=ids["semantic"],
            packageDeclarerAuthorityID=ids["declarer"],
            rawObserverAuthorityIDs=[ids["observer"]],
        ),
        caseBindings={
            ids["case"]: CaseProjectionBinding(
                bindingID=ids["case"],
                realizationCaseID=ids["case"],
                packageCaseID=ids["package_case"],
            )
        },
    )
    contract = S04ConsumerProfileContract(
        schema="s04.consumer-profile-contract.v0",
        contractID=ids["contract"],
        contractDigest=DIGEST,
        realization=realization,
        package=projection_bundle.package,
        projection=projection,
    )
    return QualifiedContractBundle(
        candidateContract=contract,
        realizationArtifact=projection_bundle.realization_artifact,
        projectionRequest=projection_bundle.request,
    )


def _ids(prefix: str) -> dict[str, str]:
    return {
        "realization": f"{prefix}-realization",
        "semantic": f"{prefix}-semantic",
        "declarer": f"{prefix}-declarer",
        "observer": f"{prefix}-observer",
        "left": f"{prefix}-left",
        "right": f"{prefix}-right",
        "claim": f"{prefix}-claim",
        "predicate": f"{prefix}-subsumes",
        "expected": f"{prefix}-expected",
        "raw": f"{prefix}-raw",
        "normalized": f"{prefix}-normalized",
        "normalize": f"{prefix}-normalize",
        "compare": f"{prefix}-compare",
        "matches": f"{prefix}-matches",
        "capability": f"{prefix}-capability",
        "plan": f"{prefix}-plan",
        "operation": f"{prefix}-operation",
        "case": f"{prefix}-case",
        "group": f"{prefix}-group",
        "observation": f"{prefix}-observation",
        "request": f"{prefix}-request",
        "judgement": f"{prefix}-judgement",
        "factset": f"{prefix}-factset",
        "package": f"{prefix}-package",
        "package_case": f"{prefix}-package-case",
        "candidate": f"{prefix}-candidate",
        "validator": f"{prefix}-validator",
        "evidence": f"{prefix}-evidence",
        "projection": f"{prefix}-projection",
        "contract": f"{prefix}-contract",
    }
