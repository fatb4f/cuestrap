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

	consumes: ["issue-12-requirements"]
	produces: [
		"S04ConsumerProfileContract.v0",
		"S04ObjectPropertyModel.v0",
	]
	nextConsumer: "lt-01-fixture-design-slice"

	qualification: #SliceQualification
})

// The source identity covers the CUE authority, typed construction model,
// generators, mutations, oracle facade, and property tests. This manifest and
// its receipt are excluded to avoid evidence self-reference.
sliceOutput: #S04ContractBundleManifest & {
	sourceSetDigest: "sha256:0b756609d6b5f17be6c062b2ec7e15d1f22be0bece9702a2fea140f1d806e217"
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
			gitBlobSHA: "3a60dcc2715271455f617a898166f60f571df06d"
		}
		"property-relations": {
			path:       "pattern/s04/property_relations.cue"
			gitBlobSHA: "054f0c8d5b478231c8330662e083b0ab6b60f960"
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
		"python-root-package": {
			path:       "src/cuestrap/__init__.py"
			gitBlobSHA: "3ecd433e45c8326fabb2aa4da331ad26e019a6c3"
		}
		"python-s04-package": {
			path:       "src/cuestrap/s04/__init__.py"
			gitBlobSHA: "773b6bd7a099a6909efa365ca0d8f890a0c2c3bb"
		}
		"pydantic-core": {
			path:       "src/cuestrap/s04/core.py"
			gitBlobSHA: "cdb6903c6b5cd809b8e02dab0bdb3daaa801a3ae"
		}
		"pydantic-fixtures": {
			path:       "src/cuestrap/s04/fixtures.py"
			gitBlobSHA: "cf68f354e814450e4a0592cc5e90498d021df354"
		}
		"pydantic-models": {
			path:       "src/cuestrap/s04/models.py"
			gitBlobSHA: "d2c31cf5a32cffae91fd6587818a1a6b3617ddd3"
		}
		"cue-oracle": {
			path:       "src/cuestrap/s04/oracle.py"
			gitBlobSHA: "9030c9486649274e0230e3b942c6c60e0a422952"
		}
		"pydantic-ppf": {
			path:       "src/cuestrap/s04/ppf.py"
			gitBlobSHA: "0b0152c3118c972f9e4365bb756dbfe19a5be918"
		}
		"property-catalog": {
			path:       "src/cuestrap/s04/properties.py"
			gitBlobSHA: "9b5379df36505987cbe60b403ac1b2ced20b206f"
		}
		"hypothesis-strategies": {
			path:       "src/cuestrap/s04/strategies.py"
			gitBlobSHA: "c4992889afcc779ca8addc811bdc626848d6259c"
		}
		"property-tests": {
			path:       "tests/test_s04_properties.py"
			gitBlobSHA: "89f6a8d870bcec77a8d609b1dc83a9d700f65be1"
		}
	}
	exportedDefinitions: [
		"#CueRealization",
		"#RealizationIntegrity",
		"#CaseLocalIntegrity",
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
			"python -m compileall -q src tests",
			"python -m unittest -v tests.test_s04_properties",
			"Hypothesis valid-construction, mutation, locality, publication, and metamorphic properties",
		]
		toolBundleDigest: "sha256:bde8864f55193a712d5e0b55e89c4e7a7fb6de11f0667dd8235f8e21373cc5e3"
		evidenceDigest:   "sha256:074cd21304604acdd25d4a133d28fc34e1027e478ea2786f8ca8d8199ec38f39"
		evidencePath:     "pattern/s04/qualification_receipt.json"
		workflowRunID:    29623739066
		artifactID:       8423106550
	}
}
