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
	disposition: #SliceQualificationDisposition
	evaluatorRevision?: #NonEmptyString
	languageVersion?:   #NonEmptyString
	commands?:           [#NonEmptyString, ...#NonEmptyString]
	evidenceDigest?:     #Digest
	diagnostics?:        [#Diagnostic, ...#Diagnostic]
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
	produces: ["S04ConsumerProfileContract.v0"]
	nextConsumer: "lt-01-fixture-design-slice"

	qualification: #SliceQualification
})

// sliceOutput is the concrete artifact handed to the next slice. Its payload
// identity excludes this manifest file to avoid self-reference and is computed
// over the ordered path/blob records below.
sliceOutput: #S04ContractBundleManifest & {
	sourceSetDigest: "sha256:231a41303557af534153cece4187b107bd6add6247309845b92cca02da0e3d29"

	sourceFiles: {
		"integrity": {
			path:       "pattern/s04/integrity.cue"
			gitBlobSHA: "9733a94cfcfd5864271aacf7cee91ad5c962ea81"
		}
		"operation-constraints": {
			path:       "pattern/s04/operation_constraints.cue"
			gitBlobSHA: "2d2279cf7059d228fef2c0fe4ead6ae7d7ecb50d"
		}
		"ppf-profile": {
			path:       "pattern/s04/ppf_profile.cue"
			gitBlobSHA: "e9556b4749f967a9b41bc8b3b63b79c8d4e15dc2"
		}
		"projection-relation": {
			path:       "pattern/s04/projection_relation.cue"
			gitBlobSHA: "5a8d1d99423543651a3486e320fc4a886c0f532e"
		}
		"semantic-ir": {
			path:       "pattern/s04/semantic_ir.cue"
			gitBlobSHA: "2802146dc2d9c5886681789ee7f2f0cad3c648f2"
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
		disposition: "indeterminate"
		diagnostics: [{
			code:    "cue-validation-pending"
			message: "Exact CUE v0.18 structural and witness validation is pending."
		}]
	}
}
