package s04

import (
	"encoding/json"
	"list"
)

#CueRealizationArtifact: close({
	digest:      #Digest
	realization: #CueRealization
})

// Callers select exact authority and case mappings but do not supply the
// resulting projection envelope.
#S04PPFProjectionRequest: close({
	projectionID:     #SafeID
	projectionDigest: #Digest

	semanticAuthorityID:        #SafeID
	packageDeclarerAuthorityID: #SafeID
	rawObserverAuthorityIDs:    [#SafeID, ...#SafeID]

	// Keys are S04 realization case IDs; values are package case IDs.
	caseMap: [RealizationCaseID=#SafeID]: #SafeID
})

// The projection is constructed internally and published only when every
// totality, membership, authority, validator, and realization-integrity proof
// is concrete.
#S04PPFProjectionDerivation: {
	realizationArtifact: #CueRealizationArtifact
	package:             #MinimalPPFPackage
	request:             #S04PPFProjectionRequest

	let R = realizationArtifact.realization
	let P = package
	let Q = request

	_realizationIntegrity: #RealizationIntegrity & {
		realization: R
	}

	_semanticAuthorityIDs:        [for ID, Authority in R.authorities if Authority.role == "semantic-authority" {ID}]
	_packageDeclarerAuthorityIDs: [for ID, Authority in R.authorities if Authority.role == "package-declarer" {ID}]
	_rawObserverAuthorityIDs:     [for ID, Authority in R.authorities if Authority.role == "raw-observer" {ID}]
	_realizationCaseIDs:          [for ID, _ in R.cases {ID}]
	_requestedCaseIDs:            [for ID, _ in Q.caseMap {ID}]
	_packageCaseIDs:              [for ID, _ in P.cases {ID}]

	_semanticAuthorityExists:        true & list.Contains(_semanticAuthorityIDs, Q.semanticAuthorityID)
	_packageDeclarerAuthorityExists: true & list.Contains(_packageDeclarerAuthorityIDs, Q.packageDeclarerAuthorityID)
	_rawObserverAuthoritiesExist: [for AuthorityID in Q.rawObserverAuthorityIDs {
		true & list.Contains(_rawObserverAuthorityIDs, AuthorityID)
	}]

	_caseMapCardinalityMatches: len(Q.caseMap) == len(R.cases)
	_requestedCasesExist: [for RealizationCaseID, _ in Q.caseMap {
		true & list.Contains(_realizationCaseIDs, RealizationCaseID)
	}]
	_allRealizationCasesMapped: [for RealizationCaseID, _ in R.cases {
		true & list.Contains(_requestedCaseIDs, RealizationCaseID)
	}]
	_targetCasesExist: [for _, PackageCaseID in Q.caseMap {
		true & list.Contains(_packageCaseIDs, PackageCaseID)
	}]

	_validatorAuthorityMatches: P.validator.semanticAuthorityID & Q.semanticAuthorityID

	_derivedProjection: #S04PPFProjection & {
		projectionID:      Q.projectionID
		projectionDigest:  Q.projectionDigest
		realizationID:     R.realizationID
		realizationDigest: realizationArtifact.digest
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
		realizationArtifact:            realizationArtifact
		package:                        package
		request:                        request
		realizationIntegrity:           _realizationIntegrity._qualificationChecks
		semanticAuthorityExists:        _semanticAuthorityExists
		packageDeclarerAuthorityExists: _packageDeclarerAuthorityExists
		rawObserverAuthoritiesExist:    _rawObserverAuthoritiesExist
		caseMapCardinalityMatches:      _caseMapCardinalityMatches
		requestedCasesExist:            _requestedCasesExist
		allRealizationCasesMapped:      _allRealizationCasesMapped
		targetCasesExist:               _targetCasesExist
		validatorAuthorityMatches:      _validatorAuthorityMatches
		derivedProjection:              _derivedProjection
	}
	_concreteQualificationJSON: json.Marshal(_concreteQualificationPayload)

	if _concreteQualificationJSON != "" {
		projection: _derivedProjection
	}
}

// A candidate contract is input. The public contract output exists only after
// realization equality and the complete projection proof are concrete.
#QualifiedS04ConsumerProfileContract: {
	candidateContract:   #S04ConsumerProfileContract
	realizationArtifact: #CueRealizationArtifact
	projectionRequest:   #S04PPFProjectionRequest

	_realizationMatches: candidateContract.realization & realizationArtifact.realization

	_projectionDerivation: #S04PPFProjectionDerivation & {
		realizationArtifact: realizationArtifact
		package:             candidateContract.package
		request:             projectionRequest
	}
	_projectionMatches: candidateContract.projection & _projectionDerivation._derivedProjection

	_concreteQualificationPayload: {
		candidateContract:       candidateContract
		realizationArtifact:     realizationArtifact
		projectionRequest:       projectionRequest
		realizationMatches:      _realizationMatches
		projectionQualification: _projectionDerivation._concreteQualificationJSON
		derivedProjection:       _projectionDerivation._derivedProjection
		projectionMatches:       _projectionMatches
	}
	_concreteQualificationJSON: json.Marshal(_concreteQualificationPayload)

	if _concreteQualificationJSON != "" {
		contract: candidateContract
	}
}
