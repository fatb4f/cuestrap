package s04

#GitBlobSHA:                    #NonEmptyString & =~"^[0-9a-f]{40}$"
#SliceSourceFile:               close({path: #RelativePath, gitBlobSHA: #GitBlobSHA})
#SliceQualificationDisposition: "qualified" | "not-qualified" | "indeterminate"
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
	consumes:            ["issue-12-requirements"]
	produces:            ["S04ConsumerProfileContract.v0", "S04ObjectPropertyModel.v0"]
	nextConsumer:        "lt-01-fixture-design-slice"
	qualification:       #SliceQualification
})

_sourceFileList: [
	{id: "workflow-properties", path: ".github/workflows/s04-properties.yml", gitBlobSHA: "f4b9dab4f6e4159d815dc8e5cf208012067c6f58"},
	{id: "object-model", path: "pattern/s04/OBJECT_MODEL.md", gitBlobSHA: "7dd2dd34b9d36f6c11a70e77b6b3359c2fde94e2"},
	{id: "integrity", path: "pattern/s04/integrity.cue", gitBlobSHA: "0c470e3838105679f988df904745bb21b4e60b78"},
	{id: "invalid-claim-value", path: "pattern/s04/invalid_claim_value.cue.txt", gitBlobSHA: "a793626eb555af517909425350d7295716476b35"},
	{id: "invalid-disjunctive-materialization", path: "pattern/s04/invalid_disjunctive_materialization.cue.txt", gitBlobSHA: "2e7f6c4c58584a8f88707cdcaabe72ada2d0f711"},
	{id: "invalid-disjunctive-required-outcome", path: "pattern/s04/invalid_disjunctive_required_outcome.cue.txt", gitBlobSHA: "0d1d1651570723fb210052de55639d6a58e80079"},
	{id: "invalid-incomplete-claim-value", path: "pattern/s04/invalid_incomplete_claim_value.cue.txt", gitBlobSHA: "bedcdfa52a6a3df385c9ac858695664389279e47"},
	{id: "invalid-incomplete-materialization", path: "pattern/s04/invalid_incomplete_materialization.cue.txt", gitBlobSHA: "86db56669f0e3c5d2c533041c97379611510cf1f"},
	{id: "invalid-materialization", path: "pattern/s04/invalid_materialization.cue.txt", gitBlobSHA: "cbd7eadbef932e14f67b0d05ae0a7d10a5656f36"},
	{id: "invalid-outcome-constraint", path: "pattern/s04/invalid_outcome_constraint.cue.txt", gitBlobSHA: "e998c46d06384fc58d60cd7de9e5df77a09ecd93"},
	{id: "invalid-projection", path: "pattern/s04/invalid_projection.cue.txt", gitBlobSHA: "529a464fd761a20984e2276b3bb8f902d4512a0a"},
	{id: "invalid-reference", path: "pattern/s04/invalid_reference.cue.txt", gitBlobSHA: "1144021fc15fe034e8dacdb989bfee34eefab244"},
	{id: "invalid-required-not-permitted", path: "pattern/s04/invalid_required_not_permitted.cue.txt", gitBlobSHA: "6287cbfc81638c3e41dc8d0c06db4eb1e7e3ab6d"},
	{id: "invalid-unpermitted-outcome", path: "pattern/s04/invalid_unpermitted_outcome.cue.txt", gitBlobSHA: "108620de0d613398d1846ee3186bf24ec1a7f2ae"},
	{id: "negative-validate", path: "pattern/s04/negative_validate.cue.txt", gitBlobSHA: "982a8740899062581e73a1e813f10467caaa6ecb"},
	{id: "ppf-profile", path: "pattern/s04/ppf_profile.cue", gitBlobSHA: "acf7bdb450d02cd954000838ea4a9893e0a28ac8"},
	{id: "projection-relation", path: "pattern/s04/projection_relation.cue", gitBlobSHA: "a1f388624863e90b2a354f6fbdc33d374cc181bc"},
	{id: "property-relations", path: "pattern/s04/property_relations.cue", gitBlobSHA: "cb2da9219d28b080f4033c026e6292721f9785ac"},
	{id: "qualification", path: "pattern/s04/qualification.cue", gitBlobSHA: "cf2f0d0a6da84fc95d7de3934a86cb2b6f473382"},
	{id: "semantic-ir", path: "pattern/s04/semantic_ir.cue", gitBlobSHA: "e03806da77fc1653f07c1e5131e9459979a06c1d"},
	{id: "validation-witness", path: "pattern/s04/validation_witness.cue", gitBlobSHA: "75276787f58ccdb9fecc58d4975c832e9f7123c2"},
	{id: "pydantic-core", path: "src/cuestrap/s04/core.py", gitBlobSHA: "cdb6903c6b5cd809b8e02dab0bdb3daaa801a3ae"},
	{id: "pydantic-fixtures", path: "src/cuestrap/s04/fixtures.py", gitBlobSHA: "cf68f354e814450e4a0592cc5e90498d021df354"},
	{id: "pydantic-models", path: "src/cuestrap/s04/models.py", gitBlobSHA: "d2c31cf5a32cffae91fd6587818a1a6b3617ddd3"},
	{id: "cue-oracle", path: "src/cuestrap/s04/oracle.py", gitBlobSHA: "9030c9486649274e0230e3b942c6c60e0a422952"},
	{id: "pydantic-ppf", path: "src/cuestrap/s04/ppf.py", gitBlobSHA: "0b0152c3118c972f9e4365bb756dbfe19a5be918"},
	{id: "property-catalog", path: "src/cuestrap/s04/properties.py", gitBlobSHA: "9b5379df36505987cbe60b403ac1b2ced20b206f"},
	{id: "hypothesis-strategies", path: "src/cuestrap/s04/strategies.py", gitBlobSHA: "c4992889afcc779ca8addc811bdc626848d6259c"},
	{id: "property-tests", path: "tests/test_s04_properties.py", gitBlobSHA: "89f6a8d870bcec77a8d609b1dc83a9d700f65be1"},
]

sliceOutput: #S04ContractBundleManifest & {
	sourceSetDigest: "sha256:2d2222b46ba21a90dedca614daf978eeda687c07480972585849478f46d2ba53"
	sourceFiles:     {for File in _sourceFileList {"\(File.id)": {path: File.path, gitBlobSHA: File.gitBlobSHA}}}
	exportedDefinitions: [
		"#CueRealization", "#RealizationIntegrity", "#JudgementDerivation",
		"#MinimalPPFPackage", "#S04PPFProjectionDerivation",
		"#QualifiedS04ConsumerProfileContract",
	]
	qualification: {
		disposition:       "indeterminate"
		evaluatorRevision: "806821e40fae070318600a264d311517e596353b"
		languageVersion:   "v0.18.0"
		goVersion:         "1.26.5"
		commands: [
			"cue fmt --check pattern/s04/*.cue",
			"cue vet -c=false pattern/s04/*.cue",
			"python -m unittest -v tests.test_s04_properties",
			"Hypothesis publication, locality, and metamorphic properties",
		]
		toolBundleDigest: "sha256:bde8864f55193a712d5e0b55e89c4e7a7fb6de11f0667dd8235f8e21373cc5e3"
		diagnostics:      [{code: "property-qualification-pending", message: "The expanded CUE, Pydantic, and Hypothesis source set requires fresh qualification."}]
	}
}
