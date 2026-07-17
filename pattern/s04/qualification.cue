package s04

// These constraints turn the committed generic witness into executable
// qualification evidence without introducing LT-01 package fixtures.
validation: {
	positive: {
		judgement: {
			outcome: "satisfied"
			comparisonResults: {
				"compare": {
					matched: true
				}
			}
		}
	}
	indeterminate: {
		judgement: {
			outcome:           "indeterminate"
			comparisonResults: close({})
			normalizedFactSet: {
				facts: close({})
			}
		}
	}
}

// Negative shape witness: validate cannot acquire a right operand.
_invalidBinaryValidate: #PrimitiveOperation & {
	operationID: "invalid-validate"
	kind:        "validate"
	left:        {subjectID: "left"}
	right:       {subjectID: "right"}
	direction:   "subject-only"
	produces:    ["raw"]
}
