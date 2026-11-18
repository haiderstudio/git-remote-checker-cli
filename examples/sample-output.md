== the whole folder : two good repos, two problems, one plain folder skipped ==
FAIL broken: remote "origin" URL "htp://github.com/haiderstudio/example.git" is not a well-formed remote URL
FAIL missing: no "origin" remote
Checked 4 repo(s), 2 problem(s) in 2 repo(s).

== good : one repo with a good https origin ==
OK — 1 repo(s) checked, every repo has an origin remote with a well-formed URL.

== the whole folder as JSON ==
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
