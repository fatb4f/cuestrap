# CUEstrap Tool Bundles

## Scope

These instructions govern changes under `tools/bundles/` and the corresponding tool-bundle GitHub Actions workflow.

The authoritative tool identities, source revisions, target platform, archive policy, and host requirements come from:

```text
environment/toolchain.cue
```

Do not introduce an independent version, revision, checksum, platform, or dependency declaration in shell, YAML, Python, or documentation when it can be derived from that CUE authority.

## Bundle Contract

The primary consumer artifact is:

```text
cuestrap-tools-linux-amd64.tar.zst
```

It must be a deterministic projection of the canonical toolchain lock.

A qualifying bundle must:

* target Linux AMD64 and the declared libc ABI;
* contain the exact locked tool revisions;
* install without network access;
* perform no compilation or package resolution during installation;
* verify the release archive before extraction;
* validate the embedded archive manifest after extraction;
* install through an atomic, versioned activation step;
* leave no stale files from a previous lock digest;
* emit a machine-readable environment and tool identity report.

The durable GitHub Release asset must be the exact byte sequence that passed qualification. Never rebuild a release artifact after qualification.

## Network Boundary

Network access is permitted only in the network-enabled build phase.

The following phases must work with network access disabled:

* checksum verification;
* archive extraction;
* installation;
* manifest verification;
* tool smoke tests;
* gopy binding generation and compilation;
* generated Python-extension import.

Do not add an installer fallback that silently downloads a missing compiler, Python package, Go module, or executable.

## Locked Dependencies

All required runtime and build-time dependencies must be represented in the CUE lock, including:

* Python standalone distribution;
* Go distribution;
* CUE source revision;
* gopls source revision;
* gopy source revision;
* goimports source revision;
* Python wheels required by gopy;
* offline Go modules required by generated gopy code.

Do not use floating versions, branches, `latest`, unpinned package indexes, or unresolved Go module versions.

Every downloaded archive or wheel must have a locked SHA-256 digest.

## gopy Admission

`gopy -h` is an identity probe, not a functional qualification.

The bundle is not admissible unless an offline test:

1. creates a minimal Go module;
2. runs `gopy build` using the bundled Python interpreter;
3. resolves all Go dependencies from the bundled local module proxy;
4. compiles through the available host C compiler;
5. generates a Python extension;
6. imports the generated module with the bundled Python interpreter;
7. calls a generated function and checks its result.

A missing `goimports`, pybindgen package, Go module, compiler capability, Python header, or libpython path is a bundle failure.

## Manifest Semantics

Keep archive identity and installed-state identity distinct.

The archive manifest may include installer-only files.

The installed-state manifest must include only files projected into the installation prefix. Any intentional omission must be explicit.

Manifest verification must detect:

* missing files;
* changed file sizes;
* changed file digests;
* unexpected installed files, except declared mutable paths;
* a lock digest mismatch;
* target-platform mismatch.

Do not place mutable caches inside the immutable verified projection unless they are explicitly classified as mutable.

## Installer Semantics

Installation must occur under a versioned directory keyed by the complete lock digest.

Activation must be atomic.

The installer must not:

* overwrite an active installation in place;
* retain stale files;
* write outside the selected prefix and its temporary sibling;
* modify shell configuration automatically;
* invoke a package manager;
* invoke a compiler;
* access the network in source-directory mode;
* accept an archive whose target or lock digest differs from the expected release metadata.

Retain the previous active installation until the new installation has passed verification.

## Archive Construction

Archives must use:

* sorted paths;
* epoch timestamps;
* numeric owner and group zero;
* stable executable modes;
* a bounded zstd compression configuration;
* no host-specific absolute paths;
* no untracked generated caches.

Build Go executables with:

```text
-trimpath
-buildvcs=true
-ldflags=-s -w
```

Do not use UPX or another executable packer.

Pruning a language distribution is permitted only when the complete offline qualification suite still passes.

## Required Qualification

At minimum, qualification must check:

* release checksum verification;
* archive path safety;
* complete archive-manifest verification;
* clean installation into an empty prefix;
* upgrade from a different lock digest without stale files;
* wrong-platform rejection;
* corrupted-archive rejection;
* missing-checksum rejection;
* Python version and standard-library operation;
* pip availability when declared;
* Go version and local compilation;
* gofmt operation;
* goimports operation;
* CUE evaluation;
* gopls version and startup;
* gopy help exit contract;
* complete offline gopy build and Python import;
* installed-state manifest verification;
* `cuestrap-doctor --json` schema validation.

Run the offline qualification in an environment whose network is explicitly disabled.

## Release Promotion

The build job creates and qualifies the candidate artifact.

The release job must download that exact Actions artifact and publish it without rebuilding or modifying it.

Publish:

```text
cuestrap-tools-linux-amd64.tar.zst
manifest.json
SHA256SUMS
install.sh
attestation.jsonl
cuestrap-tools-linux-amd64-offline.zip
```

The offline ZIP must contain a coherent, checksum-complete set of assets. Store the already-compressed `.tar.zst` entry without recompression.

## Change Reporting

Every bundle change report must state:

* canonical lock digest;
* release archive SHA-256;
* compressed size;
* installed size;
* file count;
* changed tool identities;
* qualification tests run;
* whether the gopy end-to-end smoke passed;
* whether the artifact was only qualified or also promoted to a release.

Do not describe an installation or qualification as passing unless it was executed in the environment being reported.
