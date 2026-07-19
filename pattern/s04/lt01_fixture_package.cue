package s04

// Issue #18 fixture-design slice.
//
// This value consumes the qualified S04 contract without redefining it. It
// publishes only package declarations and candidate fixtures; observation,
// normalization, comparison, and judgement artifacts remain absent until the
// later execution/judgement slice.

#LT01FixtureDesignManifest: close({
	schema:              "s04.lt01-fixture-design-manifest.v0"
	trackingIssue:       18
	parentIssue:         12
	inputContractDigest: #Digest
	packageTreeDigest:   #Digest
	candidateSetDigest:  #Digest
	packageRoot:         #RelativePath
	sourceFiles: [FileID=#SafeID]: close({
		path:   #RelativePath
		digest: #Digest
	})
	produces: [
		"LT01MinimalPPFPackage.v0",
		"LT01CandidateFixtureSet.v0",
		"LT01FixtureDesignManifest.v0",
	]
	nextConsumer: "lt-01-execution-judgement-slice"
})

lt01Realization: #CueRealization & {
	schema:        "s04.cue-realization.v0"
	realizationID: "lt01-realization"
	title:         "LT-01 directional CUE subsumption"

	authorities: {
		"s04-semantic": {
			role: "semantic-authority"
			source: {
				kind:     "cue-module"
				locator:  "pattern/s04"
				revision: "3ae2953936b8eee86068516d666b8faec1f5789b"
				digest:   "sha256:0b756609d6b5f17be6c062b2ec7e15d1f22be0bece9702a2fea140f1d806e217"
			}
		}
		"lt01-declarer": {
			role: "package-declarer"
			source: {
				kind:     "problem-package"
				locator:  "pattern/s04/fixtures/lt01"
				revision: "v0"
				digest:   "sha256:6fccb0d98d54b1f4d662219076da7e56b8179f95be4680c8c59c035b1823d82e"
			}
		}
		"cuestrap-observer": {
			role: "raw-observer"
			source: {
				kind:     "process-runner"
				locator:  "cuestrap"
				revision: "cuestrap-tools-cabbc66670d9a13b17e521a049958b4651855cf71cb754432897c14d6644781b"
				digest:   "sha256:bde8864f55193a712d5e0b55e89c4e7a7fb6de11f0667dd8235f8e21373cc5e3"
			}
		}
	}

	subjects: {
		"directional-left": {
			language: "cue"
			source: {
				kind:       "inline"
				expression: "int"
			}
			mediaType: "application/cue"
		}
		"directional-right": {
			language: "cue"
			source: {
				kind:       "inline"
				expression: "1"
			}
			mediaType: "application/cue"
		}
		"reverse-left": {
			language: "cue"
			source: {
				kind:       "inline"
				expression: "1"
			}
			mediaType: "application/cue"
		}
		"reverse-right": {
			language: "cue"
			source: {
				kind:       "inline"
				expression: "int"
			}
			mediaType: "application/cue"
		}
		"structural-left": {
			language: "cue"
			source: {
				kind:       "inline"
				expression: "{a: int, b?: string}"
			}
			mediaType: "application/cue"
		}
		"structural-right": {
			language: "cue"
			source: {
				kind:       "inline"
				expression: "{b: \"x\", a: 1}"
			}
			mediaType: "application/cue"
		}
	}

	materializations: {}

	claims: {
		"directional-claim": {
			authorityID: "s04-semantic"
			predicate:   "subsumes"
			operands: [
				{subjectID: "directional-left"},
				{subjectID: "directional-right"},
			]
			value: true
		}
		"reverse-claim": {
			authorityID: "s04-semantic"
			predicate:   "subsumes"
			operands: [
				{subjectID: "reverse-left"},
				{subjectID: "reverse-right"},
			]
			value: false
		}
		"structural-claim": {
			authorityID: "s04-semantic"
			predicate:   "subsumes"
			operands: [
				{subjectID: "structural-left"},
				{subjectID: "structural-right"},
			]
			value: true
		}
	}

	expectedFacts: {
		"directional-expected": {
			claimID:       "directional-claim"
			authorityID:   "s04-semantic"
			predicate:     "subsumes"
			expectedValue: true
		}
		"reverse-expected": {
			claimID:       "reverse-claim"
			authorityID:   "s04-semantic"
			predicate:     "subsumes"
			expectedValue: false
		}
		"structural-expected": {
			claimID:       "structural-claim"
			authorityID:   "s04-semantic"
			predicate:     "subsumes"
			expectedValue: true
		}
	}

	normalizationRules: {
		"normalize-directional": {
			observationFactID:   "directional-raw"
			normalizedFactID:    "directional-normalized"
			normalizedPredicate: "subsumes"
		}
		"normalize-reverse": {
			observationFactID:   "reverse-raw"
			normalizedFactID:    "reverse-normalized"
			normalizedPredicate: "subsumes"
		}
		"normalize-structural": {
			observationFactID:   "structural-raw"
			normalizedFactID:    "structural-normalized"
			normalizedPredicate: "subsumes"
		}
	}

	comparisonRules: {
		"compare-directional": {
			expectedFactID:   "directional-expected"
			normalizedFactID: "directional-normalized"
			operator:         "equals"
			resultPredicate:  "directional-matches"
		}
		"compare-reverse": {
			expectedFactID:   "reverse-expected"
			normalizedFactID: "reverse-normalized"
			operator:         "equals"
			resultPredicate:  "reverse-matches"
		}
		"compare-structural": {
			expectedFactID:   "structural-expected"
			normalizedFactID: "structural-normalized"
			operator:         "equals"
			resultPredicate:  "structural-matches"
		}
	}

	capabilityRequirements: {
		"cue-subsumes": {
			operationKinds: ["subsumes"]
			required:       true
		}
	}

	plans: {
		"directional-plan": {
			operations: [{
				operationID: "directional-operation"
				kind:        "subsumes"
				left:        {subjectID: "directional-left"}
				right:       {subjectID: "directional-right"}
				direction:   "left-to-right"
				produces:    ["directional-raw"]
			}]
		}
		"reverse-plan": {
			operations: [{
				operationID: "reverse-operation"
				kind:        "subsumes"
				left:        {subjectID: "reverse-left"}
				right:       {subjectID: "reverse-right"}
				direction:   "left-to-right"
				produces:    ["reverse-raw"]
			}]
		}
		"structural-plan": {
			operations: [{
				operationID: "structural-operation"
				kind:        "subsumes"
				left:        {subjectID: "structural-left"}
				right:       {subjectID: "structural-right"}
				direction:   "left-to-right"
				produces:    ["structural-raw"]
			}]
		}
	}

	cases: {
		"directional-success": {
			groupID:               "lt01"
			planID:                "directional-plan"
			subjectIDs:            ["directional-left", "directional-right"]
			expectedFactIDs:       ["directional-expected"]
			normalizationRuleIDs:  ["normalize-directional"]
			comparisonRuleIDs:     ["compare-directional"]
			requiredCapabilityIDs: ["cue-subsumes"]
			outcomeConstraint: {
				permitted: ["satisfied", "rejected", "indeterminate"]
				required:  "satisfied"
			}
		}
		"reverse-direction-rejection": {
			groupID:               "lt01"
			planID:                "reverse-plan"
			subjectIDs:            ["reverse-left", "reverse-right"]
			expectedFactIDs:       ["reverse-expected"]
			normalizationRuleIDs:  ["normalize-reverse"]
			comparisonRuleIDs:     ["compare-reverse"]
			requiredCapabilityIDs: ["cue-subsumes"]
			outcomeConstraint: {
				permitted: ["satisfied", "rejected", "indeterminate"]
				required:  "satisfied"
			}
		}
		"adversarial-structural": {
			groupID:               "lt01"
			planID:                "structural-plan"
			subjectIDs:            ["structural-left", "structural-right"]
			expectedFactIDs:       ["structural-expected"]
			normalizationRuleIDs:  ["normalize-structural"]
			comparisonRuleIDs:     ["compare-structural"]
			requiredCapabilityIDs: ["cue-subsumes"]
			outcomeConstraint: {
				permitted: ["satisfied", "rejected", "indeterminate"]
				required:  "satisfied"
			}
		}
	}
}

