package s04

// #RealizationIntegrity closes references inside one S04 realization. A value
// satisfying #CueRealization alone is shape-valid; a value admitted through
// this relation additionally proves that every referenced graph member exists
// and every semantic claim is bound to semantic authority.
#RealizationIntegrity: close({
	realization: #CueRealization

	let R = realization

	_claims: {
		for ClaimID, Claim in R.claims {
			"\(ClaimID)": {
				authority: R.authorities[Claim.authorityID] & {
					role: "semantic-authority"
				}
				subjects: [for _, Operand in Claim.operands {
					R.subjects[Operand.subjectID]
				}]
			}
		}
	}

	_expectedFacts: {
		for FactID, Fact in R.expectedFacts {
			"\(FactID)": {
				claim: R.claims[Fact.claimID] & {
					authorityID: Fact.authorityID
					predicate:   Fact.predicate
				}
				authority: R.authorities[Fact.authorityID] & {
					role: "semantic-authority"
				}
			}
		}
	}

	_comparisonRules: {
		for RuleID, Rule in R.comparisonRules {
			"\(RuleID)": {
				expectedFact: R.expectedFacts[Rule.expectedFactID]
			}
		}
	}

	_plans: {
		for PlanID, Plan in R.plans {
			"\(PlanID)": {
				operations: [for _, Operation in Plan.operations {
					leftSubject: R.subjects[Operation.left.subjectID]
					if Operation.kind != "validate" {
						rightSubject: R.subjects[Operation.right.subjectID]
					}
				}]
			}
		}
	}

	_cases: {
		for CaseID, Case in R.cases {
			"\(CaseID)": {
				plan: R.plans[Case.planID]
				subjects: [for _, SubjectID in Case.subjectIDs {
					R.subjects[SubjectID]
				}]
				expectedFacts: [for _, FactID in Case.expectedFactIDs {
					R.expectedFacts[FactID]
				}]
				comparisonRules: [for _, RuleID in Case.comparisonRuleIDs {
					R.comparisonRules[RuleID]
				}]
				capabilities: [for _, CapabilityID in Case.requiredCapabilityIDs {
					R.capabilityRequirements[CapabilityID]
				}]
			}
		}
	}
})

// Raw observation facts are identity-bound to their enclosing record.
#ObservationIntegrity: close({
	observation: #ObservationRecord

	let O = observation
	_facts: {
		for FactID, Fact in O.facts {
			"\(FactID)": Fact & {
				factID:             FactID
				observationID:      O.observationID
				sourceRecordDigest: O.sourceRecordDigest
			}
		}
	}
})

// Every judgement derivation consumes referentially closed realization and
// observation graphs, and its selected rules are exactly the case rules.
#JudgementDerivation: {
	_realizationIntegrity: #RealizationIntegrity & {
		realization: realization
	}
	_observationIntegrity: #ObservationIntegrity & {
		observation: ingress.observation
	}
	_caseReference: realization.cases[ingress.caseID]
	_semanticAuthorityReference: realization.authorities[ingress.semanticAuthorityID] & {
		role: "semantic-authority"
	}
	_observerAuthorityReference: realization.authorities[ingress.observation.observerAuthorityID] & {
		role: "raw-observer"
	}
	ingress: {
		comparisonRuleIDs: _caseReference.comparisonRuleIDs
		observation: {
			caseID: ingress.caseID
		}
	}
}
