package bindings

import "testing"

func TestLoaderConfigCarriesPackageSelector(t *testing.T) {
	loader := &Loader{Root: "/module"}
	config := loader.loadConfig("alternate")

	if config.Dir != loader.Root {
		t.Fatalf("Dir = %q, want %q", config.Dir, loader.Root)
	}
	if config.Package != "alternate" {
		t.Fatalf("Package = %q, want alternate", config.Package)
	}
}
