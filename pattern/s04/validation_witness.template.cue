package s04

// This template is not loaded by production code. The validation workflow
// copies it to a temporary filename inside the package and evaluates the
// relations against one positive and one indeterminate witness.
validation: {
	_digest: "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

	realization: #CueRealization & {
		realizationID: "lt-witness"
		title:         "S04 validation witness"
		authorities: {
			"semantic": {
				authorityID: "semantic"
				role:        "semantic-authority"
				source: {kind: "cue-module", locator: "pattern/s04", revision: "v0", digest: _digest}
			}
			"declarer": {
				authorityID: "declarer"
				role:        "package-declarer"
				source: {kind: "problem-package", locator: "witness", revision: "v0", digest: _digest}
			}
			"observer": {
				authorityID: "observer"
				role:        "raw-observer"
				source: {kind: "process-runner", locator: "witness", revision: "v0", digest: _digest}
			}
		}
		subjects: {
			"left":  {subjectID: "left", language: "cue", source: {kind: "inline", expression: "int"}, mediaType: "application/cue"}
			"right": {subjectID: "right", language: "cue", source: {kind: "inline", expression: "1"}, mediaType: "application/cue"}
		}
		claims: {
			"claim": {
				claimID: "claim", authorityID: "semantic", predicate: "subsumes", operands: [{subjectID: "left"}, {subjectID: "right"}], value: true
			}
		}
		expectedFacts: {
			"expected": {factID: "expected", claimID: "claim", authorityID: "semantic", predicate: "subsumes", expectedValue: true}
		}
		normalizationRules: {
			"normalize": {ruleID: "normalize", observationFactID: "raw", normalizedFactID: "normalized", normalizedPredicate: "subsumes"}
		}
		comparisonRules: {
			"compare": {ruleID: "compare", expectedFactID: "expected", normalizedFactID: "normalized", operator: "equals", resultPredicate: "matches"}
		}
		capabilityRequirements: {
			"native-subsumes": {capabilityID: "native-subsumes", operationKinds: ["subsumes"], required: true}
		}
		plans: {
			"plan": {
				planID: "plan"
				operations: [{operationID: "operation", kind: "subsumes", left: {subjectID: "left"}, right: {subjectID: "right"}, direction: "left-to-right", produces: ["raw"]}]
			}
		}
		cases: {
			"case": {
				caseID: "case", groupID: "group", planID: "plan", subjectIDs: ["left", "right"], expectedFactIDs: ["expected"], normalizationRuleIDs: ["normalize"], comparisonRuleIDs: ["compare"], requiredCapabilityIDs: ["native-subsumes"], outcomeConstraint: {permitted: ["satisfied", "rejected", "indeterminate"]}
			}
		}
	}

	positive: #JudgementDerivation & {
		realization: realization
		ingress: {
			requestID: "positive-request", judgementID: "positive-judgement", derivationInputDigest: _digest,
			evaluator: {cueRevision: "806821e40fae070318600a264d311517e596353b", languageVersion: "v0.18.0", relationID: "s04.derive-semantic-judgement.v0", facadeDigest: _digest},
			realizationDigest: _digest, caseID: "case", semanticAuthorityID: "semantic", packageDigest: _digest, candidateDigest: _digest,
			observation: {schema: "s04.observation-record.v0", observationID: "positive-observation", caseID: "case", observerAuthorityID: "observer", sourceRecordDigest: _digest, state: "facts-observed", facts: {"raw": {factID: "raw", observationID: "positive-observation", predicate: "subsumes", observedValue: true, sourceRecordDigest: _digest}}},
			normalizedFactSetID: "positive-facts", normalizedFactSetDigest: _digest, normalizationRuleSetDigest: _digest, comparisonRuleSetDigest: _digest,
			normalizationRuleIDs: ["normalize"], comparisonRuleIDs: ["compare"]
		}
	}

	indeterminate: #JudgementDerivation & {
		realization: realization
		ingress: {
			requestID: "missing-request", judgementID: "missing-judgement", derivationInputDigest: _digest,
			evaluator: {cueRevision: "806821e40fae070318600a264d311517e596353b", languageVersion: "v0.18.0", relationID: "s04.derive-semantic-judgement.v0", facadeDigest: _digest},
			realizationDigest: _digest, caseID: "case", semanticAuthorityID: "semantic", packageDigest: _digest, candidateDigest: _digest,
			observation: {schema: "s04.observation-record.v0", observationID: "missing-observation", caseID: "case", observerAuthorityID: "observer", sourceRecordDigest: _digest, state: "capability-absent", facts: {}, diagnostics: [{code: "capability-absent", message: "required capability unavailable"}]},
			normalizedFactSetID: "missing-facts", normalizedFactSetDigest: _digest, normalizationRuleSetDigest: _digest, comparisonRuleSetDigest: _digest,
			normalizationRuleIDs: ["normalize"], comparisonRuleIDs: ["compare"]
		}
	}
}
