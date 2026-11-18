#!/usr/bin/env python3
"""Check every git repo under a folder has an origin remote with a
well-formed URL.

Run: python3 src/git_remote_checker.py repos/
     python3 src/git_remote_checker.py --json repos/

A repo with no remote — or a typo'd remote URL — cannot
be pushed, and it is found when the push fails, after the
work is done. This tool walks a folder, finds every
folder that is a git repo, and checks it has an `origin`
remote whose URL is well-formed: an https://, http://,
ssh:// or git:// URL, or a git@host:path address. Each
problem is reported on its own line with the repo path,
and the tool exits 1, so it can fail a CI run. A folder
with no .git is skipped, not flagged.

The tool reads .git/config directly — it needs no git
binary. It never edits a file, never touches the
network, and reads only the folders you point it at.
"""

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

__version__ = "1.0.0"

SCHEME_URL = re.compile(
    r"^(https?|ssh|git)://[^/\s]+/\S+$")
SCP_URL = re.compile(
    r"^git@[^:/\s]+:[^\s/][^\s]*$")


def is_well_formed_url(url):
    """True when a remote URL is a well-formed remote address.

    Accepted forms: https://, http://, ssh:// and git://
    URLs with a host and a path, and the git@host:path
    address form. Anything else — a bare hostname, a
    local path, a typo'd scheme, an empty string, or a
    URL with a space in it — is not well-formed.
    """
    if not url or any(ch.isspace() for ch in url):
        return False
    return bool(SCHEME_URL.match(url) or SCP_URL.match(url))


def parse_git_config(text):
    """Read remotes out of a .git/config file.

    Returns {remote name: url} for every remote that has
    a url line. Only the first url line per remote is
    kept. Lines outside a [remote "name"] section are
    ignored, and a url line with no value is ignored.
    """
    remotes = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if line.startswith("["):
            match = re.match(r'\[\s*remote\s+"([^"]+)"\s*\]', line)
            current = match.group(1) if match else None
            continue
        if current is None or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip().lower() != "url":
            continue
        value = value.strip()
        if value and current not in remotes:
            remotes[current] = value
    return remotes


def resolve_git_dir(repo):
    """Find the git directory of one repo folder.

    A normal repo has a .git folder. A worktree or a
    submodule has a .git file holding a "gitdir: <path>"
    line, resolved against the repo folder. Returns the
    git directory as a Path, or None when the folder is
    not a git repo at all.
    """
    dotgit = Path(repo) / ".git"
    if dotgit.is_dir():
        return dotgit
    if dotgit.is_file():
        try:
            text = dotgit.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("gitdir:"):
                target = line[len("gitdir:"):].strip()
                path = Path(target)
                if not path.is_absolute():
                    path = Path(repo) / path
                return path
    return None


def check_repo(path):
    """Check one repo folder.

    Returns (findings, error): findings is a list of
    {"reason": str} in check order, and error is None or
    a string saying why the repo could not be checked
    at all.
    """
    git_dir = resolve_git_dir(path)
    if git_dir is None:
        return [], None
    config = git_dir / "config"
    try:
        text = config.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [], "cannot read .git/config: %s" % exc
    remotes = parse_git_config(text)
    if "origin" not in remotes:
        return [{"reason": 'no "origin" remote'}], None
    url = remotes["origin"]
    if not is_well_formed_url(url):
        return [{"reason": 'remote "origin" URL "%s" is not '
                           "a well-formed remote URL" % url}], None
    return [], None


def _matches_any(name, patterns):
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


def collect_repos(paths, recursive=True, exclude=None):
    """Expand CLI paths into a sorted list of repo folders.

    A folder given directly is checked itself when it is
    a repo, and walked for repos inside it. A folder
    with no .git is skipped, not flagged. .git folders
    are never walked into, and directory links are never
    followed, so a repo nested inside another repo is
    still found but its .git contents are not.
    """
    exclude = exclude or []
    found = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            raise FileNotFoundError("no such file or folder: %s" % raw)
        if path.is_file():
            raise ValueError("not a folder: %s" % raw)
        if resolve_git_dir(path) is not None:
            found.append(str(path))
        for dirpath, dirs, _files in os.walk(path, followlinks=False):
            dirs[:] = [
                d for d in dirs
                if d != ".git"
                and not _matches_any(d, exclude)
            ]
            for name in list(dirs):
                candidate = Path(dirpath) / name
                if resolve_git_dir(candidate) is not None:
                    found.append(str(candidate))
            if not recursive:
                break
    seen = set()
    unique = []
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return sorted(unique)


def format_finding(path, finding):
    """One human-readable line for one problem."""
    return "FAIL %s: %s" % (path, finding["reason"])


def run(paths, recursive=True, exclude=None, as_json=False):
    """Check paths, print the report, return the exit code."""
    try:
        repos = collect_repos(paths, recursive=recursive, exclude=exclude)
    except (FileNotFoundError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if not repos:
        print("error: no git repos found", file=sys.stderr)
        return 2
    results = []
    problems = 0
    repos_with_problems = 0
    for path in repos:
        bad, error = check_repo(path)
        count = len(bad) + (1 if error else 0)
        if count:
            problems += count
            repos_with_problems += 1
        results.append({"path": path, "findings": bad, "error": error})
    if as_json:
        print(json.dumps(
            {"repos": results, "checked": len(repos),
             "problems": problems},
            indent=2))
    else:
        for result in results:
            if result["error"]:
                print("FAIL %s: %s" % (result["path"], result["error"]))
            for finding in result["findings"]:
                print(format_finding(result["path"], finding))
        if problems:
            print("Checked %d repo(s), %d problem(s) in %d repo(s)."
                  % (len(repos), problems, repos_with_problems))
        else:
            print("OK — %d repo(s) checked, every repo has an "
                  "origin remote with a well-formed URL."
                  % len(repos))
    return 1 if problems else 0


def main(argv=None):
    """Parse arguments and run the checker."""
    parser = argparse.ArgumentParser(
        prog="git_remote_checker",
        description="Check every git repo under a folder has "
                    "an origin remote with a well-formed URL, "
                    "fail CI when one does not.")
    parser.add_argument("paths", nargs="*",
                        help="folders to walk for git repos")
    parser.add_argument("--no-recursive", action="store_true",
                        help="do not walk into subfolders")
    parser.add_argument("--exclude", action="append", default=[],
                        help="skip folders matching this pattern "
                             "(repeatable)")
    parser.add_argument("--json", action="store_true",
                        help="print the result as JSON")
    parser.add_argument("--version", action="version",
                        version="%(prog)s " + __version__)
    args = parser.parse_args(argv)
    if not args.paths:
        parser.error("give at least one folder")
    return run(args.paths,
               recursive=not args.no_recursive,
               exclude=args.exclude, as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
