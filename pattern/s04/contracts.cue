package s04

#NonEmptyString: string & !=""
#Digest:         string & =~"^sha256:[0-9a-f]{64}$"

#PackageVerdict:
	"accepted" |
	"rejected" |
	"indeterminate" |
	"infrastructureFailure" |
	"unsupported" |
	"invalidPackage"

#SemanticDisposition:
	"satisfied" |
	"violated" |
	"indeterminate"

#FactKind:
	"orderingHolds" |
	"orderingDoesNotHold" |
	"unificationSucceeded" |
	"structurePreserved" |
	"backendCapabilityPresent" |
	"backendCapabilityAbsent" |
	"runnerFailure" |
	"invalidObservation"

#AuthorityBinding: close({
	id:   #NonEmptyString
	role: "semanticAuthority" | "fixtureAuthority" | "executionAuthority"
	reference: close({
		kind: "cuePackage" | "cueFile" | "packageArtifact"
		path: #NonEmptyString
	})
	digest?: #Digest
})

#MaterializedSubjectIdentity: close({
	subjectID:   #NonEmptyString
	packageID:   #NonEmptyString
	candidateID: #NonEmptyString
	digest:      #Digest
	sourceDigests: [#NonEmptyString]: #Digest
})

#SubjectSpec: close({
	id:        #NonEmptyString
	kind:      "cueValue" | "cueSchema" | "cueExpression"
	structure: _
	identity?: #MaterializedSubjectIdentity
})

#Operand: close({
	role: "subject" | "candidate" | "left" | "right" | "instance" | "constraint"
	ref:  #NonEmptyString
})

#PrimitiveOperation: close({
	kind:     "evaluate" | "unify" | "subsumes" | "export" | "validate"
	operands: [#Operand, ...#Operand]
})

#BackendCapabilityRequirement: close({
	capability: #NonEmptyString
	level:      "required" | "optional"
	absenceMeans: "unsupported" | "indeterminate"
})

#OperationPlan: close({
	id:        #NonEmptyString
	operation: #PrimitiveOperation
	requires:  [...#BackendCapabilityRequirement]
	produces:  [#FactKind, ...#FactKind]
})

#ExpectedFact: close({
	source: "package"
	id:     #NonEmptyString
	kind:   #FactKind
	value:  bool
})

#ObservationProvenance: close({
	adapter:                  #NonEmptyString
	backend:                  #NonEmptyString
	operationPlanID:          #NonEmptyString
	subjectDigest:            #Digest
	rawObservationDigests:    [#Digest, ...#Digest]
	backendComparisonDigest?: #Digest
})

#ObservationFact: close({
	source: "observation"
	id:     #NonEmptyString
	caseID: #NonEmptyString
	kind:   #FactKind
	status: "observed" | "unavailable" | "indeterminate"
	value?: bool
	provenance: #ObservationProvenance
})

#ComparisonRule: close({
	mode: "allExpectedObserved"
})

#SemanticClaim: close({
	id:       #NonEmptyString
	kind:     "orders" | "doesNotOrder" | "unifies" | "preservesStructure" | "rejectsSemantically"
	expected: [#ExpectedFact, ...#ExpectedFact]
	compare:  #ComparisonRule
})

#RealizationCase: close({
	id:        #NonEmptyString
	polarity:  "accepted" | "rejected"
	subject:   #SubjectSpec
	operation: #OperationPlan
	claim:     #SemanticClaim
})

#CueRealization: close({
	id:          #NonEmptyString
	family:      #NonEmptyString
	description: string
	cases:       [#NonEmptyString]: #RealizationCase
})

#CandidateMaterialization: close({
	moduleRoot:          #NonEmptyString
	package:             #NonEmptyString
	files:               [close({path: #NonEmptyString}), ...close({path: #NonEmptyString})]
	subjectExpression:   #NonEmptyString
	candidateExpression: #NonEmptyString
})

#CandidateFixture: close({
	id:              #NonEmptyString
	caseID:          #NonEmptyString
	polarity:        "accepted" | "rejected"
	requiredVerdict: #PackageVerdict
	materialization: #CandidateMaterialization
})

#ExecutionLimits: close({
	maximumExecutions: uint & >=1 & <=16
	timeoutSeconds:    uint & >=1 & <=600
	maximumOutputBytes: uint & >=1 & <=1048576
	network: "forbidden" | "permitted"
})

#EvidenceRequirement: close({
	kind: "packageSnapshot" | "rawObservations" | "normalizedFacts" | "comparisonTrace" | "judgement" | "manifest"
	durable: true
	minimum: uint & >=1
})

