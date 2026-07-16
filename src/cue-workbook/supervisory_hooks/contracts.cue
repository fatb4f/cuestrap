package supervisoryhooks

// Closed contract for a phase-aware anti-churn controller. Control state is
// separate from append-only evidence; decisions never mutate either input.

#Digest:         =~"^sha256:[0-9a-f]{64}$"
#NonEmpty:       string & !=""
#Sequence:       uint & >=1
#RepositoryPath: #NonEmpty

#Activity: "inspect" | "probe" | "implement" | "evaluate" | "collect-evidence"
#Surface: "authority" | "pattern" | "kernel" | "fixture" | "probe" |
	"runner" | "workbook" | "none"
#ArtifactRole:   "owned" | "protected" | "generated" | "runtime-state" | "unclassified"
#OperationClass: "read" | "probe" | "mutation" | "evaluation" | "transition"
#ObservationChannel: "static-source" | "runtime" | "lsp" | "native-evaluation" |
	"code-mode" | "control"
#TargetID: "shell.read" | "git.read" | "git.mutation" | "cue.lsp" | "gopls.read" |
	"workspace.apply-patch" | "workspace.mutation" | "supervisor.transition" |
	"code-mode.resolve-session" | "code-mode.capture-state" |
	"code-mode.run-focused-probe" | "code-mode.apply-cell-transaction" |
	"evaluation.cue" | "evaluation.python" | "evaluation.go" | "evaluation.workbook" |
	"just.list" | "just.summary" | "just.dump" | "just.check"

#DecisionReason: "phase-relevant" | "new-observation" | "bounded-correction" |
	"unknown-operation" | "identical-retry" | "failure-cluster-exhausted" |
	"fanout-budget-exceeded" | "wrong-observation-channel" | "phase-invalid-churn" |
	"mixed-candidate-state" | "protected-artifact-mutation"
#DenialReason: "protected-artifact-mutation" | "mixed-candidate-state" |
	"wrong-observation-channel" | "identical-retry" | "failure-cluster-exhausted" |
	"fanout-budget-exceeded" | "phase-invalid-churn"
#ToolOutcome:    "returned" | "reported-error" | "not-dispatched" | "reducer-error"
#PermissionMode: "default" | "acceptEdits" | "plan" | "dontAsk" | "bypassPermissions"

#DenialPrecedence: [
	"protected-artifact-mutation",
	"mixed-candidate-state",
	"wrong-observation-channel",
	"identical-retry",
	"failure-cluster-exhausted",
	"fanout-budget-exceeded",
	"phase-invalid-churn",
]

#Scope: close({
	activity:       #Activity
	surface:        #Surface
	ownedPaths:     *[] | [...#RepositoryPath]
	allowedTargets: [...#TargetID]
})

#DefaultInspectScope: close({
	activity:   "inspect"
	surface:    "none"
	ownedPaths: []
	allowedTargets: [
		"shell.read",
		"git.read",
		"cue.lsp",
		"gopls.read",
		"code-mode.resolve-session",
		"code-mode.capture-state",
	]
})

#Budgets: close({
	maximumFailureClusterCorrections: *2 | int & >=1 & <=10
	maximumObservationFanout:         *64 | int & >=1 & <=10000
})

#Guidance: close({
	retryRequiresAny:   *[] | [...#NonEmpty]
	recommendedTargets: *[] | [...#TargetID]
})

#ProgressEvidence: close({
	requestChanged:        bool
	resultChanged:         bool
	relevantStateChanged:  bool
	candidateChanged:      bool
	resolvedQuestionIDs:   *[] | [...#NonEmpty]
	introducedQuestionIDs: *[] | [...#NonEmpty]
})

#CanonicalOperation: close({
	targetID:           #TargetID
	operationClass:     #OperationClass
	requestDigest:      #Digest
	mutating:           *false | bool
	targetPaths:        *[] | [...string]
	artifactRoles:      *[] | [...#ArtifactRole]
	observationChannel: #ObservationChannel
	fanout:             *1 | int & >=1
	candidateDigest:    *null | #Digest
	questionIDs:        *[] | [...#NonEmpty]
})

#Classification: close({recognized: false, operation: null}) | close({
	recognized: true
	operation:  #CanonicalOperation
})

#ObservationSummary: close({
	targetID:            #TargetID
	activity:            #Activity
	requestDigest:       #Digest
	relevantStateDigest: #Digest
	resultDigest:        #Digest
	candidateDigest:     *null | #Digest
	failureSignature:    *null | #Digest
	requiredObservationChannel: *null | #ObservationChannel
	outcome:             #ToolOutcome
})

#LedgerProjection: close({
	observations:               *[] | [...#ObservationSummary]
	activeCandidateDigest:      *null | #Digest
	activeFailureSignature:     *null | #Digest
	requiredObservationChannel: *null | #ObservationChannel
	unresolvedQuestionIDs:      *[] | [...#NonEmpty]
})

#Decision: close({
	action:            "approve" | "deny"
	reason:            #DecisionReason
	matchedPredicates: *[] | [...#DenialReason]
	guidance:          *null | #Guidance
})

#CompletedOperation: close({
	scope:               #Scope
	operation:           #CanonicalOperation
	relevantStateDigest: #Digest
	toolName:            #NonEmpty
})

#ObservedResult: close({
	outcome:               #ToolOutcome
	resultClass:           #NonEmpty
	resultDigest:          #Digest
	requiredObservationChannel: *null | #ObservationChannel
	resolvedQuestionIDs:   *[] | [...#NonEmpty]
	introducedQuestionIDs: *[] | [...#NonEmpty]
})

