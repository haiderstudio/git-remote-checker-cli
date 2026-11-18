#!/bin/sh
# Build a small folder of example repos with fake .git/config
# files — no git binary needed, the checker reads .git/config
# directly. Usage: sh make-example.sh <folder>
# Creates <folder>/good (https origin), <folder>/ssh
# (git@ origin), <folder>/missing (a repo with no origin),
# <folder>/broken (a repo with a typo'd remote URL), and
# <folder>/plain (a plain folder, no .git — skipped, not
# flagged). The caller removes the folder.
set -e
DEST="$1"
mkdir -p "$DEST/good/.git" "$DEST/ssh/.git" "$DEST/missing/.git" \
    "$DEST/broken/.git" "$DEST/plain"

cat > "$DEST/good/.git/config" <<'EOF'
[core]
	repositoryformatversion = 0
[remote "origin"]
	url = https://github.com/haiderstudio/example.git
	fetch = +refs/heads/*:refs/remotes/origin/*
EOF

cat > "$DEST/ssh/.git/config" <<'EOF'
[core]
	repositoryformatversion = 0
[remote "origin"]
	url = git@github.com:haiderstudio/example.git
	fetch = +refs/heads/*:refs/remotes/origin/*
EOF

cat > "$DEST/missing/.git/config" <<'EOF'
[core]
	repositoryformatversion = 0
[remote "upstream"]
	url = https://github.com/someone-else/example.git
	fetch = +refs/heads/*:refs/remotes/upstream/*
EOF

cat > "$DEST/broken/.git/config" <<'EOF'
[core]
	repositoryformatversion = 0
[remote "origin"]
	url = htp://github.com/haiderstudio/example.git
	fetch = +refs/heads/*:refs/remotes/origin/*
EOF

echo "a plain folder, not a repo" > "$DEST/plain/notes.txt"
