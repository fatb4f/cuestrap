package s04

// Slice 1c deterministic resolver source. This value exposes only the already
// qualified handoff and immutable candidate source identities. It contains no
// runtime observation, normalized fact, comparison result, or judgement.

#LT01ExecutionResolutionSource: close({
	schema:      "s04.lt01-execution-resolution-source.v0"
	manifest:    #LT01FixtureDesignManifest
	realization: #CueRealization
	package:     #MinimalPPFPackage
	semanticArtifacts: close({
		realization: #LT01SemanticArtifactIdentity
		projection:  #LT01SemanticArtifactIdentity
		contract:    #LT01SemanticArtifactIdentity
	})
	semanticCanonicalJSON: close({
		realization: string
		projection:  string
		contract:    string
	})
	caseBindings: [BindingID=#SafeID]: close({
		bindingID:         BindingID
		realizationCaseID: #SafeID
		packageCaseID:     #SafeID
	})
	semanticAuthorityID: #SafeID
	observerAuthorityID: #SafeID
	candidates: [CandidateID=#SafeID]: close({
		candidateID: CandidateID
		sourcePath:  #RelativePath
		digest:      #Digest
	})
})

lt01ExecutionResolutionSource: #LT01ExecutionResolutionSource & {
	manifest:    lt01FixtureDesignManifest
	realization: lt01QualifiedContract.contract.realization
	package:     lt01QualifiedContract.contract.package
	semanticArtifacts: {
		realization: {
			artifactID: lt01RealizationIdentityEvidence.artifactID
			digest:     lt01RealizationIdentityEvidence.digest
		}
		projection: {
			artifactID: lt01ProjectionIdentityEvidence.artifactID
			digest:     lt01ProjectionIdentityEvidence.digest
		}
		contract: {
			artifactID: lt01ContractIdentityEvidence.artifactID
			digest:     lt01ContractIdentityEvidence.digest
		}
	}
	semanticCanonicalJSON: {
		realization: "\(lt01RealizationIdentityEvidence.canonicalJSON)"
		projection:  "\(lt01ProjectionIdentityEvidence.canonicalJSON)"
		contract:    "\(lt01ContractIdentityEvidence.canonicalJSON)"
	}
	caseBindings:        lt01QualifiedContract.contract.projection.caseBindings
	semanticAuthorityID: lt01QualifiedContract.contract.projection.authorities.semanticAuthorityID
	observerAuthorityID: lt01QualifiedContract.contract.projection.authorities.rawObserverAuthorityIDs[0]
	candidates: {
		"accepted-reference": {
			sourcePath: "pattern/s04/fixtures/lt01/" + lt01Package.candidates["accepted-reference"].sourcePath
			digest:     lt01FixtureDesignManifest.sourceFiles["submissions-accepted-reference-cue"].digest
		}
		"rejected-reversed-operands": {
			sourcePath: "pattern/s04/fixtures/lt01/" + lt01Package.candidates["rejected-reversed-operands"].sourcePath
			digest:     lt01FixtureDesignManifest.sourceFiles["submissions-wrong-answer-reversed-operands-cue"].digest
		}
	}
}
