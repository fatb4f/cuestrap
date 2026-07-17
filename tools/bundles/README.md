# Linux AMD64 tool bundles

`environment/toolchain.cue` owns the tool versions and source revisions. The
primary distribution is the combined archive:

```text
cuestrap-tools-linux-amd64.tar.zst
```

The builder also produces five independently installable archives for caching
and maintenance:

```text
cuestrap-python-linux-amd64.tar.zst
cuestrap-go-linux-amd64.tar.zst
cuestrap-cue-linux-amd64.tar.zst
cuestrap-gopls-linux-amd64.tar.zst
cuestrap-gopy-linux-amd64.tar.zst
```

Build them from the repository root:

```bash
bash tools/bundles/build-linux-amd64.sh
```

The network-enabled build-authority environment must provide CUE so the builder
can export the canonical lock. The resulting archives do not require CUE for
installation; the CUE executable is itself one of the payloads.

Each archive contains `install.sh` and a file-level digest manifest. The Go
archive contains the complete relocatable GOROOT. The gopy archive contains the
gopy generator CLI; generated extension modules are deliberately excluded
because they are tied to a target project and Python ABI.

The Python archive contains the pinned CPython 3.14 standalone runtime. This
keeps `uv` usable as a local environment manager when sandbox network egress is
unavailable; installation does not invoke `uv python install`.

The release directory also contains `manifest.json`, `SHA256SUMS`, and a
release-level `install.sh`. The release installer verifies the combined archive
against `SHA256SUMS` before extracting it. Install from GitHub's latest release:

```bash
curl --fail --location --proto '=https' --tlsv1.2 \
  https://github.com/fatb4f/cuestrap/releases/latest/download/install.sh \
  -o install.sh
bash install.sh
```

For blocked-egress or controlled environments, download or pre-stage the
release assets and install without network access:

```bash
bash install.sh --source-dir /path/to/release-assets
```

The canonical lock digest is SHA-256 over the sorted, compact JSON export of
the CUE lock. Releases use `cuestrap-tools-<lock-digest>` as their tag.
