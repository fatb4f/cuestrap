package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"runtime"
	"runtime/debug"
	"strings"

	"cuelang.org/go/cue"
	"cuelang.org/go/cue/cuecontext"
	cueerrors "cuelang.org/go/cue/errors"
	"cuelang.org/go/cue/load"
)

const (
	observationProtocol = "cuestrap.probe-observation.v0"
	cueRevision         = "806821e40fae070318600a264d311517e596353b"
	cueModuleVersion    = "v0.18.0"
)

type SourceRef struct { Path string `json:"path"` }
type Request struct {
	Schema string `json:"schema"`
	ProbeID string `json:"probeID"`
	ModuleRoot string `json:"moduleRoot"`
	Package string `json:"package"`
	Files []SourceRef `json:"files"`
	Operation string `json:"operation"`
	SubjectExpression string `json:"subjectExpression"`
	CandidateExpression *string `json:"candidateExpression"`
	ConcreteInput any `json:"concreteInput"`
	Extensions map[string]any `json:"extensions"`
}
type Subject struct {
	Protocol string `json:"protocol"`
	ProbeID string `json:"probeID"`
	Digest string `json:"digest"`
	Extensions map[string]any `json:"extensions"`
}
type Payload struct {
	Request Request `json:"request"`
	Subject Subject `json:"subject"`
	ModuleRoot string `json:"moduleRoot"`
	Files []string `json:"files"`
}
type Observation struct {
	Schema string `json:"schema"`
	ProbeID string `json:"probeID"`
	Backend string `json:"backend"`
	SubjectDigest string `json:"subjectDigest"`
	SubjectIdentity Subject `json:"subjectIdentity"`
	State string `json:"state"`
	Facts map[string]any `json:"facts"`
	Diagnostics []map[string]any `json:"diagnostics"`
	Commands []any `json:"commands"`
	Extensions map[string]any `json:"extensions"`
}

func main() {
	payload, err := decodePayload(os.Stdin)
	if err != nil { fail(err) }
	observation, err := execute(payload)
	if err != nil { fail(err) }
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(observation); err != nil { fail(err) }
}

func decodePayload(reader io.Reader) (Payload, error) {
	var payload Payload
	decoder := json.NewDecoder(reader)
	decoder.UseNumber()
	return payload, decoder.Decode(&payload)
}

func execute(payload Payload) (Observation, error) {
	observation := Observation{
		Schema: observationProtocol,
		ProbeID: payload.Request.ProbeID,
		Backend: "cueprobe",
		SubjectDigest: payload.Subject.Digest,
		SubjectIdentity: payload.Subject,
		State: "evaluate",
		Facts: map[string]any{"available": true},
		Diagnostics: []map[string]any{},
		Commands: []any{},
		Extensions: map[string]any{
			"mode": "process",
			"cueRevision": cueRevision,
			"cueModuleVersion": cueModuleVersion,
			"observedCUEModuleVersion": observedCUEModuleVersion(),
			"goVersion": runtime.Version(),
		},
	}
	ctx := cuecontext.New()
	instances := load.Instances(payload.Files, &load.Config{Dir: payload.ModuleRoot, Package: payload.Request.Package})
	if len(instances) != 1 { return observation, fmt.Errorf("expected one CUE instance, got %d", len(instances)) }
	root := ctx.BuildInstance(instances[0])
	if err := root.Err(); err != nil {
		observation.State = "load-error"
		observation.Diagnostics = diagnostics(err)
		return observation, nil
	}
	subject, err := lookup(root, payload.Request.SubjectExpression)
	if err != nil {
		observation.State = "evaluation-error"
		observation.Diagnostics = diagnostics(err)
		return observation, nil
	}
	if err := subject.Err(); err != nil {
		observation.State = "evaluation-error"
		observation.Facts["semanticBottom"] = true
		observation.Diagnostics = diagnostics(err)
		return observation, nil
	}
	switch payload.Request.Operation {
	case "evaluate":
		if payload.Request.ConcreteInput != nil {
			data, err := json.Marshal(payload.Request.ConcreteInput)
			if err != nil { return observation, err }
			concrete := ctx.CompileString(string(data), cue.Filename("concrete.json"))
			subject = subject.Unify(concrete)
		}
		if err := subject.Err(); err != nil {
			observation.Facts["semanticBottom"] = true
			observation.Diagnostics = diagnostics(err)
			return observation, nil
		}
		observation.Facts["semanticBottom"] = false
		observation.Facts["kind"] = subject.Kind().String()
		observation.Facts["incompleteKind"] = subject.IncompleteKind().String()
		data, err := subject.MarshalJSON()
		if err != nil {
			observation.State = "incomplete"
			observation.Facts["concrete"] = false
			observation.Diagnostics = diagnostics(err)
			return observation, nil
		}
		observation.State = "project"
		observation.Facts["concrete"] = true
		observation.Facts["concreteValueDigest"] = digest(data)
	case "subsumes":
		if payload.Request.CandidateExpression == nil { return observation, fmt.Errorf("subsumes requires candidateExpression") }
		candidate, err := lookup(root, *payload.Request.CandidateExpression)
		if err != nil || candidate.Err() != nil {
			if err == nil { err = candidate.Err() }
			observation.State = "materialization-error"
			observation.Diagnostics = diagnostics(err)
			return observation, nil
		}
		observation.State = "compare"
		if err := subject.Subsume(candidate); err != nil {
			observation.Facts["subsumes"] = false
			observation.Diagnostics = diagnostics(err)
		} else { observation.Facts["subsumes"] = true }
	default:
		observation.State = "unsupported-operation"
		observation.Diagnostics = append(observation.Diagnostics, map[string]any{
			"code": "unsupported-operation",
			"message": fmt.Sprintf("cueprobe does not implement %q", payload.Request.Operation),
		})
	}
	return observation, nil
}

func lookup(value cue.Value, expression string) (cue.Value, error) {
	path := cue.ParsePath(expression)
	if err := path.Err(); err != nil { return cue.Value{}, err }
	return value.LookupPath(path), nil
}
func diagnostics(err error) []map[string]any {
	if err == nil { return []map[string]any{} }
	result := []map[string]any{}
	for _, item := range cueerrors.Errors(err) {
		positions := []map[string]any{}
		for _, position := range cueerrors.Positions(item) {
			flat := position.Position()
			positions = append(positions, map[string]any{
				"filename": flat.Filename, "offset": flat.Offset, "line": flat.Line, "column": flat.Column,
			})
		}
		result = append(result, map[string]any{
			"code": "cue-diagnostic", "message": item.Error(), "raw": item.Error(),
			"path": strings.Join(item.Path(), "."), "positions": positions,
		})
	}
	return result
}
func digest(data []byte) string {
	sum := sha256.Sum256(data)
	return "sha256:" + hex.EncodeToString(sum[:])
}
func observedCUEModuleVersion() string {
	info, ok := debug.ReadBuildInfo()
	if !ok { return "unknown" }
	for _, dependency := range info.Deps {
		if dependency.Path == "cuelang.org/go" { return dependency.Version }
	}
	return "unknown"
}
func fail(err error) { fmt.Fprintln(os.Stderr, err); os.Exit(2) }
