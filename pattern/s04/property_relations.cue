package s04

import "list"

// Publication must force every sibling proof that qualifies the selected
// judgement, not only the graph-wide integrity and derived outcome payloads.
// The aliases are required because hidden fields are lexically scoped in CUE;
// cross-file refinements must select them through the value being refined.
#JudgementDerivation: D={
	_concreteQualificationPayload: {
		semanticAuthority:       D._semanticAuthority
		observerAuthority:       D._observerAuthority
		caseIDMatch:             D._caseIDMatch
		normalizationRulesMatch: D._normalizationRulesMatch
		comparisonRulesMatch:    D._comparisonRulesMatch
	}
}

// Case-local coherence prevents a case from borrowing semantically unrelated
// nodes that merely happen to exist elsewhere in the realization graph.
#RealizationIntegrity: I={
	let R = I.realization

	_caseLocalCoherence: {
		for CaseID, Case in R.cases {
			"\(CaseID)": {
				_plan: R.plans[Case.planID]

				planSubjects: [for _, Operation in _plan.operations {
					leftSelected: true & list.Contains(Case.subjectIDs, Operation.left.subjectID)
					if Operation.kind != "validate" {
						rightSelected: true & list.Contains(Case.subjectIDs, Operation.right.subjectID)
					}
					capabilityCovered: true & (len([
						for _, CapabilityID in Case.requiredCapabilityIDs
						if list.Contains(R.capabilityRequirements[CapabilityID].operationKinds, Operation.kind) {
							CapabilityID
						}
					]) > 0)
				}]

				normalizationRules: [for _, RuleID in Case.normalizationRuleIDs {
					_rule: R.normalizationRules[RuleID]
					observationProduced: true & (len([
						for _, Operation in _plan.operations
						if list.Contains(Operation.produces, _rule.observationFactID) {
							Operation.operationID
						}
					]) > 0)
				}]

				comparisonRules: [for _, RuleID in Case.comparisonRuleIDs {
					_rule:                R.comparisonRules[RuleID]
					expectedFactSelected: true & list.Contains(Case.expectedFactIDs, _rule.expectedFactID)
					normalizedFactSelected: true & (len([
						for _, NormalizationRuleID in Case.normalizationRuleIDs
						if R.normalizationRules[NormalizationRuleID].normalizedFactID == _rule.normalizedFactID {
							NormalizationRuleID
						}
					]) > 0)
				}]

				expectedFactSubjects: [for _, FactID in Case.expectedFactIDs {
					_claim: R.claims[R.expectedFacts[FactID].claimID]
					operands: [for _, Operand in _claim.operands {
						selected: true & list.Contains(Case.subjectIDs, Operand.subjectID)
					}]
				}]
			}
		}
	}

	_qualificationChecks: {
		caseLocalCoherence: I._caseLocalCoherence
	}
}
