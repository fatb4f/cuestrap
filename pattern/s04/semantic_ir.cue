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

#EvaluatorIdentity: close({
	cueRevision:     "806821e40fae070318600a264d311517e596353b"
	languageVersion: "v0.18.0"
	relationID:      "s04.derive-semantic-judgement.v0"
	facadeDigest:    #Digest
})

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
	materializationID:     #SafeID
	realizationID:         #SafeID
	subjectID:             #SafeID
	materializationDigest: #Digest
	files: [FileID=#SafeID]: #FileIdentity & {
		path: #RelativePath
	}
})

#SubjectRef: close({
	subjectID:         #SafeID
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

#PrimitiveOperation:
	close({
		operationID: #SafeID
		kind:        "unify"
		left:        #SubjectRef
		right:       #SubjectRef
		direction:   "symmetric"
		produces:    [#SafeID, ...#SafeID]
	}) |
	close({
		operationID: #SafeID
		kind:        "subsumes"
		left:        #SubjectRef
		right:       #SubjectRef
		direction:   "left-to-right" | "right-to-left"
		produces:    [#SafeID, ...#SafeID]
	}) |
	close({
		operationID: #SafeID
		kind:        "validate"
		left:        #SubjectRef
		direction:   "subject-only"
		produces:    [#SafeID, ...#SafeID]
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
	factID:        #SafeID
	claimID:       #SafeID
	authorityID:   #SafeID
	predicate:     #SafeID
	expectedValue: #FactValue
})

#ObservationFact: close({
	factID:             #SafeID
	observationID:      #SafeID
	predicate:          #SafeID
	observedValue:      #FactValue
	sourceRecordDigest: #Digest
})

#NormalizationRule: close({
	ruleID:              #SafeID
	observationFactID:   #SafeID
	normalizedFactID:    #SafeID
	normalizedPredicate: #SafeID
})

#NormalizedFact: close({
	factID:                  #SafeID
	normalizationRuleID:     #SafeID
	observationFactID:       #SafeID
	predicate:               #SafeID
	value:                   #FactValue
	sourceObservationDigest: #Digest
})

#NormalizedFactSet: close({
	schema:                     "s04.normalized-fact-set.v0"
	factSetID:                  #SafeID
	factSetDigest:              #Digest
	normalizationRuleSetDigest: #Digest
	sourceObservationDigest:    #Digest
	facts: [FactID=#SafeID]: #NormalizedFact & {
		factID: FactID
	}
})

#ComparisonOperator:
	"equals" |
	"not-equals"

#ComparisonRule: close({
	ruleID:           #SafeID
	expectedFactID:   #SafeID
	normalizedFactID: #SafeID
	operator:         #ComparisonOperator
	resultPredicate:  #SafeID
})

