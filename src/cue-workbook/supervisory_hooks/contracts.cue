package supervisoryhooks

// Closed contracts for Codex PreToolUse/PostToolUse ingress and the durable
// supervisory ledger. These records contain structural facts, never semantic
// acceptance claims.

#Digest:      =~"^sha256:[0-9a-f]{64}$"
#NonEmpty:    string & !=""
#Sequence:    uint
#Phase:       "inspect" | "probe" | "implement" | "evaluate" | "collect-evidence"
#ToolOutcome: "returned" | "reported-error" | "not-dispatched"
#ToolClass: "read-only" | "evaluation" | "workspace-mutation" | "code-mode-read" |
	"code-mode-probe" | "code-mode-mutation" | "direct-code-mode" |
	"git-mutation" | "external-mcp" | "supervisor-control" | "unknown"

#PermissionMode: "default" | "acceptEdits" | "plan" | "dontAsk" | "bypassPermissions"

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

#PreDecisionRecord: close({
	schemaVersion:         "supervisory-tool-event/v1"
	kind:                  "pre-decision"
	sequence:              #Sequence
	recordedAtNanoseconds: uint
	runID:                 #Digest
	attemptID:             #NonEmpty
	operationID:           #NonEmpty
	sessionID:             #NonEmpty
	turnID:                #NonEmpty
	phase:                 #Phase
	toolName:              #NonEmpty
	toolClass:             #ToolClass
	requestDigest:         #Digest
	repositoryStateDigest: #Digest
	decision:              "allow" | "deny"
	reason:                #NonEmpty
	coverage:              "codex-supported-hook-event"
})

#PostObservationRecord: close({
	schemaVersion:         "supervisory-tool-event/v1"
	kind:                  "post-observation"
	sequence:              #Sequence
	recordedAtNanoseconds: uint
	runID:                 #Digest
	attemptID:             #NonEmpty
	operationID:           #NonEmpty
	sessionID:             #NonEmpty
	turnID:                #NonEmpty
	phase:                 #Phase
	toolName:              #NonEmpty
	toolClass:             #ToolClass
	requestDigest:         #Digest
	responseDigest:        #Digest
	repositoryStateDigest: #Digest
	outcome:               #ToolOutcome
	redacted:              bool
	quarantined:           bool
	reason:                #NonEmpty
	coverage:              "codex-supported-hook-event"
})

#ControlTransitionRecord: close({
	schemaVersion:         "supervisory-tool-event/v1"
	kind:                  "control-transition"
	sequence:              #Sequence
	recordedAtNanoseconds: uint
	runID?:                #Digest
	attemptID?:            #NonEmpty
	operationID:           #NonEmpty
	phase:                 #Phase
	previousPhase:         #Phase
	reason:                #NonEmpty
})

#LedgerRecord: #PreDecisionRecord | #PostObservationRecord | #ControlTransitionRecord

#PendingOperation: close({
	requestDigest:         #Digest
	repositoryStateDigest: #Digest
	toolName:              #NonEmpty
	toolClass:             #ToolClass
	phase:                 #Phase
})

#SupervisorState: close({
	schemaVersion:              "supervisory-state/v1"
	phase:                      #Phase
	sequence:                   #Sequence
	sessionID?:                 #NonEmpty
	runID?:                     #Digest
	attemptID?:                 #NonEmpty
	quarantined:                bool
	quarantineReason?:          #NonEmpty
	quarantineSequence?:        #Sequence
	mutationRequiresEvaluation: bool
	lastEvaluationSequence?:    #Sequence
	pending: [#NonEmpty]:          #PendingOperation
	failedFingerprints: [#Digest]: uint & >0
})
