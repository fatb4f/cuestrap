#!/usr/bin/env bash
set -euo pipefail

repository_root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
output=${1:-"$repository_root/dist/bundles"}
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

require() {
	command -v "$1" >/dev/null 2>&1 || { echo "required command unavailable: $1" >&2; exit 1; }
}

for command_name in bash cue curl git python3 sha256sum tar zstd; do
	require "$command_name"
done

mkdir -p "$output" "$work/download" "$work/source" "$work/stage"

lock_json="$work/toolchain-lock.json"
cue export "$repository_root/environment/toolchain.cue" -e bundle --out json > "$lock_json"
lock_digest=$(python3 - "$lock_json" <<'PY'
import hashlib
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
document = json.loads(path.read_text())
canonical = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
path.write_bytes(canonical + b"\n")
print(hashlib.sha256(canonical).hexdigest())
PY
)
lock_field() {
	python3 - "$lock_json" "$1" "$2" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text())
print(document["tools"][sys.argv[2]][sys.argv[3]])
PY
}

python_version=$(lock_field python version)
python_revision=$(lock_field python revision)
python_release=${python_revision##*/}
python_source=$(lock_field python source)
python_archive_sha256=$(lock_field python sha256)
go_version=$(lock_field go version)
go_revision=$(lock_field go revision)
go_source=$(lock_field go source)
go_archive_sha256=$(lock_field go sha256)
cue_version=$(lock_field cue version)
cue_revision=$(lock_field cue revision)
cue_source=$(lock_field cue source)
gopls_version=$(lock_field gopls version)
gopls_revision=$(lock_field gopls revision)
gopls_source=$(lock_field gopls source)
gopy_version=$(lock_field gopy version)
gopy_revision=$(lock_field gopy revision)
gopy_source=$(lock_field gopy source)

python_archive="$work/download/cpython-${python_version}+${python_release}-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
curl --fail --location --proto '=https' --tlsv1.2 \
	"$python_source" \
	-o "$python_archive"
printf '%s  %s\n' "$python_archive_sha256" "$python_archive" | sha256sum --check --status
mkdir -p "$work/python-standalone"
tar -xzf "$python_archive" -C "$work/python-standalone"

go_archive="$work/download/go${go_version}.linux-amd64.tar.gz"
curl --fail --location --proto '=https' --tlsv1.2 \
	"$go_source" -o "$go_archive"
printf '%s  %s\n' "$go_archive_sha256" "$go_archive" | sha256sum --check --status
tar -xzf "$go_archive" -C "$work"

export GOROOT="$work/go"
export PATH="$GOROOT/bin:$PATH"
export CGO_ENABLED=0
export GOOS=linux
export GOARCH=amd64
export GOTOOLCHAIN=local

checkout() {
	local url=$1 revision=$2 destination=$3
	git init --quiet "$destination"
	git -C "$destination" remote add origin "$url"
	git -C "$destination" fetch --quiet --depth=1 origin "$revision"
	git -C "$destination" checkout --quiet --detach FETCH_HEAD
	[[ $(git -C "$destination" rev-parse HEAD) == "$revision" ]]
}

checkout "$cue_source" "$cue_revision" "$work/source/cue"
checkout "$gopls_source" "$gopls_revision" "$work/source/tools"
checkout "$gopy_source" "$gopy_revision" "$work/source/gopy"

mkdir -p "$work/bin"
(cd "$work/source/cue" && go build -trimpath -buildvcs=true -o "$work/bin/cue" ./cmd/cue)
(cd "$work/source/tools/gopls" && go build -trimpath -buildvcs=true -o "$work/bin/gopls" .)
(cd "$work/source/gopy" && go build -trimpath -buildvcs=true -o "$work/bin/gopy" .)

emit_manifest() {
	local stage=$1 name=$2 version=$3 revision=$4 upstream_digest=${5:-}
	python3 - "$stage" "$name" "$version" "$revision" "$upstream_digest" <<'PY'
import hashlib
import json
import pathlib
import sys

stage = pathlib.Path(sys.argv[1])
manifest = stage / "share" / "cuestrap" / "manifest.json"
files = []
for path in sorted(stage.rglob("*")):
    if path.is_file() and path != manifest:
        payload = path.read_bytes()
        files.append({
            "path": path.relative_to(stage).as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size": len(payload),
        })
document = {
    "schema": "cuestrap.tool-bundle-manifest/v1",
    "target": {"os": "linux", "arch": "amd64"},
    "tool": {"name": sys.argv[2], "version": sys.argv[3], "revision": sys.argv[4]},
    "files": files,
}
if sys.argv[5]:
    document["upstreamArchiveSha256"] = sys.argv[5]
manifest.parent.mkdir(parents=True, exist_ok=True)
manifest.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
PY
}

make_stage() {
	local name=$1
	local stage="$work/stage/$name"
	mkdir -p "$stage/bin" "$stage/share/cuestrap"
	cp "$repository_root/tools/bundles/install.sh" "$stage/install.sh"
	chmod 0755 "$stage/install.sh"
	printf '%s\n' "$stage"
}

go_stage=$(make_stage go)
mkdir -p "$go_stage/libexec"
cp -a "$GOROOT" "$go_stage/libexec/go"
cat > "$go_stage/bin/go" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
prefix=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec "$prefix/libexec/go/bin/go" "$@"
EOF
chmod 0755 "$go_stage/bin/go"
emit_manifest "$go_stage" go "$go_version" "$go_revision" "$go_archive_sha256"

python_stage=$(make_stage python)
mkdir -p "$python_stage/libexec/python"
cp -a "$work/python-standalone/python/." "$python_stage/libexec/python/"
for executable in python python3; do
	cat > "$python_stage/bin/$executable" <<EOF
#!/usr/bin/env bash
set -euo pipefail
prefix=\$(CDPATH= cd -- "\$(dirname -- "\$0")/.." && pwd)
exec "\$prefix/libexec/python/bin/python3" "\$@"
EOF
	chmod 0755 "$python_stage/bin/$executable"
done
emit_manifest "$python_stage" python "$python_version" "$python_revision" "$python_archive_sha256"

for name in cue gopls gopy; do
	stage=$(make_stage "$name")
	cp "$work/bin/$name" "$stage/bin/$name"
	chmod 0755 "$stage/bin/$name"
	case "$name" in
		cue) emit_manifest "$stage" cue "$cue_version" "$cue_revision" ;;
		gopls) emit_manifest "$stage" gopls "$gopls_version" "$gopls_revision" ;;
		gopy) emit_manifest "$stage" gopy "$gopy_version" "$gopy_revision" ;;
	esac
