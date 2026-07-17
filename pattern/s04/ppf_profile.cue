package s04

// Minimal S04 projection of the Kattis Problem Package Format.
//
// The profile pins the package surfaces needed by issue #12 without importing
// Kattis verdicts as semantic authority. Candidate expectations are package
// declarations; final outcomes are #SemanticJudgement values derived by S04.

#PPFSourceSpecVersion: "2025-09"
#PPFProfileID:         "s04.kattis-ppf-minimal.v0"
#PackageShortName:     #NonEmptyString & =~"^[a-z0-9]+$"
#UUID: #NonEmptyString & =~"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"

#PPFLicense:
	"unknown" |
	"public domain" |
	"cc0" |
	"cc by" |
	"cc by-sa" |
	"educational" |
	"permission"

#PPFCredits: close({
	authors: [#NonEmptyString, ...#NonEmptyString]
})

// #PPFExecutionLimits uses the field names serialized in problem.yaml.
#PPFExecutionLimits: close({
	"time_limit":        number & >0
	memory:              int & >0
	output:              int & >0
	"validation_time":  number & >0
	"validation_memory": int & >0
	"validation_output": int & >0
})

// #PPFProblemMetadata is the exact problem.yaml projection used by this profile.
#PPFProblemMetadata: close({
	"problem_format_version": #PPFSourceSpecVersion
	type:                     "pass-fail"
	name:                     #NonEmptyString
	uuid:                     #UUID
	source?:                  #NonEmptyString
	credits?:                 #PPFCredits
	license?:                 #PPFLicense
	"rights_owner"?:          #NonEmptyString
	limits:                   #PPFExecutionLimits
})

#PPFPackagePaths: close({
	problemConfig:       "problem.yaml"
	statement:           #RelativePath
	secretDataRoot:      "data/secret"
	submissionsRoot:     "submissions"
	inputValidatorsRoot: "input_validators"
	judgeEntrypoint:     #RelativePath
	rawObservationRoot:  #RelativePath
	normalizedFactRoot:  #RelativePath
	comparisonRoot:      #RelativePath
	judgementRoot:       #RelativePath
})

#PPFCaseGroup: close({
	groupID: #SafeID
	caseIDs: [#SafeID, ...#SafeID]
})

#PPFCase: close({
	caseID:       #SafeID
	groupID:      #SafeID
	inputPath:    #RelativePath
	answerPath:   #RelativePath
	evidencePath: #RelativePath
})

#CandidateExpectation:
	"accepted" |
	"rejected"

#PPFCandidate: close({
	candidateID:  #SafeID
	sourcePath:   #RelativePath
	expectation:  #CandidateExpectation
	evidencePath: #RelativePath
})

#PPFValidator: close({
	validatorID:          #SafeID
	kind:                 "s04-independent-judge"
	entrypoint:           #RelativePath
	semanticAuthorityID:  #SafeID
	observationInputRoot: #RelativePath
	judgementOutputRoot:  #RelativePath
})

#PPFEvidenceRequirement: close({
	evidenceID: #SafeID
	kind:
		"package-identity" |
		"candidate-identity" |
		"raw-observation" |
		"normalized-fact" |
		"comparison-result" |
		"semantic-judgement"
	path:    #RelativePath
	durable: true
})

#MinimalPPFPackage: close({
	schema:            "s04.minimal-ppf-package.v0"
	profileID:         #PPFProfileID
	sourceSpecVersion: #PPFSourceSpecVersion
	conformance:       "profile-only"

	packageID:       #SafeID
	packageDirectory: #PackageShortName
	packageDigest:   #Digest
	metadata: #PPFProblemMetadata & {
		"problem_format_version": sourceSpecVersion
	}
	paths: #PPFPackagePaths
	validator: #PPFValidator & {
		entrypoint:           paths.judgeEntrypoint
		observationInputRoot: paths.rawObservationRoot
		judgementOutputRoot:  paths.judgementRoot
	}

	groups: [GroupID=#SafeID]: #PPFCaseGroup & {
		groupID: GroupID
	}
	cases: [CaseID=#SafeID]: #PPFCase & {
		caseID: CaseID
	}
	candidates: [CandidateID=#SafeID]: #PPFCandidate & {
		candidateID: CandidateID
	}
	evidenceRequirements: [EvidenceID=#SafeID]: #PPFEvidenceRequirement & {
		evidenceID: EvidenceID
	}
})

#CaseProjectionBinding: close({
	bindingID:         #SafeID
	realizationCaseID: #SafeID
	packageCaseID:     #SafeID
})

#AuthorityProjection: close({
	semanticAuthorityID:        #SafeID
	packageDeclarerAuthorityID: #SafeID
	rawObserverAuthorityIDs:    [#SafeID, ...#SafeID]
})

#S04PPFProjection: close({
	schema: "s04.ppf-projection.v0"

	projectionID:      #SafeID
	projectionDigest:  #Digest
	realizationID:     #SafeID
	realizationDigest: #Digest
	packageID:         #SafeID
	packageDigest:     #Digest

	authorities: #AuthorityProjection
	caseBindings: [BindingID=#SafeID]: #CaseProjectionBinding & {
		bindingID: BindingID
	}
	judgementVocabulary: "s04.semantic-outcome.v0"
})

#S04ConsumerProfileContract: close({
	schema:         "s04.consumer-profile-contract.v0"
	contractID:     #SafeID
	contractDigest: #Digest
	realization:    #CueRealization
	package:        #MinimalPPFPackage
	projection: #S04PPFProjection & {
		realizationID: realization.realizationID
		packageID:     package.packageID
		packageDigest: package.packageDigest
		authorities: {
			semanticAuthorityID: package.validator.semanticAuthorityID
		}
	}
})
