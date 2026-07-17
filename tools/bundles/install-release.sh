#!/usr/bin/env bash
set -euo pipefail

archive_name=cuestrap-tools-linux-amd64.tar.zst
prefix=${CUESTRAP_PREFIX:-"${HOME}/.local/cuestrap"}
base_url=${CUESTRAP_RELEASE_URL:-https://github.com/fatb4f/cuestrap/releases/latest/download}
source_dir=
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)

# Prefer release assets uploaded or pre-staged beside this script. This keeps
# restricted-sandbox installation entirely offline.
if [[ -f "$script_dir/$archive_name" && -f "$script_dir/SHA256SUMS" ]]; then
	source_dir=$script_dir
fi

usage() {
	cat <<'EOF'
Usage: install.sh [--prefix DIR] [--base-url URL | --source-dir DIR]

Downloads (or reads from DIR), verifies, and installs the precompiled combined
Linux AMD64 CUEstrap tool bundle. Assets beside this script are used
automatically without network access.
EOF
}

while (($#)); do
	case "$1" in
		--prefix)
			[[ $# -ge 2 ]] || { echo "--prefix requires a value" >&2; exit 2; }
			prefix=$2
			shift 2
			;;
		--base-url)
			[[ $# -ge 2 ]] || { echo "--base-url requires a value" >&2; exit 2; }
			base_url=${2%/}
			source_dir=
			shift 2
			;;
		--source-dir)
			[[ $# -ge 2 ]] || { echo "--source-dir requires a value" >&2; exit 2; }
			source_dir=$2
			shift 2
			;;
		--help|-h)
			usage
			exit 0
			;;
		*)
			echo "unknown argument: $1" >&2
			usage >&2
			exit 2
			;;
	esac
done

if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
	echo "this bundle requires Linux on x86_64" >&2
	exit 1
fi

for command_name in sha256sum tar zstd; do
	command -v "$command_name" >/dev/null 2>&1 || {
		echo "required command unavailable: $command_name" >&2
		exit 1
	}
done

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

if [[ -n "$source_dir" ]]; then
	cp "$source_dir/$archive_name" "$source_dir/SHA256SUMS" "$work/"
else
	command -v curl >/dev/null 2>&1 || { echo "required command unavailable: curl" >&2; exit 1; }
	curl --fail --location --proto '=https' --tlsv1.2 \
		"$base_url/$archive_name" -o "$work/$archive_name"
	curl --fail --location --proto '=https' --tlsv1.2 \
		"$base_url/SHA256SUMS" -o "$work/SHA256SUMS"
fi

expected=$(awk -v name="$archive_name" '$2 == name || $2 == "*" name { print; exit }' "$work/SHA256SUMS")
[[ -n "$expected" ]] || { echo "$archive_name is absent from SHA256SUMS" >&2; exit 1; }
(cd "$work" && printf '%s\n' "$expected" | sha256sum --check --strict)

mkdir -p "$work/extracted"
tar --zstd -xf "$work/$archive_name" -C "$work/extracted"
bash "$work/extracted/install.sh" --prefix "$prefix"
