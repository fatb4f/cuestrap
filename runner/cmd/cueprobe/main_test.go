package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDecodePayloadPreservesNumbers(t *testing.T) {
	const number = "9007199254740993"
	payload, err := decodePayload(strings.NewReader(
		`{"request":{"concreteInput":` + number + `,"extensions":{"large":` + number + `}}}`,
	))
	if err != nil {
		t.Fatal(err)
	}

	concrete, ok := payload.Request.ConcreteInput.(json.Number)
	if !ok || concrete.String() != number {
		t.Fatalf("concreteInput = %T(%v), want json.Number(%s)", payload.Request.ConcreteInput, payload.Request.ConcreteInput, number)
	}
	extension, ok := payload.Request.Extensions["large"].(json.Number)
	if !ok || extension.String() != number {
		t.Fatalf("extension = %T(%v), want json.Number(%s)", payload.Request.Extensions["large"], payload.Request.Extensions["large"], number)
	}
}

func TestExecutePreservesLargeIntegerProjectionDigest(t *testing.T) {
	const number = "9007199254740993"
	moduleRoot := t.TempDir()
	if err := os.WriteFile(
		filepath.Join(moduleRoot, "value.cue"),
		[]byte("package test\nvalue: int\n"),
		0o600,
	); err != nil {
		t.Fatal(err)
	}

	payload := Payload{
		Request: Request{
			ProbeID:           "large-integer",
			Package:           "test",
			Operation:         "evaluate",
			SubjectExpression: "value",
			ConcreteInput:     json.Number(number),
		},
		Subject:    Subject{Digest: "subject", Extensions: map[string]any{}},
		ModuleRoot: moduleRoot,
		Files:      []string{"value.cue"},
	}

	observation, err := execute(payload)
	if err != nil {
		t.Fatal(err)
	}
	if observation.State != "project" {
		t.Fatalf("state = %q, want project; diagnostics = %v", observation.State, observation.Diagnostics)
	}
	want := digest([]byte(number))
	if got := observation.Facts["concreteValueDigest"]; got != want {
		t.Fatalf("concreteValueDigest = %v, want %s", got, want)
	}
}
