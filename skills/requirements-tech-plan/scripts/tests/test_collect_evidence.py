import json
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
        self._write(
            "shirley-admin/src/views/RefundAppeal.vue",
            "const url = '/sysc/refund/appeal/cancel'\n",
        )
        self._write(
            "shirley-web/web/src/main/java/RefundController.java",
            "@PostMapping(\"/sysc/refund/appeal/cancel\")\npublic void cancelAppeal() {}\n",
        )
        self._write(
            "shirley-web/biz/src/main/java/ApprovalRefundStrategy.java",
            "class ApprovalRefundStrategy {\n    void rejectRefund() { cancelAppeal(); }\n}\n",
        )
        self._write(
            "shirley-web/domain/src/main/java/RefundAppealPO.java",
            "class RefundAppealPO { String approvalStatus; }\n",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write(self, relative_path, content):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _run(self, requirement, max_evidence=None):
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
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return json.loads(completed.stdout)

    def test_collects_cross_layer_candidates_with_live_line_numbers(self):
        result = self._run("退费拒绝时作废审批中的申诉")

        self.assertEqual(
            {"frontend", "controller", "biz", "domain"},
            set(result["matched_layers"]),
        )
        self.assertFalse(result["requires_deep_search"])
        self.assertTrue(result["evidence"])
        self.assertTrue(all(item["line"] > 0 for item in result["evidence"]))
        self.assertTrue(all(item["file_sha256"] for item in result["evidence"]))

    def test_invalidates_cached_evidence_when_source_changes(self):
        first = self._run("退费拒绝时作废审批中的申诉")
        self.assertFalse(first["cache_hit"])

        path = self.root / "shirley-web/biz/src/main/java/ApprovalRefundStrategy.java"
        path.write_text("\n\nclass ApprovalRefundStrategy { void rejectRefund() {} }\n", encoding="utf-8")

        second = self._run("退费拒绝时作废审批中的申诉")
        self.assertFalse(second["cache_hit"])
        biz_lines = [
            item["line"]
            for item in second["evidence"]
            if item["path"].endswith("ApprovalRefundStrategy.java")
        ]
        self.assertEqual([3], biz_lines)

    def test_marks_sparse_results_for_deep_search(self):
        result = self._run("库存同步")

        self.assertTrue(result["requires_deep_search"])
        self.assertIn("full_repository_search", result["recommended_next_steps"])

    def test_keeps_cross_layer_evidence_when_results_are_capped(self):
        for index in range(30):
            self._write(
                f"shirley-web/biz/src/main/java/RefundApproval{index}.java",
                "class RefundApproval { void rejectRefund() { cancelAppeal(); } }\n",
            )

        result = self._run("退费拒绝时作废审批中的申诉", max_evidence=20)

        self.assertIn("controller", result["matched_layers"])
        self.assertIn("frontend", result["matched_layers"])
        self.assertIn("domain", result["matched_layers"])


if __name__ == "__main__":
    unittest.main()
