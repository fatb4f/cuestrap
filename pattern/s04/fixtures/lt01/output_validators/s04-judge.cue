package validator

// Fixture-design entrypoint contract only. The execution/judgement slice binds
// raw observation records to these paths and evaluates the qualified S04 judge.
entrypoint: {
	schema:               "s04.lt01-judge-entrypoint.v0"
	observationInputRoot: "evidence/raw"
	normalizedFactRoot:   "evidence/normalized"
	comparisonRoot:       "evidence/comparison"
	judgementOutputRoot:  "evidence/judgement"
	semanticAuthority:    "s04-semantic"
}
