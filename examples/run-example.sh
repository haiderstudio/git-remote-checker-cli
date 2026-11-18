#!/bin/sh
# Build the example repos in a temp folder and show what the
# checker says about the whole folder, about one good repo,
# and about the whole folder as JSON. The folder run fails on
# purpose, so each run is allowed to fail. The temp folder is
# removed at the end.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
sh "$HERE/make-example.sh" "$TMP"
cd "$TMP"

echo "== the whole folder : two good repos, two problems, one plain folder skipped =="
python3 "$ROOT/src/git_remote_checker.py" . || true
echo
echo "== good : one repo with a good https origin =="
python3 "$ROOT/src/git_remote_checker.py" good || true
echo
echo "== the whole folder as JSON =="
python3 "$ROOT/src/git_remote_checker.py" --json . || true
