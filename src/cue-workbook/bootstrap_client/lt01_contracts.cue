package bootstrapclient

// Closed deterministic LT-01 workbook protocol. The caller selects only the
// action, candidate, case, and bounded recovery. All executable coordinates are
// resolved from the qualified S04 handoff before the native runner is called.

#LT01Action:
	"execute-case" |
		"report-capability-absence" |
		"report-transport-failure" |
		"report-invalid-observation"

#LT01Recovery:
	"none" |
		"retry" |
		"refresh-capabilities" |
		"stop-indeterminate" |
		"request-human-review"

#LT01CandidateID: "accepted-reference" | "rejected-reversed-operands"
#LT01CaseID:
	"directional-success" |
		"reverse-direction-rejection" |
		"adversarial-structural"

#LT01ExecutionIntent: close({
	schema:      "cuestrap.lt01-execution-intent.v0"
	action:      #LT01Action
	candidateID: #LT01CandidateID
	caseID:      #LT01CaseID
	recovery:    #LT01Recovery
})

#LT01ResolvedExecution: close({
	schema:               "cuestrap.lt01-resolved-execution.v0"
	resolutionDigest:     #Digest
	action:               #LT01Action
	recovery:             #LT01Recovery
	provenanceCommit:     =~"^[0-9a-f]{40}$"
	manifestDigest:       #Digest
	inputContractDigest:  #Digest
	realizationID:        string & !=""
	realizationDigest:    #Digest
	projectionDigest:     #Digest
	contractDigest:       #Digest
	packageDigest:        #Digest
	candidateSetDigest:   #Digest
	candidateID:          #LT01CandidateID
	candidateDigest:      #Digest
	candidateSourcePath:  #RepositoryPath
	caseID:               #LT01CaseID
	operationID:          #OperationID
	operationKind:        "subsumes"
	direction:            "left-to-right"
	leftSubjectID:        string & !=""
	rightSubjectID:       string & !=""
	leftSelector:         string & !=""
	rightSelector:        string & !=""
	observationFactID:    string & !=""
	normalizationRuleIDs: [string & !="", ...string & !=""]
	comparisonRuleIDs:    [string & !="", ...string & !=""]
	semanticAuthorityID:  string & !=""
	observerAuthorityID:  string & !=""
	capabilityIDs:        [string & !="", ...string & !=""]
	timeoutMilliseconds:  uint & >0 & <=300000
	maximumOutputBytes:   uint & >0 & <=67108864
	evidencePath:         #RepositoryPath
})

#LT01ObservationState:
	"facts-observed" |
		"transport-failure" |
		"capability-absent" |
		"invalid-observation"

#LT01RawExecutionRecord: close({
	schema:           "cuestrap.lt01-raw-execution-record.v0"
	recordDigest:     #Digest
	resolutionDigest: #Digest
	action:           #LT01Action
	transportState:   "returned" | "transport-failure"
	observationState: #LT01ObservationState
	facts: [string]: bool
	diagnostics:         [...close({code: string & !="", message: string & !=""})]
	backendObservations: _

	if observationState != "facts-observed" {
		facts:       close({})
		diagnostics: [_, ...]
	}
	if observationState == "facts-observed" {
		facts: close({subsumes: bool})
	}
})

#LT01StableReplayProjection: close({
	schema:           "cuestrap.lt01-stable-replay-projection.v0"
	rawRecordDigest:  #Digest
	projectionDigest: #Digest
	bindingDigest:    #Digest
	projection: close({
		resolutionDigest: #Digest
		action:           #LT01Action
		transportState:   "returned" | "transport-failure"
		observationState: #LT01ObservationState
		facts: [string]: bool
		diagnostics:         [...close({code: string & !="", message: string & !=""})]
		backendObservations: _
	})
})

#LT01ReplayRecord: close({
	schema:     "cuestrap.lt01-replay-record.v0"
	resolution: #LT01ResolvedExecution
	rawRecord: #LT01RawExecutionRecord & {
		resolutionDigest: resolution.resolutionDigest
		action:           resolution.action
	}
	stableReplayProjection: #LT01StableReplayProjection & {
		rawRecordDigest: rawRecord.recordDigest
		projection: {
			resolutionDigest: resolution.resolutionDigest
			action:           resolution.action
		}
	}
	replayDigest: #Digest
})
