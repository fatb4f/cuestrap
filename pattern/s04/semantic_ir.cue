package s04

// S04 v0 semantic realization intermediate representation.
//
// This package defines semantic contracts only. Runners and transports emit raw
// observations; they do not author semantic satisfaction or rejection.

#NonEmptyString: string & !=""
#SafeID: #NonEmptyString & =~"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
#Digest: #NonEmptyString & =~"^sha256:[0-9a-f]{64}$"
#RelativePath: #NonEmptyString & !~"^/" & !~"(^|/)\\.\\.(/|$)"
#FactValue: bool | number | string

#AuthorityRole:
	"semantic-authority" |
	"package-declarer" |
	"raw-observer"

#AuthoritySourceKind:
	"cue-module" |
	"problem-package" |
	"native-runner" |
	"process-runner"

#AuthorityBinding: close({
	authorityID: #SafeID
	role:        #AuthorityRole
	source: close({
		kind:     #AuthoritySourceKind
		locator:  #NonEmptyString
		revision: #NonEmptyString
		digest:   #Digest
	})
})

#SubjectSource: close({
	kind:       "inline"
	expression: #NonEmptyString
}) | close({
	kind:   "path"
	path:   #RelativePath
	digest: #Digest
})

#SubjectSpec: close({
	subjectID: #SafeID
	language:  "cue"
	source:    #SubjectSource
	mediaType: "application/cue"
})

#FileIdentity: close({
	path:   #RelativePath
	digest: #Digest
})

#MaterializedSubjectIdentity: close({
	materializationID:    #SafeID
	realizationID:       #SafeID
	subjectID:           #SafeID
	materializationDigest: #Digest
	files: [FileID=#SafeID]: #FileIdentity & {
		path: #RelativePath
	}
})

#SubjectRef: close({
	subjectID:       #SafeID
	materializationID?: #SafeID
})

#PrimitiveOperationKind:
	"unify" |
	"subsumes" |
	"validate"

#OperationDirection:
	"symmetric" |
	"left-to-right" |
	"right-to-left" |
	"subject-only"

#PrimitiveOperation: close({
	operationID: #SafeID
	kind:        #PrimitiveOperationKind
	left:        #SubjectRef
	right?:      #SubjectRef
	direction:   #OperationDirection
	produces:    [#SafeID, ...#SafeID]

	if kind == "unify" {
		right:     #SubjectRef
		direction: "symmetric"
	}
	if kind == "subsumes" {
		right:     #SubjectRef
		direction: "left-to-right" | "right-to-left"
	}
	if kind == "validate" {
		direction: "subject-only"
	}
})

#OperationPlan: close({
	planID:     #SafeID
	operations: [#PrimitiveOperation, ...#PrimitiveOperation]
})

#SemanticClaim: close({
	claimID:     #SafeID
	authorityID: #SafeID
	predicate:   #SafeID
	operands:    [#SubjectRef, ...#SubjectRef]
	value:       #FactValue
})

#ExpectedFact: close({
	factID:      #SafeID
	claimID:     #SafeID
	authorityID: #SafeID
	predicate:   #SafeID
	expectedValue: #FactValue
})

#ObservationFact: close({
	factID:             #SafeID
	observationID:      #SafeID
	predicate:          #SafeID
	observedValue:      #FactValue
	sourceRecordDigest: #Digest
})

#ComparisonOperator:
	"equals" |
	"not-equals"

#ComparisonRule: close({
	ruleID:            #SafeID
	expectedFactID:    #SafeID
	observationFactID: #SafeID
	operator:          #ComparisonOperator
	resultPredicate:   #SafeID
})

#BackendCapabilityRequirement: close({
	capabilityID: #SafeID
	operationKinds: [#PrimitiveOperationKind, ...#PrimitiveOperationKind]
	required: true
})

#SemanticOutcome:
	"satisfied" |
	"rejected" |
	"indeterminate"

#OutcomeConstraint: close({
	permitted: [#SemanticOutcome, ...#SemanticOutcome]
	required?: #SemanticOutcome
})

#RealizationCase: close({
	caseID:                  #SafeID
	groupID:                 #SafeID
	planID:                  #SafeID
	subjectIDs:              [#SafeID, ...#SafeID]
	expectedFactIDs:         [#SafeID, ...#SafeID]
	comparisonRuleIDs:       [#SafeID, ...#SafeID]
	requiredCapabilityIDs:   [#SafeID, ...#SafeID]
	outcomeConstraint:       #OutcomeConstraint
})

#Diagnostic: close({
	code:    #SafeID
	message: #NonEmptyString
	path?:   #RelativePath
})

#ObservationState:
	"facts-observed" |
	"transport-failure" |
	"capability-absent" |
	"invalid-observation"

#ObservationRecord: close({
	schema:       "s04.observation-record.v0"
	observationID: #SafeID
	caseID:       #SafeID
	observerAuthorityID: #SafeID
	sourceRecordDigest:   #Digest
	state:        #ObservationState
	facts:        [FactID=#SafeID]: #ObservationFact & {factID: FactID}
	diagnostics?: [#Diagnostic, ...#Diagnostic]

	if state != "facts-observed" {
		facts: close({})
		diagnostics: [#Diagnostic, ...#Diagnostic]
	}
})

#ComparisonResult: close({
	ruleID:  #SafeID
	matched: bool
})

#SemanticJudgement: close({
	schema:       "s04.semantic-judgement.v0"
	judgementID:  #SafeID
	realizationID: #SafeID
	caseID:       #SafeID
	semanticAuthorityID: #SafeID
	packageDigest:        #Digest
	candidateDigest:      #Digest
	observationDigest:    #Digest
	comparisonResults: [RuleID=#SafeID]: #ComparisonResult & {ruleID: RuleID}
	outcome: #SemanticOutcome
	diagnostics?: [#Diagnostic, ...#Diagnostic]
})

#CueRealization: close({
	schema:        "s04.cue-realization.v0"
	realizationID: #SafeID
	title:         #NonEmptyString
	description?:  #NonEmptyString

	authorities: [AuthorityID=#SafeID]: #AuthorityBinding & {
		authorityID: AuthorityID
	}
	subjects: [SubjectID=#SafeID]: #SubjectSpec & {
		subjectID: SubjectID
	}
	claims: [ClaimID=#SafeID]: #SemanticClaim & {
		claimID: ClaimID
	}
	expectedFacts: [FactID=#SafeID]: #ExpectedFact & {
		factID: FactID
	}
	comparisonRules: [RuleID=#SafeID]: #ComparisonRule & {
		ruleID: RuleID
	}
	capabilityRequirements: [CapabilityID=#SafeID]: #BackendCapabilityRequirement & {
		capabilityID: CapabilityID
	}
	plans: [PlanID=#SafeID]: #OperationPlan & {
		planID: PlanID
	}
	cases: [CaseID=#SafeID]: #RealizationCase & {
		caseID: CaseID
	}
})