#BackendCapabilityRequirement: close({
	capabilityID:  #SafeID
	operationKinds: [#PrimitiveOperationKind, ...#PrimitiveOperationKind]
	required:      true
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
	caseID:                #SafeID
	groupID:               #SafeID
	planID:                #SafeID
	subjectIDs:            [#SafeID, ...#SafeID]
	expectedFactIDs:       [#SafeID, ...#SafeID]
	normalizationRuleIDs:  [#SafeID, ...#SafeID]
	comparisonRuleIDs:     [#SafeID, ...#SafeID]
	requiredCapabilityIDs: [#SafeID, ...#SafeID]
	outcomeConstraint:     #OutcomeConstraint
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
	schema:              "s04.observation-record.v0"
	observationID:       #SafeID
	caseID:              #SafeID
	observerAuthorityID: #SafeID
	sourceRecordDigest:  #Digest
	state:               #ObservationState
	facts:               [FactID=#SafeID]: #ObservationFact & {factID: FactID}
	diagnostics?:        [#Diagnostic, ...#Diagnostic]

	if state != "facts-observed" {
		facts:       close({})
		diagnostics: [#Diagnostic, ...#Diagnostic]
	}
})

#ComparisonResult: close({
	ruleID:           #SafeID
	expectedFactID:   #SafeID
	normalizedFactID: #SafeID
	expectedValue:    #FactValue
	observedValue:    #FactValue
	matched:          bool
})

#SemanticJudgement: close({
	schema:                  "s04.semantic-judgement.v0"
	derivationRelation:      "s04.derive-semantic-judgement.v0"
	judgementID:             #SafeID
	derivationInputDigest:   #Digest
	evaluator:               #EvaluatorIdentity
	realizationID:           #SafeID
	realizationDigest:       #Digest
	caseID:                  #SafeID
	semanticAuthorityID:     #SafeID
	packageDigest:           #Digest
	candidateDigest:         #Digest
	observationDigest:       #Digest
	normalizedFactSet:       #NormalizedFactSet
	comparisonRuleSetDigest: #Digest
	comparisonResults:       [RuleID=#SafeID]: #ComparisonResult & {ruleID: RuleID}
	outcome:                 #SemanticOutcome
	diagnostics?:            [#Diagnostic, ...#Diagnostic]
})

// #JudgementIngress is a definition-closed caller contract. It deliberately
// avoids recursive close() so the nested observation remains instantiable while
// the outer field vocabulary is still closed by definition semantics.
#JudgementIngress: {
	requestID:                  #SafeID
	judgementID:                #SafeID
	derivationInputDigest:      #Digest
	evaluator:                  #EvaluatorIdentity
	realizationDigest:          #Digest
	caseID:                     #SafeID
	semanticAuthorityID:        #SafeID
	packageDigest:              #Digest
	candidateDigest:            #Digest
	observation:                #ObservationRecord
	normalizedFactSetID:        #SafeID
	normalizedFactSetDigest:    #Digest
	normalizationRuleSetDigest: #Digest
	comparisonRuleSetDigest:    #Digest
	normalizationRuleIDs:       [#SafeID, ...#SafeID]
	comparisonRuleIDs:          [#SafeID, ...#SafeID]
}

// #JudgementDerivation is an internal semantic relation, not an ingress schema.
// Its caller-controlled fields are closed by their own definitions; its derived
// fields remain visible for evaluation and evidence export.
#JudgementDerivation: {
	realization: #CueRealization
	ingress:     #JudgementIngress

	_realizationIntegrity: #RealizationIntegrity & {
		realization: realization
	}
	_observationIntegrity: #ObservationIntegrity & {
		observation: ingress.observation
	}

	_case: realization.cases[ingress.caseID]
	_semanticAuthority: realization.authorities[ingress.semanticAuthorityID] & {
		role: "semantic-authority"
	}
	_observerAuthority: realization.authorities[ingress.observation.observerAuthorityID] & {
		role: "raw-observer"
	}
	_caseIDMatch:             ingress.observation.caseID & ingress.caseID
	_normalizationRulesMatch: ingress.normalizationRuleIDs & _case.normalizationRuleIDs
	_comparisonRulesMatch:    ingress.comparisonRuleIDs & _case.comparisonRuleIDs

	_normalizedFacts:   {}
	_comparisonResults: {}
	_unmatchedRuleIDs:  [...#SafeID]
	_allMatched:        bool

	if ingress.observation.state == "facts-observed" {
		_normalizedFacts: close({
			for _, RuleID in ingress.normalizationRuleIDs {
				"\(realization.normalizationRules[RuleID].normalizedFactID)": #NormalizedFact & {
					factID:                  realization.normalizationRules[RuleID].normalizedFactID
					normalizationRuleID:     RuleID
					observationFactID:       realization.normalizationRules[RuleID].observationFactID
					predicate:               realization.normalizationRules[RuleID].normalizedPredicate
					value:                   ingress.observation.facts[observationFactID].observedValue
					sourceObservationDigest: ingress.observation.sourceRecordDigest
				}
			}
		})

		_comparisonResults: close({
			for _, RuleID in ingress.comparisonRuleIDs {
				"\(RuleID)": #ComparisonResult & {
					ruleID:           RuleID
					expectedFactID:   realization.comparisonRules[RuleID].expectedFactID
					normalizedFactID: realization.comparisonRules[RuleID].normalizedFactID
					expectedValue:    realization.expectedFacts[expectedFactID].expectedValue
					observedValue:    _normalizedFacts[normalizedFactID].value
					if realization.comparisonRules[RuleID].operator == "equals" {
						matched: expectedValue == observedValue
					}
					if realization.comparisonRules[RuleID].operator == "not-equals" {
						matched: expectedValue != observedValue
					}
				}
			}
		})

		_unmatchedRuleIDs: [for RuleID, Result in _comparisonResults if Result.matched == false {RuleID}]
		_allMatched:       len(_unmatchedRuleIDs) == 0
	}

	if ingress.observation.state != "facts-observed" {
		_normalizedFacts:   close({})
		_comparisonResults: close({})
		_unmatchedRuleIDs:  []
		_allMatched:        false
	}

	_normalizedFactSet: #NormalizedFactSet & {
		factSetID:                  ingress.normalizedFactSetID
		factSetDigest:              ingress.normalizedFactSetDigest
		normalizationRuleSetDigest: ingress.normalizationRuleSetDigest
		sourceObservationDigest:    ingress.observation.sourceRecordDigest
		facts:                      _normalizedFacts
	}

	judgement: #SemanticJudgement & {
		judgementID:             ingress.judgementID
		derivationInputDigest:   ingress.derivationInputDigest
		evaluator:               ingress.evaluator
		realizationID:           realization.realizationID
		realizationDigest:       ingress.realizationDigest
		caseID:                  ingress.caseID
		semanticAuthorityID:     ingress.semanticAuthorityID
		packageDigest:           ingress.packageDigest
		candidateDigest:         ingress.candidateDigest
		observationDigest:       ingress.observation.sourceRecordDigest
		normalizedFactSet:       _normalizedFactSet
		comparisonRuleSetDigest: ingress.comparisonRuleSetDigest
		comparisonResults:       _comparisonResults

		if ingress.observation.state != "facts-observed" {
			outcome:     "indeterminate"
			diagnostics: ingress.observation.diagnostics
		}
		if ingress.observation.state == "facts-observed" && _allMatched {
			outcome: "satisfied"
		}
		if ingress.observation.state == "facts-observed" && !_allMatched {
			outcome: "rejected"
		}
	}
}

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
	normalizationRules: [RuleID=#SafeID]: #NormalizationRule & {
		ruleID: RuleID
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
