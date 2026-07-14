// Package bindings exposes a deliberately narrow gopy-friendly facade over CUE.
package bindings

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"runtime/debug"
	"strings"
	"sync/atomic"

	"cuelang.org/go/cue"
	"cuelang.org/go/cue/cuecontext"
	cueerrors "cuelang.org/go/cue/errors"
	"cuelang.org/go/cue/load"
)

const (
	TargetCUERevision      = "806821e40fae070318600a264d311517e596353b"
	TargetCUEModuleVersion = "v0.18.0"
	BindingProtocol        = "cuestrap.gopy-binding.v0"
)

var contextSequence atomic.Int64

type EngineIdentity struct {
	Backend                  string `json:"backend"`
	BindingProtocol          string `json:"binding_protocol"`
	CUERevision              string `json:"cue_revision"`
	CUEModuleVersion         string `json:"cue_module_version"`
	ObservedCUEModuleVersion string `json:"observed_cue_module_version"`
	GoVersion                string `json:"go_version"`
}

func Identity() *EngineIdentity {
	return &EngineIdentity{
		Backend:                  "gopy-direct",
		BindingProtocol:          BindingProtocol,
		CUERevision:              TargetCUERevision,
		CUEModuleVersion:         TargetCUEModuleVersion,
		ObservedCUEModuleVersion: observedCUEModuleVersion(),
		GoVersion:                runtime.Version(),
	}
}

func IdentityJSON() string { return mustJSON(Identity()) }

type Position struct {
	Filename string `json:"filename"`
	Offset   int    `json:"offset"`
	Line     int    `json:"line"`
	Column   int    `json:"column"`
}

type Diagnostic struct {
	Message   string     `json:"message"`
	Raw       string     `json:"raw"`
	Path      string     `json:"path"`
	Positions []Position `json:"positions"`
}

type OperationResult struct {
	OK          bool         `json:"ok"`
	Message     string       `json:"message"`
	Diagnostics []Diagnostic `json:"diagnostics"`
}

func (r *OperationResult) JSON() string { return mustJSON(r) }

type ProjectionResult struct {
	OK          bool         `json:"ok"`
	JSONValue   string       `json:"json_value"`
	Message     string       `json:"message"`
	Diagnostics []Diagnostic `json:"diagnostics"`
}

func (r *ProjectionResult) JSON() string { return mustJSON(r) }

type Context struct {
	native *cue.Context
	id     int64
}

func NewContext() *Context {
	return &Context{native: cuecontext.New(), id: contextSequence.Add(1)}
}

func (c *Context) CompileString(source, filename string) *Value {
	if filename == "" {
		filename = "unit.cue"
	}
	return &Value{native: c.native.CompileString(source, cue.Filename(filename)), owner: c}
}

func (c *Context) OpenLoader(root string) (*Loader, error) {
	absolute, err := filepath.Abs(root)
	if err != nil {
		return nil, err
	}
	info, err := os.Stat(absolute)
	if err != nil {
		return nil, err
	}
	if !info.IsDir() {
		return nil, fmt.Errorf("loader root is not a directory: %s", absolute)
	}
	return &Loader{Root: absolute, context: c}, nil
}

type Loader struct {
	Root    string
	context *Context
}

func (l *Loader) LoadPackage(pattern string) (*Value, error) {
	if pattern == "" {
		pattern = "."
	}
	return l.load([]string{pattern}, "")
}

func (l *Loader) LoadFiles(paths []string, packageName string) (*Value, error) {
	if len(paths) == 0 {
		return nil, fmt.Errorf("at least one file path is required")
	}
	return l.load(paths, packageName)
}

func (l *Loader) load(args []string, packageName string) (*Value, error) {
	instances := load.Instances(args, l.loadConfig(packageName))
	if len(instances) != 1 {
		return nil, fmt.Errorf("expected exactly one CUE instance, got %d", len(instances))
	}
	return &Value{native: l.context.native.BuildInstance(instances[0]), owner: l.context}, nil
}

func (l *Loader) loadConfig(packageName string) *load.Config {
	return &load.Config{Dir: l.Root, Package: packageName}
}

type Value struct {
	native cue.Value
	owner  *Context
}