#JudgeEntrypoint: close({
	moduleRoot: #NonEmptyString
	package:    #NonEmptyString
	files:      [close({path: #NonEmptyString}), ...close({path: #NonEmptyString})]
	expression: "#PackageJudgement"
})

#ProblemPackage: close({
	profile: "s04-kattis-ppf-v0"
	metadata: close({
		id:      #NonEmptyString
		title:   #NonEmptyString
		version: #NonEmptyString
		family:  "LT-01"
	})
	authorities: [#NonEmptyString]: #AuthorityBinding
	authorization: close({
		permittedBackends:       [#NonEmptyString, ...#NonEmptyString]
		permittedAdapters:       [#NonEmptyString, ...#NonEmptyString]
		requireAuthorityDigest:  bool
		requireCandidateIdentity: bool
	})
	realization:  #CueRealization
	capabilities: [#BackendCapabilityRequirement, ...#BackendCapabilityRequirement]
	candidates:   [#NonEmptyString]: #CandidateFixture
	limits:       #ExecutionLimits
	evidence:     [#EvidenceRequirement, ...#EvidenceRequirement]
	judge:        #JudgeEntrypoint
	verdictPolicy: close({
		permitted: [#PackageVerdict, ...#PackageVerdict]
	})
})

#JudgementRequest: close({
	package:      #ProblemPackage
	packageDigest: #Digest
	candidateID:  #NonEmptyString
	observations: [...#ObservationFact]
})

#ComparisonStep: close({
	expectedFactID:  #NonEmptyString
	observedFactID?: #NonEmptyString
	result:           "matched" | "missing"
})

#PackageJudgement: {
	request: #JudgementRequest

	_candidate: request.package.candidates[request.candidateID]
	_case:      request.package.realization.cases[_candidate.caseID]

	_caseObservations: [for observation in request.observations if observation.caseID == _case.id {observation}]
	_runnerFailures: [for observation in _caseObservations if observation.kind == "runnerFailure" {observation}]
	_invalidObservations: [for observation in _caseObservations if observation.kind == "invalidObservation" {observation}]
	_capabilityGaps: [for observation in _caseObservations if observation.kind == "backendCapabilityAbsent" {observation}]

	_matches: [
		for expected in _case.claim.expected
		for observation in _caseObservations
		if observation.status == "observed"
		if observation.kind == expected.kind
		if observation.value == expected.value {
			expectedFactID: expected.id
			observedFactID: observation.id
			result:         "matched"
		}
	]

	_missing: [
		for expected in _case.claim.expected
		if len([
			for observation in _caseObservations
			if observation.status == "observed"
			if observation.kind == expected.kind
			if observation.value == expected.value {true}
		]) == 0 {
			expectedFactID: expected.id
			result:         "missing"
		}
	]

	_permittedRequiredVerdict: [
		for verdict in request.package.verdictPolicy.permitted
		if verdict == _candidate.requiredVerdict {verdict}
	]

	judgement: close({
		schema:        "s04.package-judgement.v0"
		packageID:     request.package.metadata.id
		packageDigest: request.packageDigest
		candidateID:   _candidate.id
		caseID:        _case.id
		comparisonTrace: [for step in _matches {step}] + [for step in _missing {step}]
		evidenceFactIDs: [for observation in _caseObservations {observation.id}]

		if len(_permittedRequiredVerdict) == 0 {
			semanticDisposition: "indeterminate"
			packageVerdict:      "invalidPackage"
			verdictConstraintSatisfied: false
		}
		if len(_permittedRequiredVerdict) == 1 && len(_runnerFailures) > 0 {
			semanticDisposition: "indeterminate"
			packageVerdict:      "infrastructureFailure"
			verdictConstraintSatisfied: false
		}
		if len(_permittedRequiredVerdict) == 1 && len(_runnerFailures) == 0 && len(_invalidObservations) > 0 {
			semanticDisposition: "indeterminate"
			packageVerdict:      "indeterminate"
			verdictConstraintSatisfied: false
		}
		if len(_permittedRequiredVerdict) == 1 && len(_runnerFailures) == 0 && len(_invalidObservations) == 0 && len(_capabilityGaps) > 0 {
			semanticDisposition: "indeterminate"
			packageVerdict:      "unsupported"
			verdictConstraintSatisfied: false
		}
		if len(_permittedRequiredVerdict) == 1 && len(_runnerFailures) == 0 && len(_invalidObservations) == 0 && len(_capabilityGaps) == 0 && len(_caseObservations) == 0 {
			semanticDisposition: "indeterminate"
			packageVerdict:      "indeterminate"
			verdictConstraintSatisfied: false
		}
		if len(_permittedRequiredVerdict) == 1 && len(_runnerFailures) == 0 && len(_invalidObservations) == 0 && len(_capabilityGaps) == 0 && len(_caseObservations) > 0 && len(_matches) == len(_case.claim.expected) {
			semanticDisposition: "satisfied"
			packageVerdict:      _candidate.requiredVerdict
			verdictConstraintSatisfied: true
		}
		if len(_permittedRequiredVerdict) == 1 && len(_runnerFailures) == 0 && len(_invalidObservations) == 0 && len(_capabilityGaps) == 0 && len(_caseObservations) > 0 && len(_matches) < len(_case.claim.expected) {
			semanticDisposition: "violated"
			packageVerdict:      "indeterminate"
			verdictConstraintSatisfied: false
		}
	})
}
