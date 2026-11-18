"""Tests for git_remote_checker.

Run from the repo root:

    python3 tests/test_git_remote_checker.py
"""

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src" / "git_remote_checker.py"

sys.path.insert(0, str(REPO / "src"))
import git_remote_checker as tool  # noqa: E402


def make_repo(tmp, name, url=None, extra=""):
    """Make a fake repo folder with a .git/config file.

    url=None means the config has no origin remote at all.
    Returns the repo path as a string.
    """
    repo = Path(tmp) / name
    (repo / ".git").mkdir(parents=True)
    if url is None:
        config = ("[core]\n\trepositoryformatversion = 0\n"
                  + extra)
    else:
        config = ('[core]\n\trepositoryformatversion = 0\n'
                  '[remote "origin"]\n\turl = %s\n'
                  '\tfetch = +refs/heads/*:refs/remotes/origin/*\n'
                  % url + extra)
    (repo / ".git" / "config").write_text(config)
    return str(repo)


def run_cli(args, cwd=None):
    result = subprocess.run(
        [sys.executable, str(SRC)] + args,
        cwd=cwd or str(REPO), capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


class TestIsWellFormedUrl(unittest.TestCase):
    def test_https_passes(self):
        self.assertTrue(tool.is_well_formed_url(
            "https://github.com/haiderstudio/example.git"))

    def test_http_passes(self):
        self.assertTrue(tool.is_well_formed_url(
            "http://git.example.com/team/repo.git"))

    def test_git_at_passes(self):
        self.assertTrue(tool.is_well_formed_url(
            "git@github.com:haiderstudio/example.git"))

    def test_ssh_url_passes(self):
        self.assertTrue(tool.is_well_formed_url(
            "ssh://git@github.com/haiderstudio/example.git"))

    def test_git_url_passes(self):
        self.assertTrue(tool.is_well_formed_url(
            "git://github.com/haiderstudio/example.git"))

    def test_typo_scheme_fails(self):
        self.assertFalse(tool.is_well_formed_url(
            "htp://github.com/haiderstudio/example.git"))

    def test_bare_hostname_fails(self):
        self.assertFalse(tool.is_well_formed_url(
            "github.com/haiderstudio/example.git"))

    def test_local_path_fails(self):
        self.assertFalse(tool.is_well_formed_url("/srv/git/example.git"))

    def test_empty_fails(self):
        self.assertFalse(tool.is_well_formed_url(""))

    def test_space_in_url_fails(self):
        self.assertFalse(tool.is_well_formed_url(
            "https://github.com/haider studio/example.git"))

    def test_scheme_with_no_path_fails(self):
        self.assertFalse(tool.is_well_formed_url("https://github.com"))

    def test_git_at_with_no_path_fails(self):
        self.assertFalse(tool.is_well_formed_url("git@github.com:"))


class TestParseGitConfig(unittest.TestCase):
    def test_origin_url_found(self):
        text = ('[core]\n\trepositoryformatversion = 0\n'
                '[remote "origin"]\n'
                '\turl = https://github.com/a/b.git\n')
        self.assertEqual(
            tool.parse_git_config(text),
            {"origin": "https://github.com/a/b.git"})

    def test_two_remotes_found(self):
        text = ('[remote "upstream"]\n'
                '\turl = https://github.com/u/b.git\n'
                '[remote "origin"]\n'
                '\turl = git@github.com:a/b.git\n')
        self.assertEqual(
            tool.parse_git_config(text),
            {"upstream": "https://github.com/u/b.git",
             "origin": "git@github.com:a/b.git"})

    def test_url_outside_remote_section_ignored(self):
        text = ('[core]\n\turl = https://github.com/a/b.git\n'
                '[remote "origin"]\n\tfetch = +refs/heads/*:x\n')
        self.assertEqual(tool.parse_git_config(text), {})

    def test_first_url_wins(self):
        text = ('[remote "origin"]\n'
                '\turl = https://github.com/a/first.git\n'
                '\turl = https://github.com/a/second.git\n')
        self.assertEqual(
            tool.parse_git_config(text),
            {"origin": "https://github.com/a/first.git"})

    def test_comments_and_blank_lines_ignored(self):
        text = ('# a comment\n; another comment\n\n'
                '[remote "origin"]\n'
                '\turl = https://github.com/a/b.git\n')
        self.assertEqual(
            tool.parse_git_config(text),
            {"origin": "https://github.com/a/b.git"})

    def test_empty_config(self):
        self.assertEqual(tool.parse_git_config(""), {})


class TestCheckRepo(unittest.TestCase):
    def test_https_origin_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(
                tmp, "good",
                "https://github.com/haiderstudio/example.git")
            self.assertEqual(tool.check_repo(repo), ([], None))

    def test_git_at_origin_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(
                tmp, "good", "git@github.com:haiderstudio/example.git")
            self.assertEqual(tool.check_repo(repo), ([], None))

    def test_no_origin_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(tmp, "nope", None)
            bad, error = tool.check_repo(repo)
            self.assertIsNone(error)
            self.assertEqual(len(bad), 1)
            self.assertIn('no "origin" remote', bad[0]["reason"])

    def test_other_remote_only_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "upstream-only"
            (repo / ".git").mkdir(parents=True)
            (repo / ".git" / "config").write_text(
                '[remote "upstream"]\n'
                '\turl = https://github.com/u/b.git\n')
            bad, error = tool.check_repo(str(repo))
            self.assertIsNone(error)
            self.assertEqual(len(bad), 1)
            self.assertIn('no "origin" remote', bad[0]["reason"])

    def test_malformed_url_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(
                tmp, "broken",
                "htp://github.com/haiderstudio/example.git")
            bad, error = tool.check_repo(repo)
            self.assertIsNone(error)
            self.assertEqual(len(bad), 1)
            self.assertIn("htp://github.com", bad[0]["reason"])
            self.assertIn("not a well-formed remote URL",
                          bad[0]["reason"])

    def test_missing_config_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "nocfg"
            (repo / ".git").mkdir(parents=True)
            bad, error = tool.check_repo(str(repo))
            self.assertEqual(bad, [])
            self.assertIn("cannot read .git/config", error)

    def test_git_file_with_gitdir_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "real-git"
            real.mkdir()
            (real / "config").write_text(
                '[remote "origin"]\n'
                '\turl = https://github.com/a/b.git\n')
            repo = Path(tmp) / "worktree"
            repo.mkdir()
            (repo / ".git").write_text("gitdir: ../real-git\n")
            self.assertEqual(tool.check_repo(str(repo)), ([], None))

    def test_plain_folder_is_not_a_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp) / "plain"
            plain.mkdir()
            self.assertIsNone(tool.resolve_git_dir(str(plain)))


