package s04

import (
	"encoding/json"
	"list"
)

#CueRealizationArtifact: close({
	digest:      #Digest
	realization: #CueRealization
})

#S04PPFProjectionRequest: close({
	projectionID:               #SafeID
	projectionDigest:           #Digest
	semanticAuthorityID:        #SafeID
	packageDeclarerAuthorityID: #SafeID
	rawObserverAuthorityIDs:    [#SafeID, ...#SafeID]
	caseMap: [RealizationCaseID=#SafeID]: #SafeID
})

// Projection is an internal construction. The public field exists only after
// every totality, membership, role, validator, and realization proof is concrete.
#S04PPFProjectionDerivation: D={
	realizationArtifact: #CueRealizationArtifact
	package:             #MinimalPPFPackage
	request:             #S04PPFProjectionRequest

	let R = D.realizationArtifact.realization
	let P = D.package
	let Q = D.request

	_realizationIntegrity: #RealizationIntegrity & {realization: R}
	_caseLocalIntegrity:   #CaseLocalIntegrity & {realization: R}

	_semanticAuthorityIDs:        [for ID, Authority in R.authorities if Authority.role == "semantic-authority" {ID}]
	_packageDeclarerAuthorityIDs: [for ID, Authority in R.authorities if Authority.role == "package-declarer" {ID}]
	_rawObserverAuthorityIDs:     [for ID, Authority in R.authorities if Authority.role == "raw-observer" {ID}]
	_realizationCaseIDs:          [for ID, _ in R.cases {ID}]
	_requestedCaseIDs:            [for ID, _ in Q.caseMap {ID}]
	_packageCaseIDs:              [for ID, _ in P.cases {ID}]

	_semanticAuthorityExists:        true & list.Contains(D._semanticAuthorityIDs, Q.semanticAuthorityID)
	_packageDeclarerAuthorityExists: true & list.Contains(D._packageDeclarerAuthorityIDs, Q.packageDeclarerAuthorityID)
	_rawObserverAuthoritiesExist: [for AuthorityID in Q.rawObserverAuthorityIDs {
		true & list.Contains(D._rawObserverAuthorityIDs, AuthorityID)
	}]
	_caseMapCardinalityMatches: len(Q.caseMap) == len(R.cases)
	_requestedCasesExist: [for RealizationCaseID, _ in Q.caseMap {
		true & list.Contains(D._realizationCaseIDs, RealizationCaseID)
	}]
	_allRealizationCasesMapped: [for RealizationCaseID, _ in R.cases {
		true & list.Contains(D._requestedCaseIDs, RealizationCaseID)
	}]
	_targetCasesExist: [for _, PackageCaseID in Q.caseMap {
		true & list.Contains(D._packageCaseIDs, PackageCaseID)
	}]
	_validatorAuthorityMatches: P.validator.semanticAuthorityID & Q.semanticAuthorityID

	_derivedProjection: #S04PPFProjection & {
		projectionID:      Q.projectionID
		projectionDigest:  Q.projectionDigest
		realizationID:     R.realizationID
		realizationDigest: D.realizationArtifact.digest
		packageID:         P.packageID
		packageDigest:     P.packageDigest
		authorities: {
			semanticAuthorityID:        Q.semanticAuthorityID
			packageDeclarerAuthorityID: Q.packageDeclarerAuthorityID
			rawObserverAuthorityIDs:    Q.rawObserverAuthorityIDs
		}
		caseBindings: {
			for RealizationCaseID, PackageCaseID in Q.caseMap {
				"\(RealizationCaseID)": {
					bindingID:         RealizationCaseID
					realizationCaseID: RealizationCaseID
					packageCaseID:     PackageCaseID
				}
			}
		}
	}

	_concreteQualificationPayload: {
		realizationArtifact:            D.realizationArtifact
		packageValue:                   D.package
		requestValue:                   D.request
		realizationIntegrity:           D._realizationIntegrity._qualificationChecks
		caseLocalIntegrity:             D._caseLocalIntegrity.qualificationChecks
		semanticAuthorityExists:        D._semanticAuthorityExists
		packageDeclarerAuthorityExists: D._packageDeclarerAuthorityExists
		rawObserverAuthoritiesExist:    D._rawObserverAuthoritiesExist
		caseMapCardinalityMatches:      D._caseMapCardinalityMatches
		requestedCasesExist:            D._requestedCasesExist
		allRealizationCasesMapped:      D._allRealizationCasesMapped
		targetCasesExist:               D._targetCasesExist
		validatorAuthorityMatches:      D._validatorAuthorityMatches
		derivedProjection:              D._derivedProjection
	}
	_concreteQualificationJSON: json.Marshal(D._concreteQualificationPayload)

	if D._concreteQualificationJSON != "" {
		projection: D._derivedProjection
	}
}

// A candidate contract is input. Publication forces realization equality and
// the complete projection proof; no unqualified contract field is exposed.
#QualifiedS04ConsumerProfileContract: C={
	candidateContract:   #S04ConsumerProfileContract
	realizationArtifact: #CueRealizationArtifact
	projectionRequest:   #S04PPFProjectionRequest

	_realizationMatches: C.candidateContract.realization & C.realizationArtifact.realization
	_projectionDerivation: #S04PPFProjectionDerivation & {
		realizationArtifact: C.realizationArtifact
		package:             C.candidateContract.package
		request:             C.projectionRequest
	}
	_projectionMatches: C.candidateContract.projection & C._projectionDerivation._derivedProjection

	_concreteQualificationPayload: {
		candidateContract:       C.candidateContract
		realizationArtifact:     C.realizationArtifact
		projectionRequest:       C.projectionRequest
		realizationMatches:      C._realizationMatches
		projectionQualification: C._projectionDerivation._concreteQualificationJSON
		derivedProjection:       C._projectionDerivation._derivedProjection
		projectionMatches:       C._projectionMatches
	}
	_concreteQualificationJSON: json.Marshal(C._concreteQualificationPayload)

	if C._concreteQualificationJSON != "" {
		contract: C.candidateContract
	}
}