done

for name in python go cue gopls gopy; do
	archive="$output/cuestrap-${name}-linux-amd64.tar.zst"
	tar --sort=name --mtime='@0' --owner=0 --group=0 --numeric-owner \
		--zstd -cf "$archive" -C "$work/stage/$name" .
	(cd "$output" && sha256sum "$(basename "$archive")" > "$(basename "$archive").sha256")
done

combined_stage=$(make_stage tools)
for name in python go cue gopls gopy; do
	cp -a "$work/stage/$name/bin/." "$combined_stage/bin/"
	if [[ -d "$work/stage/$name/libexec" ]]; then
		mkdir -p "$combined_stage/libexec"
		cp -a "$work/stage/$name/libexec/." "$combined_stage/libexec/"
	fi
done

python3 - "$combined_stage" "$lock_json" "$lock_digest" <<'PY'
import hashlib
import json
import pathlib
import sys

stage = pathlib.Path(sys.argv[1])
lock = json.loads(pathlib.Path(sys.argv[2]).read_text())
manifest = stage / "share" / "cuestrap" / "manifest.json"
files = []
for path in sorted(stage.rglob("*")):
    if path.is_file() and path != manifest:
        payload = path.read_bytes()
        files.append({
            "path": path.relative_to(stage).as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size": len(payload),
        })
document = {
    "schema": "cuestrap.combined-tool-bundle-manifest/v1",
    "lockDigest": sys.argv[3],
    "target": lock["target"],
    "tools": lock["tools"],
    "files": files,
}
manifest.parent.mkdir(parents=True, exist_ok=True)
manifest.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
PY

combined_archive="$output/cuestrap-tools-linux-amd64.tar.zst"
tar --sort=name --mtime='@0' --owner=0 --group=0 --numeric-owner \
	--zstd -cf "$combined_archive" -C "$combined_stage" .

cp "$repository_root/tools/bundles/install-release.sh" "$output/install.sh"
chmod 0755 "$output/install.sh"
python3 - "$lock_json" "$combined_archive" "$lock_digest" "$output/manifest.json" <<'PY'
import hashlib
import json
import pathlib
import sys

lock = json.loads(pathlib.Path(sys.argv[1]).read_text())
archive = pathlib.Path(sys.argv[2])
payload = archive.read_bytes()
document = {
    "schema": "cuestrap.tool-release-manifest/v1",
    "lockDigest": sys.argv[3],
    "releaseTag": f"cuestrap-tools-{sys.argv[3]}",
    "target": lock["target"],
    "tools": lock["tools"],
    "archive": {
        "name": archive.name,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
    },
}
pathlib.Path(sys.argv[4]).write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
PY

(
	cd "$output"
	sha256sum --check ./*.tar.zst.sha256
	sha256sum cuestrap-tools-linux-amd64.tar.zst manifest.json install.sh > SHA256SUMS
)

printf 'lock-digest=%s\n' "$lock_digest"
printf 'release-tag=cuestrap-tools-%s\n' "$lock_digest"
