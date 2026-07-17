#!/usr/bin/env bash
set -euo pipefail

prefix="${HOME}/.local/cuestrap"
while (($#)); do
	case "$1" in
		--prefix)
			[[ $# -ge 2 ]] || { echo "--prefix requires a value" >&2; exit 2; }
			prefix=$2
			shift 2
			;;
		*)
			echo "unknown argument: $1" >&2
			exit 2
			;;
	esac
done

root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$prefix/bin" "$prefix/share/cuestrap"
cp -a "$root/bin/." "$prefix/bin/"
cp -a "$root/share/cuestrap/." "$prefix/share/cuestrap/"
if [[ -d "$root/libexec" ]]; then
	mkdir -p "$prefix/libexec"
	cp -a "$root/libexec/." "$prefix/libexec/"
fi

echo "installed into $prefix"
echo "export PATH=$prefix/bin:\$PATH"
