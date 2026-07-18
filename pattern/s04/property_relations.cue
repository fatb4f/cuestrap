package s04

import "list"

// Case-local coherence is a first-class relation instead of a cross-file
// extension of #RealizationIntegrity's hidden fields. Hidden field identities
// are file-scoped in CUE and are therefore unsuitable as extension points.
#CaseLocalIntegrity: I={
	realization: #CueRealization
	let R = I.realization

	_checks: {
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

	qualificationChecks: I._checks
}

// Publication forces every sibling proof that qualifies the selected
// judgement. Aliases are required for cross-file access to hidden fields.
#JudgementDerivation: D={
	_caseLocalIntegrity: #CaseLocalIntegrity & {
		realization: D.realization
	}
	_concreteQualificationPayload: {
		semanticAuthority:       D._semanticAuthority
		observerAuthority:       D._observerAuthority
		caseIDMatch:             D._caseIDMatch
		normalizationRulesMatch: D._normalizationRulesMatch
		comparisonRulesMatch:    D._comparisonRulesMatch
		caseLocalIntegrity:      D._caseLocalIntegrity.qualificationChecks
	}
}
