package bootstrapclient

// This file is the contract source for the constrained bootstrap client.

#Digest:         =~"^sha256:[0-9a-f]{64}$"
#RunID:          string & !=""
#AttemptID:      string & !=""
#OperationID:    string & !=""
#ObservationID:  #Digest
#SessionID:      string & !=""
#CellID:         string & !=""
#QuestionID:     string & !=""
#TransactionID:  string & !=""
#VariableName:   =~"^[A-Za-z_][A-Za-z0-9_]*$"
#RepositoryPath: string & !=""

#BootstrapPhase: "inspect" | "probe" | "implement" | "evaluate" | "collect-evidence"

#BootstrapRunBinding: close({
	schemaVersion: "bootstrap-run-binding/v1"
	runID:         #RunID
	attemptID:     #AttemptID
	phase:         #BootstrapPhase

	controller: close({
		sourcePath:   #RepositoryPath
		sourceDigest: #Digest
	})
	target: close({
		repositoryDigest: #Digest
		workbookPath:     #RepositoryPath
		workbookDigest?:  #Digest
	})
	client: close({identity: #Digest, revision: #Digest})
	skill:  close({identity: #Digest, revision: #Digest})
	marimo: close({
		engineIdentity: #Digest
		engineRevision: #Digest
		mode:           "code-mode"
	})
	authority: close({
		cueSourceDigest:    #Digest
		cueEvaluatorDigest: #Digest
	})
})

#SessionBinding: close({
	sessionID:             #SessionID
	workbookPath:          #RepositoryPath
	sessionMetadataDigest: #Digest
	resolvedBy:            "exact-workbook-path"
	resolvedAtSequence:    uint
})

#ExecutionLimits: close({
	timeoutMilliseconds: uint & >0 & <=300000
	maximumOutputBytes:  uint & >0 & <=1048576
	maximumStdoutBytes:  uint & >0 & <=1048576
	maximumStderrBytes:  uint & >0 & <=1048576
})

#StateProjection: close({
	cells:     bool
	graph:     bool
	variables: bool
	outputs:   bool
	errors:    bool
})

#CellSelection: close({kind: "all"}) | close({
	kind:    "explicit"
	cellIDs: [#CellID, ...#CellID]
})

#ResolveSession: close({
	kind:          "resolve-session"
	operationID:   #OperationID
	workbookPath:  #RepositoryPath
	selectionRule: "exactly-one-by-workbook-path"
	limits:        #ExecutionLimits
})

#CaptureState: close({
	kind:               "capture-state"
	operationID:        #OperationID
	projection:         #StateProjection
	cellSelection:      #CellSelection
	maximumOutputBytes: uint & >0 & <=1048576
	limits:             #ExecutionLimits
})

#ProbeTemplateID: "variable-repr" | "cell-source"

#ProbeParameters: close({
	variableName?: #VariableName
	cellID?:       #CellID
})

#ObservationShape: close({
	kind:         "object" | "array" | "string" | "number" | "boolean" | "null"
	requiredKeys: [...string]
})

#RunFocusedProbe: close({
	kind:        "run-focused-probe"
	operationID: #OperationID
	questionID:  #QuestionID
	subject: close({
		workbookPath: #RepositoryPath
		cellIDs:      [...#CellID]
		variableNames: [...#VariableName]
	})
	probe: close({
		templateID: #ProbeTemplateID
		parameters: #ProbeParameters
	})
	expectedObservationShape: #ObservationShape
	limits:                   #ExecutionLimits
})

#Replacement: close({
	source:       string
	sourceDigest: #Digest
})

#TargetCell: close({
	cellID:                 #CellID
	expectedPreimageDigest: #Digest
	replacement:            #Replacement
})

#ApplyCellTransaction: close({
	kind:                     "apply-cell-transaction"
	operationID:              #OperationID
	transactionID:            #TransactionID
	targetCells:              [#TargetCell, ...#TargetCell]
	expectedWorkbookRevision: #Digest
	postCapture:              #StateProjection
	limits:                   #ExecutionLimits
})

#BootstrapOperation: #ResolveSession | #CaptureState | #RunFocusedProbe | #ApplyCellTransaction

#PreOperationInput: close({
	run:             #BootstrapRunBinding
	operationID:     #OperationID
	operation:       #BootstrapOperation
	sessionBinding?: #SessionBinding
	expectedState?:  #WorkbookStateIdentity
	limits:          #ExecutionLimits
})

#PreOperationDecision: close({
	kind:          "allow"
	requestDigest: #Digest
}) | close({
	kind:          "allow-with-constraints"
	requestDigest: #Digest
	constraints:   #ExecutionLimits
}) | close({
	kind:   "deny"
	reason: string & !=""
})

#WorkbookStateIdentity: close({
	revision:    #Digest
	cellDigests: [#CellID]: #Digest
	graphDigest: #Digest
})

#CodeModeEffect: "none" | "read-only" | "scratchpad" | "live-cells"

#RawCodeModeObservation: close({
	schemaVersion: "raw-code-mode-observation/v1"
	runID:          #RunID
	attemptID:      #AttemptID
	operationID:    #OperationID
	session:        #SessionBinding
	request: close({
		operationKind:     "resolve-session" | "capture-state" | "run-focused-probe" | "apply-cell-transaction"
		requestDigest:     #Digest
		generatedCodeDigest: #Digest
	})
	transport: close({state: "returned" | "transport-error" | "timed-out"})
	execution: close({
		state:            "exited" | "raised" | "not-executed"
		exceptionType?:   string
		exceptionDigest?: #Digest
	})
	output: close({
		valueDigest?:  #Digest
		stdoutDigest?: #Digest
		stderrDigest?: #Digest
		truncated:     bool
		redacted:      bool
		shapeMatched?: bool
	})
	before?: #WorkbookStateIdentity
	after?:  #WorkbookStateIdentity
	effects: close({
		declared:                 #CodeModeEffect
		observed:                 #CodeModeEffect
		changedCellIDs:           [...#CellID]
		unexpectedChangedCellIDs: [...#CellID]
	})
	structuralResult?: "applied-as-declared" | "not-applied" | "partially-applied" | "unexpected-cell-change" | "cell-identity-changed" | "post-state-unavailable"
	artifacts:          [...close({kind: string & !="", digest: #Digest})]
	recordedAtSequence: uint
})

#PostOperationDisposition: close({
	kind:          "release"
	observationID: #ObservationID
}) | close({
	kind:          "release-redacted"
	observationID: #ObservationID
}) | close({
	kind:          "quarantine"
	observationID: #ObservationID
	reason:        string & !=""
})
