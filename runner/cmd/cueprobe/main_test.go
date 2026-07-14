package main

import (
	"encoding/json"
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
