# Security Policy

This tool runs locally, collects no data, sends nothing anywhere, and needs no API key or secret. It only reads the folders you point it at, and it never rewrites a file and never changes anything. It writes nothing except the report on standard output (and usage errors on standard error). It never fetches a URL.

It only reads `.git/config` files to find the `origin` remote URL. It never runs the git binary, never runs code found in a repo, and never follows a remote URL anywhere.

If you find a case where the tool rewrites a file, opens a URL, or reports a pass for a repo with no origin remote or a malformed remote URL, please open an issue describing the exact commands and input. Do not include any real secret in the report.
