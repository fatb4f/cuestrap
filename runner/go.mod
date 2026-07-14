module github.com/fatb4f/cuestrap/runner

go 1.25.0

require cuelang.org/go v0.18.0

// Both the gopy binding and cueprobe compile against this exact checkout.
replace cuelang.org/go => ../.deps/cue