class TestCollectRepos(unittest.TestCase):
    def test_folder_without_git_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp) / "plain"
            plain.mkdir()
            (plain / "notes.txt").write_text("hello\n")
            self.assertEqual(tool.collect_repos([tmp]), [])

    def test_walk_finds_nested_repos(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, "a",
                      "https://github.com/a/a.git")
            make_repo(tmp, "group/b",
                      "git@github.com:a/b.git")
            plain = Path(tmp) / "plain"
            plain.mkdir()
            found = tool.collect_repos([tmp])
            self.assertEqual(len(found), 2)
            self.assertTrue(any(p.endswith("a") for p in found))
            self.assertTrue(any(p.endswith("group/b") for p in found))

    def test_repo_inside_repo_is_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            outer = make_repo(tmp, "outer",
                              "https://github.com/a/outer.git")
            make_repo(outer, "inner",
                      "https://github.com/a/inner.git")
            found = tool.collect_repos([tmp])
            self.assertEqual(len(found), 2)

    def test_direct_repo_arg_is_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(tmp, "solo",
                             "https://github.com/a/solo.git")
            self.assertEqual(tool.collect_repos([repo]), [repo])

    def test_no_recursive_stops_at_top(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, "top",
                      "https://github.com/a/top.git")
            make_repo(tmp, "group/deep",
                      "https://github.com/a/deep.git")
            found = tool.collect_repos([tmp], recursive=False)
            self.assertEqual(len(found), 1)
            self.assertTrue(found[0].endswith("top"))

    def test_exclude_skips_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, "keep",
                      "https://github.com/a/keep.git")
            make_repo(tmp, "skip-me",
                      "https://github.com/a/skip.git")
            found = tool.collect_repos([tmp], exclude=["skip-*"])
            self.assertEqual(len(found), 1)
            self.assertTrue(found[0].endswith("keep"))

    def test_missing_path_raises(self):
        with self.assertRaises(FileNotFoundError):
            tool.collect_repos(["/no/such/folder/anywhere"])

    def test_file_arg_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "file.txt"
            target.write_text("x\n")
            with self.assertRaises(ValueError):
                tool.collect_repos([str(target)])


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        tmp = self.tmp.name
        make_repo(tmp, "good",
                  "https://github.com/haiderstudio/example.git")
        make_repo(tmp, "ssh",
                  "git@github.com:haiderstudio/example.git")
        make_repo(tmp, "missing", None)
        make_repo(tmp, "broken",
                  "htp://github.com/haiderstudio/example.git")
        plain = Path(tmp) / "plain"
        plain.mkdir()
        (plain / "notes.txt").write_text("not a repo\n")

    def test_whole_folder_reports_two_problems(self):
        code, out, _err = run_cli([self.tmp.name])
        self.assertEqual(code, 1)
        self.assertIn('FAIL', out)
        self.assertIn('no "origin" remote', out)
        self.assertIn("not a well-formed remote URL", out)
        self.assertIn("Checked 4 repo(s), 2 problem(s) in 2 repo(s).",
                      out)
        self.assertNotIn("plain", out)

    def test_clean_folder_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, "good",
                      "https://github.com/haiderstudio/example.git")
            code, out, _err = run_cli([tmp])
            self.assertEqual(code, 0)
            self.assertIn(
                "OK — 1 repo(s) checked, every repo has an origin "
                "remote with a well-formed URL.", out)

    def test_json_output(self):
        code, out, _err = run_cli(["--json", self.tmp.name])
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual(data["checked"], 4)
        self.assertEqual(data["problems"], 2)
        by_path = {r["path"]: r for r in data["repos"]}
        self.assertEqual(by_path[self.tmp.name + "/good"]["findings"], [])
        self.assertEqual(len(by_path[self.tmp.name + "/missing"]
                           ["findings"]), 1)

    def test_no_repos_found_is_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _out, err = run_cli([tmp])
            self.assertEqual(code, 2)
            self.assertIn("no git repos found", err)

    def test_missing_path_is_usage_error(self):
        code, _out, err = run_cli(["/no/such/folder/anywhere"])
        self.assertEqual(code, 2)
        self.assertIn("no such file or folder", err)

    def test_no_paths_is_usage_error(self):
        result = subprocess.run(
            [sys.executable, str(SRC)],
            cwd=str(REPO), capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("give at least one folder", result.stderr)

    def test_version_flag(self):
        code, out, _err = run_cli(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("1.0.0", out)

    def test_runs_from_other_folders(self):
        with tempfile.TemporaryDirectory() as other:
            code, out, _err = run_cli([self.tmp.name], cwd=other)
            self.assertEqual(code, 1)
            self.assertIn("2 problem(s)", out)


class TestExamples(unittest.TestCase):
    def test_run_example_matches_saved_output(self):
        result = subprocess.run(
            ["sh", str(REPO / "examples" / "run-example.sh")],
            cwd=str(REPO), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = (REPO / "examples" / "sample-output.md").read_text()
        self.assertEqual(result.stdout, saved)

    def test_readme_commands_are_real(self):
        readme = (REPO / "README.md").read_text()
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                ["sh", str(REPO / "examples" / "make-example.sh"), tmp],
                check=True, capture_output=True, text=True)
            good = subprocess.run(
                [sys.executable, str(SRC), "good"],
                cwd=tmp, capture_output=True, text=True)
            self.assertEqual(good.returncode, 0)
            self.assertIn(good.stdout.strip(), readme)
            whole = subprocess.run(
                [sys.executable, str(SRC), "."],
                cwd=tmp, capture_output=True, text=True)
            self.assertEqual(whole.returncode, 1)
            self.assertIn(whole.stdout.strip(), readme)
            js = subprocess.run(
                [sys.executable, str(SRC), "--json", "."],
                cwd=tmp, capture_output=True, text=True)
            self.assertEqual(js.returncode, 1)
            self.assertIn(js.stdout.strip(), readme)


class TestHygiene(unittest.TestCase):
    def _repo_files(self):
        for root, dirs, files in os.walk(REPO):
            # Skip every .git directory anywhere in the tree:
            # GitHub ships sample hooks under .git/hooks, and
            # the example fixtures may carry .git folders too.
            dirs[:] = [d for d in dirs
                       if d not in (".git", "__pycache__", "tests")]
            for name in files:
                if name.endswith(".pyc"):
                    continue
                yield Path(root) / name

    def test_no_placeholder_text(self):
        banned = ["TODO", "coming soon", "lorem", "FIXME", "XXX"]
        hits = []
        for path in self._repo_files():
            text = path.read_text(errors="ignore")
            for word in banned:
                if word in text:
                    hits.append("%s: %s" % (path.name, word))
        self.assertEqual(hits, [])

    def test_no_absolute_paths(self):
        hits = []
        for path in self._repo_files():
            text = path.read_text(errors="ignore")
            for marker in ("/home/", "/Users/", "C:\\"):
                if marker in text:
                    hits.append("%s: %s" % (path.name, marker))
        self.assertEqual(hits, [])

    def test_no_secrets(self):
        hits = []
        for path in self._repo_files():
            text = path.read_text(errors="ignore").lower()
            for marker in ("api_key", "api-key", "password", "secret=",
                           "token="):
                if marker in text:
                    hits.append("%s: %s" % (path.name, marker))
        self.assertEqual(hits, [])

    def test_stdlib_imports_only(self):
        stdlib = set(sys.stdlib_module_names)
        for target in (REPO / "src/git_remote_checker.py",
                       REPO / "tests/test_git_remote_checker.py"):
            tree = ast.parse(target.read_text())
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(a.name.split(".")[0]
                                    for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            self.assertFalse(
                imported - stdlib - {"git_remote_checker"},
                (target.name, imported))
            self.assertNotIn("yaml", imported)

    def test_no_network_use_in_src(self):
        src = (REPO / "src/git_remote_checker.py").read_text()
        for marker in ("urllib", "requests", "socket", "http.client",
                       "urlopen", "urlretrieve"):
            self.assertNotIn(marker, src, marker)

    def test_gitignore_lists_env_first(self):
        lines = (REPO / ".gitignore").read_text().splitlines()
        self.assertEqual(lines[0], ".env")

    def test_ci_runs_this_test_file(self):
        ci = (REPO / ".github/workflows/ci.yml").read_text()
        self.assertIn("tests/test_git_remote_checker.py", ci)
        self.assertIn("ubuntu-latest", ci)
        self.assertIn("3.12", ci)
        self.assertIn("actions/checkout", ci)
        self.assertIn("setup-python", ci)
        self.assertIn("push", ci)
        self.assertIn("pull_request", ci)

    def test_ci_yaml_is_well_formed(self):
        lines = (REPO / ".github/workflows/ci.yml").read_text()
        self.assertNotIn("\t", lines)
        for line in lines.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            self.assertFalse(
                line.startswith(" " * 1) and not line.startswith("  "),
                line)

    def test_hygiene_scan_skips_git_dirs_anywhere(self):
        nested = REPO / "examples" / "fake-fixture" / ".git" / "hooks"
        nested.mkdir(parents=True, exist_ok=True)
        try:
            (nested / "sample").write_text("# TODO: sample hook\n")
            seen = [p for p in self._repo_files()
                    if p.name == "sample"]
            self.assertEqual(seen, [])
        finally:
            import shutil
            shutil.rmtree(REPO / "examples" / "fake-fixture")


if __name__ == "__main__":
    unittest.main(verbosity=2)
