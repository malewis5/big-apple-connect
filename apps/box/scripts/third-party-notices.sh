#!/usr/bin/env bash
# Prints the license notices of everything compiled into the given programs:
# Go's standard library and every module listed in the programs' build
# information. The release workflow attaches the output to each release as
# THIRD_PARTY_NOTICES.txt, because several of those licenses (BSD, Apache)
# ask for their notice to travel with the program.
#
#   scripts/third-party-notices.sh dist/big-apple-connect-box_* > dist/THIRD_PARTY_NOTICES.txt
#
# Run it from apps/box, so `go` finds this module. It fails if a module has
# no license file, so a new dependency can't ship without its notice.
set -euo pipefail

if [ "$#" -eq 0 ]; then
  echo "usage: $0 PROGRAM..." >&2
  exit 2
fi

# Every module in any of the programs, once each.
modules=$(for program in "$@"; do go version -m "$program"; done |
  awk '$1 == "dep" { print $2 "@" $3 }' | sort -u)

section() {
  printf '%s\n' "================================================================================"
  printf '%s\n\n' "$1"
}

cat <<'EOF'
Third-party notices for the Big Apple Connect Box

The Big Apple Connect Box program is licensed under the Apache License,
Version 2.0 (see LICENSE and NOTICE in the repository). It includes the
software below, each under its own license, reproduced here as required.

EOF

section "Go standard library ($(go env GOVERSION))"
cat "$(go env GOROOT)/LICENSE"
echo

for module in $modules; do
  dir=$(go mod download -json "$module" | sed -n 's/^[[:space:]]*"Dir": "\(.*\)",$/\1/p')
  files=$(find "$dir" -maxdepth 1 -type f \( -iname 'LICENSE*' -o -iname 'LICENCE*' -o -iname 'COPYING*' -o -iname 'NOTICE*' \) | sort)
  if [ -z "$files" ]; then
    echo "no license file found for $module in $dir" >&2
    exit 1
  fi
  section "$module"
  for file in $files; do
    cat "$file"
    echo
  done
done
