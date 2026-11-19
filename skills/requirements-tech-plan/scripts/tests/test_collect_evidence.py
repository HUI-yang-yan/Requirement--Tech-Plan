import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "collect_evidence.py"


class CollectEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.cache_dir = self.root / "cache"
        self.env = os.environ.copy()
        self.env["PYTHONIOENCODING"] = "utf-8"
        self.env["PYTHONUTF8"] = "1"
        self._write(
            "portal/src/pages/AccountPage.tsx",
            "const message = 'account locked after login failure'\n",
        )
        self._write(
            "identity/src/routes/account_routes.py",
            "@router.post('/account/lock')\ndef lock_account(): pass\n",
        )
        self._write(
            "identity/src/services/account_service.py",
            "def lock_after_failed_login(account):\n    account.locked = True\n",
        )
        self._write(
            "identity/src/models/account.py",
            "class Account:\n    locked: bool = False\n",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write(self, relative_path, content):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _run(self, requirement, max_evidence=None, search_roots=None):
        command = [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(self.root),
            "--requirement",
            requirement,
            "--cache-dir",
            str(self.cache_dir),
        ]
        if max_evidence is not None:
            command.extend(["--max-evidence", str(max_evidence)])
        for search_root in search_roots or []:
            command.extend(["--search-root", search_root])
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            env=self.env,
        )
        return json.loads(completed.stdout)

    def test_collects_cross_layer_candidates_with_live_line_numbers(self):
        result = self._run("登录失败后锁定账号")

        self.assertEqual(
            {"frontend", "controller", "service", "domain"},
            set(result["matched_layers"]),
        )
        self.assertFalse(result["requires_deep_search"])
        self.assertTrue(result["evidence"])
        self.assertTrue(all(item["line"] > 0 for item in result["evidence"]))
        self.assertTrue(all(item["file_sha256"] for item in result["evidence"]))

    def test_invalidates_cached_evidence_when_source_changes(self):
        first = self._run("登录失败后锁定账号")
        self.assertFalse(first["cache_hit"])

        path = self.root / "identity/src/services/account_service.py"
        path.write_text("\n\ndef lock_after_failed_login(account): pass\n", encoding="utf-8")

        second = self._run("登录失败后锁定账号")
        self.assertFalse(second["cache_hit"])
        service_lines = [
            item["line"]
            for item in second["evidence"]
            if item["path"].endswith("account_service.py")
        ]
        self.assertEqual([3], service_lines)

    def test_invalidates_cached_evidence_when_size_and_mtime_are_preserved(self):
        first = self._run("登录失败后锁定账号")
        self.assertFalse(first["cache_hit"])

        path = self.root / "identity/src/services/account_service.py"
        stat = path.stat()
        content = path.read_text(encoding="utf-8")
        path.write_text(content.replace("True", "None"), encoding="utf-8")
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))

        second = self._run("登录失败后锁定账号")

        self.assertFalse(second["cache_hit"])

    def test_marks_sparse_results_for_deep_search(self):
        result = self._run("生成月度报表")

        self.assertTrue(result["requires_deep_search"])
        self.assertIn("full_repository_search", result["recommended_next_steps"])

    def test_keeps_cross_layer_evidence_when_results_are_capped(self):
        for index in range(30):
            self._write(
                f"identity/src/services/account_lock_{index}_service.py",
                "def lock_after_failed_login(account): account.locked = True\n",
            )

        result = self._run("登录失败后锁定账号", max_evidence=20)

        self.assertIn("controller", result["matched_layers"])
        self.assertIn("frontend", result["matched_layers"])
        self.assertIn("domain", result["matched_layers"])

    def test_scans_modules_without_known_project_names(self):
        self._write(
            "worker/jobs/notification_job.go",
            "func sendAccountLockedNotification() {}\n",
        )

        result = self._run("发送账号锁定通知")

        self.assertTrue(any(item["path"].startswith("worker/") for item in result["evidence"]))

    def test_explicit_module_scope_limits_search_and_has_its_own_cache(self):
        full = self._run("登录失败后锁定账号")
        scoped = self._run("登录失败后锁定账号", search_roots=["identity"])

        self.assertFalse(scoped["cache_hit"])
        self.assertEqual(["identity"], scoped["search_roots"])
        self.assertTrue(full["evidence"])
        self.assertTrue(scoped["evidence"])
        self.assertTrue(all(item["path"].startswith("identity/") for item in scoped["evidence"]))


if __name__ == "__main__":
    unittest.main()