#ReducerResult: close({
	observation:    #ObservationSummary
	progress:       #ProgressEvidence
	evidenceStatus: #NonEmpty
	guidance:       *null | #Guidance
})

#CommonHookInput: {
	session_id:      #NonEmpty
	transcript_path: string | null
	cwd:             #NonEmpty
	hook_event_name: #NonEmpty
	model:           #NonEmpty
	turn_id:         #NonEmpty
	permission_mode: #PermissionMode
}

#PreToolUseInput: close({
	#CommonHookInput
	hook_event_name: "PreToolUse"
	tool_name:       #NonEmpty
	tool_use_id:     #NonEmpty
	tool_input:      _
})

#PostToolUseInput: close({
	#CommonHookInput
	hook_event_name: "PostToolUse"
	tool_name:       #NonEmpty
	tool_use_id:     #NonEmpty
	tool_input:      _
	tool_response:   _
})

#PendingOperation: close({
	toolName:            #NonEmpty
	scope:               #Scope
	operation:           #CanonicalOperation
	relevantStateDigest: #Digest
})

#SupervisorStateV2: close({
	schemaVersion:     *"supervisory-state/v2" | "supervisory-state/v2"
	version:           *2 | 2
	scope:             *#DefaultInspectScope | #Scope
	budgets:           *#Budgets | #Budgets
	sessionID:         *null | #NonEmpty
	runID:             *null | #Digest
	attemptID:         *null | #NonEmpty
	pending:           *{} | {[#NonEmpty]: #PendingOperation}
	legacyStateDigest: *null | #Digest
})

#V1PendingOperation: close({
	requestDigest:         #Digest
	repositoryStateDigest: #Digest
	toolName:              #NonEmpty
	toolClass:             #NonEmpty
	phase:                 #Activity
})

#SupervisorStateV1: close({
	schemaVersion:              *"supervisory-state/v1" | "supervisory-state/v1"
	phase:                      *"inspect" | #Activity
	sequence:                   *0 | uint
	sessionID:                  *null | #NonEmpty
	runID:                      *null | #Digest
	attemptID:                  *null | #NonEmpty
	quarantined:                *false | bool
	quarantineReason:           *null | #NonEmpty
	quarantineSequence:         *null | uint
	mutationRequiresEvaluation: *false | bool
	lastEvaluationSequence:     *null | uint
	pending:                    *{} | {[#NonEmpty]: #V1PendingOperation}
	failedFingerprints:         *{} | {[#Digest]: int & >0}
})

#EvidenceBase: {
	schemaVersion:         "supervisory-evidence/v2"
	kind:                  #NonEmpty
	sequence:              #Sequence
	recordedAtNanoseconds: uint
	operationID:           #NonEmpty
}

#PreDecisionRecord: close({
	#EvidenceBase
	kind:                "pre-decision"
	runID:               #Digest
	attemptID:           #NonEmpty
	sessionID:           #NonEmpty
	turnID:              #NonEmpty
	scope:               #Scope
	toolName:            #NonEmpty
	recognized:          true
	targetID:            #TargetID
	requestDigest:       #Digest
	relevantStateDigest: #Digest
	candidateDigest:     *null | #Digest
	action:              "approve" | "deny"
	reason:              #DecisionReason
	matchedPredicates:   [...#DenialReason]
	coverage:            "codex-supported-hook-event"
})

#UnclassifiedObservationRecord: close({
	#EvidenceBase
	kind:          "unclassified-observation"
	stage:         "pre" | "post"
	sessionID:     #NonEmpty
	turnID:        #NonEmpty
	toolName:      #NonEmpty
	requestDigest: #Digest
	resultDigest:  *null | #Digest
	outcome:       *null | #ToolOutcome
})

#PostObservationRecord: close({
	#EvidenceBase
	kind:                "post-observation"
	runID:               #Digest
	attemptID:           #NonEmpty
	sessionID:           #NonEmpty
	turnID:              #NonEmpty
	scope:               #Scope
	toolName:            #NonEmpty
	targetID:            #TargetID
	requestDigest:       #Digest
	relevantStateDigest: #Digest
	resultDigest:        #Digest
	candidateDigest:     *null | #Digest
	failureSignature:    *null | #Digest
	requiredObservationChannel: *null | #ObservationChannel
	outcome:             #ToolOutcome
	evidenceStatus:      #NonEmpty
	progress:            #ProgressEvidence
	guidance:            *null | #Guidance
	coverage:            "codex-supported-hook-event"
})

#ControlTransitionRecord: close({
	#EvidenceBase
	kind:          "control-transition"
	runID:         *null | #Digest
	attemptID:     *null | #NonEmpty
	previousScope: #Scope
	scope:         #Scope
	reason:        #NonEmpty
})

#ReductionErrorRecord: close({
	#EvidenceBase
	kind:          "reduction-error"
	sessionID:     #NonEmpty
	turnID:        #NonEmpty
	toolName:      #NonEmpty
	requestDigest: #Digest
	errorDigest:   #Digest
})

#EvidenceRecord: #PreDecisionRecord | #UnclassifiedObservationRecord |
	#PostObservationRecord | #ControlTransitionRecord | #ReductionErrorRecord

// Shared fixture envelopes used by Python tests and `cue vet`.
#VocabularyFixture: close({
	activities:       [...#Activity]
	surfaces:         [...#Surface]
	artifactRoles:    [...#ArtifactRole]
	targetIDs:        [...#TargetID]
	decisionReasons:  [...#DecisionReason]
	denialPrecedence: #DenialPrecedence
})

#StateFixtureV1: #SupervisorStateV1
#StateFixtureV2: #SupervisorStateV2