func (v *Value) Exists() bool { return v != nil && v.native.Exists() }
func (v *Value) IsBottom() bool { return v == nil || v.native.Err() != nil }
func (v *Value) Error() string {
	if v == nil {
		return "nil CUE value"
	}
	if err := v.native.Err(); err != nil {
		return err.Error()
	}
	return ""
}
func (v *Value) Kind() string {
	if v == nil {
		return "bottom"
	}
	return v.native.Kind().String()
}
func (v *Value) IncompleteKind() string {
	if v == nil {
		return "bottom"
	}
	return v.native.IncompleteKind().String()
}
func (v *Value) DiagnosticsJSON() string {
	if v == nil {
		return mustJSON(diagnostics(fmt.Errorf("nil CUE value")))
	}
	return mustJSON(diagnostics(v.native.Err()))
}
func (v *Value) Lookup(path string) (*Value, error) {
	if err := v.ensure(); err != nil {
		return nil, err
	}
	parsed := cue.ParsePath(path)
	if err := parsed.Err(); err != nil {
		return nil, err
	}
	return &Value{native: v.native.LookupPath(parsed), owner: v.owner}, nil
}
func (v *Value) Unify(other *Value) (*Value, error) {
	if err := sameContext(v, other); err != nil {
		return nil, err
	}
	return &Value{native: v.native.Unify(other.native), owner: v.owner}, nil
}
func (v *Value) CheckSubsume(specific *Value) *OperationResult {
	if err := sameContext(v, specific); err != nil {
		return operationResult(err)
	}
	return operationResult(v.native.Subsume(specific.native))
}
func (v *Value) CheckValidate(concrete, disallowCycles bool) *OperationResult {
	if err := v.ensure(); err != nil {
		return operationResult(err)
	}
	opts := []cue.Option{}
	if concrete {
		opts = append(opts, cue.Concrete(true))
	}
	if disallowCycles {
		opts = append(opts, cue.DisallowCycles(true))
	}
	return operationResult(v.native.Validate(opts...))
}
func (v *Value) ProjectJSON() *ProjectionResult {
	if err := v.ensure(); err != nil {
		return projectionResult(nil, err)
	}
	data, err := v.native.MarshalJSON()
	return projectionResult(data, err)
}
func (v *Value) ensure() error {
	if v == nil || v.owner == nil {
		return fmt.Errorf("CUE value is not attached to a live context")
	}
	return nil
}
func sameContext(left, right *Value) error {
	if err := left.ensure(); err != nil {
		return err
	}
	if err := right.ensure(); err != nil {
		return err
	}
	if left.owner != right.owner || left.owner.id != right.owner.id {
		return fmt.Errorf("CUE values belong to different contexts")
	}
	return nil
}
func operationResult(err error) *OperationResult {
	if err == nil {
		return &OperationResult{OK: true, Diagnostics: []Diagnostic{}}
	}
	return &OperationResult{OK: false, Message: err.Error(), Diagnostics: diagnostics(err)}
}
func projectionResult(data []byte, err error) *ProjectionResult {
	if err == nil {
		return &ProjectionResult{OK: true, JSONValue: string(data), Diagnostics: []Diagnostic{}}
	}
	return &ProjectionResult{OK: false, Message: err.Error(), Diagnostics: diagnostics(err)}
}
func diagnostics(err error) []Diagnostic {
	if err == nil {
		return []Diagnostic{}
	}
	items := cueerrors.Errors(err)
	result := make([]Diagnostic, 0, len(items))
	for _, item := range items {
		positions := cueerrors.Positions(item)
		converted := make([]Position, 0, len(positions))
		for _, position := range positions {
			flat := position.Position()
			converted = append(converted, Position{Filename: flat.Filename, Offset: flat.Offset, Line: flat.Line, Column: flat.Column})
		}
		result = append(result, Diagnostic{Message: item.Error(), Raw: item.Error(), Path: strings.Join(item.Path(), "."), Positions: converted})
	}
	return result
}
func observedCUEModuleVersion() string {
	info, ok := debug.ReadBuildInfo()
	if !ok {
		return "unknown"
	}
	for _, dependency := range info.Deps {
		if dependency.Path == "cuelang.org/go" {
			return dependency.Version
		}
	}
	return "unknown"
}
func mustJSON(value any) string {
	data, err := json.Marshal(value)
	if err != nil {
		return fmt.Sprintf(`{"error":%q}`, err.Error())
	}
	return string(data)
}
