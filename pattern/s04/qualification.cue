package s04

// These constraints turn the committed generic witness into executable
// qualification evidence without introducing LT-01 package fixtures.
validation: {
	positive: {
		_concreteQualificationJSON: string & !=""
		_derivedJudgement: {
			outcome: "satisfied"
			comparisonResults: {
				"compare": {
					matched: true
				}
			}
		}
	}
	indeterminate: {
		_concreteQualificationJSON: string & !=""
		_derivedJudgement: {
			outcome:           "indeterminate"
			comparisonResults: close({})
			normalizedFactSet: {
				facts: close({})
			}
		}
	}
}
