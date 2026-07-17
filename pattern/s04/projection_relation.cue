package s04

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

// #S04PPFProjectionDerivation proves that the mapping is total over the S04
// realization, contains no foreign S04 cases, targets existing package cases,
// and binds every projected authority to the required role.
#S04PPFProjectionDerivation: close({
	realizationArtifact: #CueRealizationArtifact
	package:             #MinimalPPFPackage
	request:             #S04PPFProjectionRequest

	let R = realizationArtifact.realization
	let P = package
	let Q = request

	_realizationIntegrity: #RealizationIntegrity & {
		realization: R
	}
	_semanticAuthority: R.authorities[Q.semanticAuthorityID] & {
		role: "semantic-authority"
	}
	_packageDeclarerAuthority: R.authorities[Q.packageDeclarerAuthorityID] & {
		role: "package-declarer"
	}
	_rawObserverAuthorities: [for _, AuthorityID in Q.rawObserverAuthorityIDs {
		R.authorities[AuthorityID] & {role: "raw-observer"}
	}]

	// Every requested source case must exist, which rejects foreign keys.
	_requestedSourceCases: {
		for RealizationCaseID, _ in Q.caseMap {
			"\(RealizationCaseID)": R.cases[RealizationCaseID]
		}
	}

	// Every realization case must have exactly one map entry and target an
	// existing package case. Map keys make the source binding unique.
	_totalTargetCases: {
		for RealizationCaseID, _ in R.cases {
			"\(RealizationCaseID)": P.cases[Q.caseMap[RealizationCaseID]]
		}
	}

	package: {
		validator: {
			semanticAuthorityID: Q.semanticAuthorityID
		}
	}

	projection: #S04PPFProjection & {
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
})

// This is the admitted consumer-profile contract relation. The original
// #S04ConsumerProfileContract remains the closed data envelope; qualification
// requires its projection to be the exact output of the derivation above.
#QualifiedS04ConsumerProfileContract: close({
	contract:            #S04ConsumerProfileContract
	realizationArtifact: #CueRealizationArtifact
	projectionRequest:   #S04PPFProjectionRequest

	realizationArtifact: {
		realization: contract.realization
	}

	_projectionDerivation: #S04PPFProjectionDerivation & {
		realizationArtifact: realizationArtifact
		package:             contract.package
		request:             projectionRequest
		projection:          contract.projection
	}
})
