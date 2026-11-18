# git-remote-checker-cli

Check every git repo under a folder has an origin remote with a well-formed URL — fail CI when one does not.

[![CI](https://github.com/haiderstudio/git-remote-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/git-remote-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`git_remote_checker` walks a folder, finds every
folder that is a git repo, and checks it has an
`origin` remote whose URL is well-formed. Each
problem is reported on its own line with the repo
path, and the tool exits 1, so it can fail a CI run.
A folder with every repo in order exits 0.

- A well-formed URL is an `https://`, `http://`,
  `ssh://` or `git://` URL with a host and a path,
  or a `git@host:path` address. A bare hostname, a
  local path, a typo'd scheme such as `htp://`, an
  empty URL, or a URL with a space in it is not
  well-formed.
- A repo with no `origin` remote at all fails — even
  when it has another remote such as `upstream`.
- A folder with no `.git` is skipped, not flagged.
  Only folders that are repos are counted.
- A repo nested inside another repo is still checked.
  `.git` folders are never walked into, and directory
  links are never followed.
- A worktree or submodule whose `.git` is a file
  holding a `gitdir:` line is checked through the
  git directory it points at.
- `--json` prints the result as JSON.
- The tool reads `.git/config` directly — it needs
  no git binary.

## Who it is for

Every developer with local-only clones. A repo with
no remote — or a typo'd remote URL — cannot be
pushed, and it is found when the push fails, after
the work is done. This is the gate that catches it
at the pull request, when the fix is one line in
`.git/config`.

## What it does NOT do

- It does not check that the remote URL actually
  answers, or that you can push to it — that needs
  the network, and this tool never touches it. It
  only checks the URL is well-formed.
- It does not check any remote other than `origin`.
  An `upstream` remote on its own does not count.
- It does not check branch names, commit history, or
  whether the repo is up to date — those are
  different checks.
- It never edits a file. It only reports what it
  finds.

## How this differs

- A fresh search of GitHub on Nov 17, 2026 found 0
  results for `"git-remote-checker-cli"` and 7
  results for `git remote checker`. The closest
  rival, AlurienFlame/git-remote-checker, 0 stars,
  is a 1,391-byte interactive script from 2023 — it
  prompts for a directory, lists subfolders with no
  git repo or no remote, and has no README, no
  tests, no CI, no exit code, and no URL validation,
  so it cannot run in CI. The other hits are
  different jobs: muzammil-13/Git-Status-Checker,
  0 stars, a broader multi-check script with no CI
  claim; stealth-alpha/branchpol, 0 stars, a branch
  naming and protection policy checker.
- No rival is a tested CLI gate that checks the
  origin remote AND a well-formed URL, with
  per-line reporting and a CI exit code.

## Install

```sh
git clone https://github.com/haiderstudio/git-remote-checker-cli.git
cd git-remote-checker-cli
```

There is nothing else to install: Python 3.10 or newer,
standard library only, no dependencies.

## Usage

Check a whole folder of repos:

```sh
python3 src/git_remote_checker.py repos/
```

A folder where two repos have problems fails, with
the repo path for each one:

```sh
$ python3 src/git_remote_checker.py .
FAIL broken: remote "origin" URL "htp://github.com/haiderstudio/example.git" is not a well-formed remote URL
FAIL missing: no "origin" remote
Checked 4 repo(s), 2 problem(s) in 2 repo(s).
```

Check one repo with a good `https` origin:

```sh
$ python3 src/git_remote_checker.py good
OK — 1 repo(s) checked, every repo has an origin remote with a well-formed URL.
```

Machine-readable output:

```sh
$ python3 src/git_remote_checker.py --json .
{
  "repos": [
    {
      "path": "broken",
      "findings": [
        {
          "reason": "remote \"origin\" URL \"htp://github.com/haiderstudio/example.git\" is not a well-formed remote URL"
        }
      ],
      "error": null
    },
    {
      "path": "good",
      "findings": [],
      "error": null
    },
    {
      "path": "missing",
      "findings": [
        {
          "reason": "no \"origin\" remote"
        }
      ],
      "error": null
    },
    {
      "path": "ssh",
      "findings": [],
      "error": null
    }
  ],
  "checked": 4,
  "problems": 2
}
```

Exit codes: 0 when every repo has an origin remote
with a well-formed URL, 1 when any repo has a
problem or a `.git/config` cannot be read, 2 for a
usage error (a missing path, a file given instead
of a folder, or no git repos found).

## Examples

A repo with a `git@` origin passes — the address
form counts as well-formed, same as `https://`.
`examples/` holds a script that builds these
example repos; run it with `sh
examples/run-example.sh` and the output is saved in
[examples/sample-output.md](examples/sample-output.md).

A worktree-style repo, where `.git` is a file
holding a `gitdir:` line instead of a folder, is
checked through the git directory it points at —
it passes when that config has a good origin:

```sh
$ python3 src/git_remote_checker.py linked
OK — 1 repo(s) checked, every repo has an origin remote with a well-formed URL.
```

A repo nested inside another repo is still checked
on its own — the outer repo passing does not hide
the inner repo failing:

```sh
$ python3 src/git_remote_checker.py outer
FAIL outer/inner: remote "origin" URL "htp://bad-url" is not a well-formed remote URL
Checked 2 repo(s), 1 problem(s) in 1 repo(s).
```

## How it is tested

```sh
python3 tests/test_git_remote_checker.py
```

The tests run the real CLI on throwaway repo folders
with fake `.git/config` files, check the bundled
examples against their saved output, and check every
command quoted in this README by running it.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool is original work, written for this
repository. It builds on the Python standard library
only (`re` for the URL and config parsing). The
idea was researched against GitHub on Nov 17,
2026 — no existing tool does this exact job, as
noted above under "How this differs".
