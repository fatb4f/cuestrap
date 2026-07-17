package s04

import "list"

// #RealizationIntegrity closes references inside one S04 realization. A value
// satisfying #CueRealization alone is shape-valid; a value admitted through
// this relation additionally proves that every referenced graph member exists
// and every semantic claim is bound to semantic authority.
#RealizationIntegrity: {
	realization: #CueRealization

	let R = realization

	_authorityIDs: [for ID, _ in R.authorities {ID}]
	_semanticAuthorityIDs: [for ID, Authority in R.authorities if Authority.role == "semantic-authority" {ID}]
	_subjectIDs: [for ID, _ in R.subjects {ID}]
	_claimIDs: [for ID, _ in R.claims {ID}]
	_expectedFactIDs: [for ID, _ in R.expectedFacts {ID}]
	_normalizationRuleIDs: [for ID, _ in R.normalizationRules {ID}]
	_normalizedFactIDs: [for _, Rule in R.normalizationRules {Rule.normalizedFactID}]
	_comparisonRuleIDs: [for ID, _ in R.comparisonRules {ID}]
	_capabilityIDs: [for ID, _ in R.capabilityRequirements {ID}]
	_planIDs: [for ID, _ in R.plans {ID}]

	_claims: {
		for ClaimID, Claim in R.claims {
			"\(ClaimID)": {
				authorityExists: true & list.Contains(_semanticAuthorityIDs, Claim.authorityID)
				subjectsExist: [for _, Operand in Claim.operands {
					true & list.Contains(_subjectIDs, Operand.subjectID)
				}]
			}
		}
	}

	_expectedFacts: {
		for FactID, Fact in R.expectedFacts {
			"\(FactID)": {
				claimExists:     true & list.Contains(_claimIDs, Fact.claimID)
				authorityExists: true & list.Contains(_semanticAuthorityIDs, Fact.authorityID)
				matchingClaimCount: 1 & len([for ClaimID, Claim in R.claims if ClaimID == Fact.claimID && Claim.authorityID == Fact.authorityID && Claim.predicate == Fact.predicate {ClaimID}])
			}
		}
	}

	_normalizedFactIDsUnique: true & list.UniqueItems(_normalizedFactIDs)

	_comparisonRules: {
		for RuleID, Rule in R.comparisonRules {
			"\(RuleID)": {
				expectedFactExists:   true & list.Contains(_expectedFactIDs, Rule.expectedFactID)
				normalizedFactExists: true & list.Contains(_normalizedFactIDs, Rule.normalizedFactID)
			}
		}
	}

	_plans: {
		for PlanID, Plan in R.plans {
			"\(PlanID)": {
				operations: [for _, Operation in Plan.operations {
					leftSubjectExists: true & list.Contains(_subjectIDs, Operation.left.subjectID)
					if Operation.kind != "validate" {
						rightSubjectExists: true & list.Contains(_subjectIDs, Operation.right.subjectID)
					}
				}]
			}
		}
	}

	_cases: {
		for CaseID, Case in R.cases {
			"\(CaseID)": {
				planExists: true & list.Contains(_planIDs, Case.planID)
				subjectsExist: [for _, SubjectID in Case.subjectIDs {
					true & list.Contains(_subjectIDs, SubjectID)
				}]
				expectedFactsExist: [for _, FactID in Case.expectedFactIDs {
					true & list.Contains(_expectedFactIDs, FactID)
				}]
				normalizationRulesExist: [for _, RuleID in Case.normalizationRuleIDs {
					true & list.Contains(_normalizationRuleIDs, RuleID)
				}]
				comparisonRulesExist: [for _, RuleID in Case.comparisonRuleIDs {
					true & list.Contains(_comparisonRuleIDs, RuleID)
				}]
				capabilitiesExist: [for _, CapabilityID in Case.requiredCapabilityIDs {
					true & list.Contains(_capabilityIDs, CapabilityID)
				}]
			}
		}
	}
}

// Raw observation facts are identity-bound to their enclosing record.
#ObservationIntegrity: {
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
}
