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
	evidenceDigest?:   #Digest
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
// identity excludes this manifest file to avoid self-reference and is computed
// over the ordered path/blob records below.
sliceOutput: #S04ContractBundleManifest & {
	sourceSetDigest: "sha256:95b7bc6342dff95727fbbb1ee65c42a9c743e2312b1bccb846f9137ea03d21f3"

	sourceFiles: {
		"integrity": {
			path:       "pattern/s04/integrity.cue"
			gitBlobSHA: "c3059dc075c76d3245762371dd3842985bba1098"
		}
		"invalid-projection": {
			path:       "pattern/s04/invalid_projection.cue.txt"
			gitBlobSHA: "529a464fd761a20984e2276b3bb8f902d4512a0a"
		}
		"invalid-reference": {
			path:       "pattern/s04/invalid_reference.cue.txt"
			gitBlobSHA: "1144021fc15fe034e8dacdb989bfee34eefab244"
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
			gitBlobSHA: "7d0035d382faf66646e61623f1e2d451af4e3653"
		}
		"semantic-ir": {
			path:       "pattern/s04/semantic_ir.cue"
			gitBlobSHA: "6a0fe24a4d51a07aedd7055f9222eb738b9afb01"
		}
		"validation-witness": {
			path:       "pattern/s04/validation_witness.cue"
			gitBlobSHA: "7a235ce14a62d70cd8bc857362a6f3a84d7775b0"
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
		disposition:       "indeterminate"
		evaluatorRevision: "806821e40fae070318600a264d311517e596353b"
		languageVersion:   "v0.18.0"
		goVersion:         "1.25.5"
		commands: [
			"cue fmt --check pattern/s04/*.cue",
			"cue vet -c=false pattern/s04/*.cue",
			"cue eval pattern/s04/*.cue -e validation.positive.judgement.outcome --out text",
			"cue eval pattern/s04/*.cue -e validation.indeterminate.judgement.outcome --out text",
			"expected-bottom validation for binary validate, foreign semantic references, and foreign projection cases",
		]
		diagnostics: [{
			code:    "exact-source-validation-pending"
			message: "The exact frozen source set has not yet been qualified."
		}]
	}
}
