package s04

#GitBlobSHA: #NonEmptyString & =~"^[0-9a-f]{40}$"

#SliceSourceFile: close({
	path:       #RelativePath
	gitBlobSHA: #GitBlobSHA
})

#SliceQualificationDisposition:
	"qualified" |
		"not-qualified" |
		"indeterminate"

#SliceQualification: close({
	disposition:       #SliceQualificationDisposition
	evaluatorRevision: #NonEmptyString
	languageVersion:   #NonEmptyString
	goVersion:         #NonEmptyString
	commands:          [#NonEmptyString, ...#NonEmptyString]
	toolBundleDigest?: #Digest
	evidenceDigest?:   #Digest
	evidencePath?:     #RelativePath
	workflowRunID?:    uint & >0
	artifactID?:       uint & >0
	diagnostics?:      [#Diagnostic, ...#Diagnostic]
})

#S04ContractBundleManifest: close({
	schema:          "s04.contract-bundle-manifest.v0"
	artifactID:      "s04-consumer-profile-contract-v0"
	artifactKind:    "semantic-contract-bundle"
	trackingIssue:   13
	parentIssue:     12
	pullRequest:     14
	sourceSetDigest: #Digest

	sourceFiles: [FileID=#SafeID]: #SliceSourceFile
	exportedDefinitions: [#NonEmptyString, ...#NonEmptyString]

	consumes:     ["issue-12-requirements"]
	produces:     ["S04ConsumerProfileContract.v0"]
	nextConsumer: "lt-01-fixture-design-slice"

	qualification: #SliceQualification
})

// sliceOutput is the concrete artifact handed to the next slice. Its payload
// identity excludes this manifest and its qualification receipt to avoid
// self-reference. The receipt binds the exact source set and bundled evaluator.
sliceOutput: #S04ContractBundleManifest & {
	sourceSetDigest: "sha256:36c482ade6289f6bf8d618632a7e6ea4033bc4c39b1a5c668032c2966d68157f"

	sourceFiles: {
		"integrity": {
			path:       "pattern/s04/integrity.cue"
			gitBlobSHA: "0c470e3838105679f988df904745bb21b4e60b78"
		}
		"invalid-claim-value": {
			path:       "pattern/s04/invalid_claim_value.cue.txt"
			gitBlobSHA: "a793626eb555af517909425350d7295716476b35"
		}
		"invalid-disjunctive-materialization": {
			path:       "pattern/s04/invalid_disjunctive_materialization.cue.txt"
			gitBlobSHA: "2e7f6c4c58584a8f88707cdcaabe72ada2d0f711"
		}
		"invalid-disjunctive-required-outcome": {
			path:       "pattern/s04/invalid_disjunctive_required_outcome.cue.txt"
			gitBlobSHA: "0d1d1651570723fb210052de55639d6a58e80079"
		}
		"invalid-incomplete-claim-value": {
			path:       "pattern/s04/invalid_incomplete_claim_value.cue.txt"
			gitBlobSHA: "bedcdfa52a6a3df385c9ac858695664389279e47"
		}
		"invalid-incomplete-materialization": {
			path:       "pattern/s04/invalid_incomplete_materialization.cue.txt"
			gitBlobSHA: "86db56669f0e3c5d2c533041c97379611510cf1f"
		}
		"invalid-materialization": {
			path:       "pattern/s04/invalid_materialization.cue.txt"
			gitBlobSHA: "cbd7eadbef932e14f67b0d05ae0a7d10a5656f36"
		}
		"invalid-outcome-constraint": {
			path:       "pattern/s04/invalid_outcome_constraint.cue.txt"
			gitBlobSHA: "e998c46d06384fc58d60cd7de9e5df77a09ecd93"
		}
		"invalid-projection": {
			path:       "pattern/s04/invalid_projection.cue.txt"
			gitBlobSHA: "529a464fd761a20984e2276b3bb8f902d4512a0a"
		}
		"invalid-reference": {
			path:       "pattern/s04/invalid_reference.cue.txt"
			gitBlobSHA: "1144021fc15fe034e8dacdb989bfee34eefab244"
		}
		"invalid-required-not-permitted": {
			path:       "pattern/s04/invalid_required_not_permitted.cue.txt"
			gitBlobSHA: "6287cbfc81638c3e41dc8d0c06db4eb1e7e3ab6d"
		}
		"invalid-unpermitted-outcome": {
			path:       "pattern/s04/invalid_unpermitted_outcome.cue.txt"
			gitBlobSHA: "108620de0d613398d1846ee3186bf24ec1a7f2ae"
		}
		"negative-validate": {
			path:       "pattern/s04/negative_validate.cue.txt"
			gitBlobSHA: "982a8740899062581e73a1e813f10467caaa6ecb"
		}
		"ppf-profile": {
			path:       "pattern/s04/ppf_profile.cue"
			gitBlobSHA: "acf7bdb450d02cd954000838ea4a9893e0a28ac8"
		}
		"projection-relation": {
			path:       "pattern/s04/projection_relation.cue"
			gitBlobSHA: "3aa0a00a9a950b2fc40b10894c08f35e3cb0d8e5"
		}
		"qualification": {
			path:       "pattern/s04/qualification.cue"
			gitBlobSHA: "cf2f0d0a6da84fc95d7de3934a86cb2b6f473382"
		}
		"semantic-ir": {
			path:       "pattern/s04/semantic_ir.cue"
			gitBlobSHA: "e03806da77fc1653f07c1e5131e9459979a06c1d"
		}
		"validation-witness": {
			path:       "pattern/s04/validation_witness.cue"
			gitBlobSHA: "75276787f58ccdb9fecc58d4975c832e9f7123c2"
		}
	}

	exportedDefinitions: [
		"#CueRealization",
		"#RealizationIntegrity",
		"#JudgementDerivation",
		"#MinimalPPFPackage",
		"#S04PPFProjectionDerivation",
		"#QualifiedS04ConsumerProfileContract",
	]

	qualification: {
		disposition:       "qualified"
		evaluatorRevision: "806821e40fae070318600a264d311517e596353b"
		languageVersion:   "v0.18.0"
		goVersion:         "1.26.5"
		commands: [
			"cue fmt --check pattern/s04/*.cue",
			"cue vet -c=false pattern/s04/*.cue",
			"cue eval -c pattern/s04/*.cue -e validation.positive.judgement --out json",
			"cue eval -c pattern/s04/*.cue -e validation.indeterminate.judgement --out json",
			"expected-bottom validation for eight concrete structural regressions",
			"public-outcome blocking for four incomplete or disjunctive regressions",
		]
		toolBundleDigest: "sha256:bde8864f55193a712d5e0b55e89c4e7a7fb6de11f0667dd8235f8e21373cc5e3"
		evidenceDigest:   "sha256:03f2d8bf0511689a24ec964247c738967ae13108eb175e63f6e02a80652c4692"
		evidencePath:     "pattern/s04/qualification_receipt.json"
	}
}
