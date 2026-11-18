# Contributing

Small, focused improvements are welcome.

- Open an issue first for anything larger than a typo or a clearer example, so the scope can be agreed before work starts.
- Never weaken the safety rules: a repo with no origin remote, or a malformed origin URL, must stay a fail, and the tool must never rewrite a file.
- Every claim in a proposed change must be verifiable: a command must be runnable, a pass or fail must be real, a badge must be true.
- Run `python3 tests/test_git_remote_checker.py` before opening a pull request. It must pass.
- Do not add placeholder text, invented features, or copied content without attribution.
- Python standard library only — no new dependency without a reason in the issue.
- Never include a real secret in an issue, a test, or an example. Every URL in this repo is a fake example address.