lt01Package: #MinimalPPFPackage & {
	schema:            "s04.minimal-ppf-package.v0"
	profileID:         "s04.kattis-ppf-minimal.v0"
	sourceSpecVersion: "2025-09"
	conformance:       "profile-only"

	packageID:        "lt01-package"
	packageDirectory: "lt01"
	packageDigest:    "sha256:6fccb0d98d54b1f4d662219076da7e56b8179f95be4680c8c59c035b1823d82e"

	metadata: {
		problem_format_version: "2025-09"
		type:                   "pass-fail"
		name:                   "LT-01 Directional CUE Subsumption"
		uuid:                   "18000000-0000-4000-8000-000000000018"
		source:                 "CUEstrap S04 issue 18"
		credits: authors: ["CUEstrap"]
		license:      "permission"
		rights_owner: "CUEstrap"
		limits: {
			time_limit:        1
			memory:            64
			output:            64
			validation_time:   1
			validation_memory: 64
			validation_output: 64
		}
	}

	paths: {
		problemConfig:       "problem.yaml"
		statement:           "problem_statement/problem.en.tex"
		secretDataRoot:      "data/secret"
		submissionsRoot:     "submissions"
		inputValidatorsRoot: "input_validators"
		judgeEntrypoint:     "output_validators/s04-judge.cue"
		rawObservationRoot:  "evidence/raw"
		normalizedFactRoot:  "evidence/normalized"
		comparisonRoot:      "evidence/comparison"
		judgementRoot:       "evidence/judgement"
	}

	validator: {
		validatorID:          "lt01-independent-judge"
		kind:                 "s04-independent-judge"
		entrypoint:           "output_validators/s04-judge.cue"
		semanticAuthorityID:  "s04-semantic"
		observationInputRoot: "evidence/raw"
		judgementOutputRoot:  "evidence/judgement"
	}

	groups: {
		"lt01": {
			caseIDs: [
				"directional-success",
				"reverse-direction-rejection",
				"adversarial-structural",
			]
		}
	}

	cases: {
		"directional-success": {
			groupID:      "lt01"
			inputPath:    "data/secret/directional-success.in"
			answerPath:   "data/secret/directional-success.ans"
			evidencePath: "evidence/cases/directional-success"
		}
		"reverse-direction-rejection": {
			groupID:      "lt01"
			inputPath:    "data/secret/reverse-direction-rejection.in"
			answerPath:   "data/secret/reverse-direction-rejection.ans"
			evidencePath: "evidence/cases/reverse-direction-rejection"
		}
		"adversarial-structural": {
			groupID:      "lt01"
			inputPath:    "data/secret/adversarial-structural.in"
			answerPath:   "data/secret/adversarial-structural.ans"
			evidencePath: "evidence/cases/adversarial-structural"
		}
	}

	candidates: {
		"accepted-reference": {
			sourcePath:   "submissions/accepted/reference.cue"
			expectation:  "accepted"
			evidencePath: "evidence/candidates/accepted-reference"
		}
		"rejected-reversed-operands": {
			sourcePath:   "submissions/wrong_answer/reversed-operands.cue"
			expectation:  "rejected"
			evidencePath: "evidence/candidates/rejected-reversed-operands"
		}
	}

	evidenceRequirements: {
		"package-identity": {
			kind:    "package-identity"
			path:    "evidence/package"
			durable: true
		}
		"candidate-identity": {
			kind:    "candidate-identity"
			path:    "evidence/candidates"
			durable: true
		}
		"raw-observation": {
			kind:    "raw-observation"
			path:    "evidence/raw"
			durable: true
		}
		"normalized-fact": {
			kind:    "normalized-fact"
			path:    "evidence/normalized"
			durable: true
		}
		"comparison-result": {
			kind:    "comparison-result"
			path:    "evidence/comparison"
			durable: true
		}
		"semantic-judgement": {
			kind:    "semantic-judgement"
			path:    "evidence/judgement"
			durable: true
		}
	}
}

lt01ProjectionRequest: #S04PPFProjectionRequest & {
	projectionID:               "lt01-projection"
	projectionDigest:           "sha256:2063465b5525c69a9a76ddd866bb4802e75c58a75d775240facef3c0216e47b2"
	semanticAuthorityID:        "s04-semantic"
	packageDeclarerAuthorityID: "lt01-declarer"
	rawObserverAuthorityIDs:    ["cuestrap-observer"]
	caseMap: {
		"directional-success":         "directional-success"
		"reverse-direction-rejection": "reverse-direction-rejection"
		"adversarial-structural":      "adversarial-structural"
	}
}

lt01ProjectionDerivation: #S04PPFProjectionDerivation & {
	realizationArtifact: {
		digest:      "sha256:e3fe797f82c56ec61a4582b2121557fb94ca322c6a691e6e76e787cf0bd31f1a"
		realization: lt01Realization
	}
	package: lt01Package
	request: lt01ProjectionRequest
}

lt01CandidateContract: #S04ConsumerProfileContract & {
	schema:         "s04.consumer-profile-contract.v0"
	contractID:     "lt01-consumer-profile"
	contractDigest: "sha256:e277d2eb3d328604070a82f5858e55ceb153231f1cc5406352cb354036b0e4de"
	realization:    lt01Realization
	package:        lt01Package
	projection:     lt01ProjectionDerivation.projection
}

lt01QualifiedContract: #QualifiedS04ConsumerProfileContract & {
	candidateContract: lt01CandidateContract
	realizationArtifact: {
		digest:      "sha256:e3fe797f82c56ec61a4582b2121557fb94ca322c6a691e6e76e787cf0bd31f1a"
		realization: lt01Realization
	}
	projectionRequest: lt01ProjectionRequest
}

lt01FixtureDesignManifest: #LT01FixtureDesignManifest & {
	inputContractDigest: "sha256:0b756609d6b5f17be6c062b2ec7e15d1f22be0bece9702a2fea140f1d806e217"
	packageTreeDigest:   "sha256:6fccb0d98d54b1f4d662219076da7e56b8179f95be4680c8c59c035b1823d82e"
	candidateSetDigest:  "sha256:9a2672ff42dd3da4e5956090a683992eec880a70b7a5062003b59cb938710ffe"
	packageRoot:         "pattern/s04/fixtures/lt01"
	sourceFiles: {
		"data-secret-adversarial-structural-ans": {
			path:   "pattern/s04/fixtures/lt01/data/secret/adversarial-structural.ans"
			digest: "sha256:42e2fa586026d1bdedd1bf3c65a6f4316d4583fed4b753e25be27cc96e762ec0"
		}
		"data-secret-adversarial-structural-in": {
			path:   "pattern/s04/fixtures/lt01/data/secret/adversarial-structural.in"
			digest: "sha256:674decf8de6ea74a19bd6479dbba26dd53b61840447fba6fd921cf697f08e4f3"
		}
		"data-secret-directional-success-ans": {
			path:   "pattern/s04/fixtures/lt01/data/secret/directional-success.ans"
			digest: "sha256:7bf31203f4f28c0f35ef2fa6c343699d709bdc1f253af39cc2a36e0ad5c66c8a"
		}
		"data-secret-directional-success-in": {
			path:   "pattern/s04/fixtures/lt01/data/secret/directional-success.in"
			digest: "sha256:edea623f522a8c0f2ca41bc2780ea4d41f3ee51c128694ebaa85071bf663d1e4"
		}
		"data-secret-reverse-direction-rejection-ans": {
			path:   "pattern/s04/fixtures/lt01/data/secret/reverse-direction-rejection.ans"
			digest: "sha256:6e7d088eb7f27e2e33a3cd079bc0fb8ded79e511fe10f12fc91a92f026790b8b"
		}
		"data-secret-reverse-direction-rejection-in": {
			path:   "pattern/s04/fixtures/lt01/data/secret/reverse-direction-rejection.in"
			digest: "sha256:33b5102ff275ebff6ded100d90b4de8b2bd71bad0a603b73a97b7c89decc0bc3"
		}
		"evidence-readme-md": {
			path:   "pattern/s04/fixtures/lt01/evidence/README.md"
			digest: "sha256:bf08ad2727a33989f820c7b8d9a0cc78e5125a0bea6a87bece3ff021f9409c18"
		}
		"input-validators-readme-md": {
			path:   "pattern/s04/fixtures/lt01/input_validators/README.md"
			digest: "sha256:b7b5f42a1e8eda7cfd9400d43253c9ba37cc065b87ca240514287c35a8a9376f"
		}
		"output-validators-s04-judge-cue": {
			path:   "pattern/s04/fixtures/lt01/output_validators/s04-judge.cue"
			digest: "sha256:3e0ded93663e1fe43ebdacebcef18e649765b758cba674d97a2789dbd94cb782"
		}
		"problem-yaml": {
			path:   "pattern/s04/fixtures/lt01/problem.yaml"
			digest: "sha256:df613c5d3e762dcd249355c34ad9712a65e5e924e4c5109f450678a95f5f52bd"
		}
		"problem-statement-problem-en-tex": {
			path:   "pattern/s04/fixtures/lt01/problem_statement/problem.en.tex"
			digest: "sha256:63807499784b5ea20310933a6cf49495ecccf08ad3cc99fa2e0fc36623990372"
		}
		"submissions-accepted-reference-cue": {
			path:   "pattern/s04/fixtures/lt01/submissions/accepted/reference.cue"
			digest: "sha256:7db9a8c8c66530b109da948a938a9750f1b77dd6f3688fa9aed4e37f5084d2d4"
		}
		"submissions-wrong-answer-reversed-operands-cue": {
			path:   "pattern/s04/fixtures/lt01/submissions/wrong_answer/reversed-operands.cue"
			digest: "sha256:d77b99ce3244126f92fac1b42c0acdcade2a59d7e5bad330f0704b7e3fb3278d"
		}
	}
}
