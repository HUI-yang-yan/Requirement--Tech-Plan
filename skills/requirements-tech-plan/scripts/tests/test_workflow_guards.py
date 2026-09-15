import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
PYTHON = os.environ.get("PYTHON", "python")


class WorkflowGuardsTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "project"
        self.root.mkdir()
        self.session_dir = Path(self.temp_dir.name) / "sessions"
        self.output_dir = Path(self.temp_dir.name) / "generated-docs"
        self.env = os.environ.copy()
        self.env["REQUIREMENTS_GOVERNOR_SESSION_DIR"] = str(self.session_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_script(self, name, *args, check=False):
        return subprocess.run(
            [PYTHON, str(SCRIPT_DIR / name), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=self.env,
            check=check,
        )

    def test_session_blocks_source_until_validated_plan_and_explicit_approval(self):
        start = self.run_script("requirement_session.py", "start", "--root", str(self.root), "--requirement", "新增退费审批")
        self.assertEqual(0, start.returncode)
        session = json.loads(start.stdout)
        session_id = session["session_id"]
        source = self.root / "shirley-web" / "Approval.java"
        source.parent.mkdir()
        source.write_text("class Approval {}\n", encoding="utf-8")

        blocked = self.run_script("requirement_session.py", "check-write", "--root", str(self.root), "--session-id", session_id, "--file", str(source))
        self.assertNotEqual(0, blocked.returncode)

        plan = self.output_dir / "2026-09-02-新增退费审批技术方案.md"
        plan.parent.mkdir()
        plan.write_text("plan", encoding="utf-8")
        self.assertEqual(0, self.run_script("requirement_session.py", "plan-created", "--root", str(self.root), "--session-id", session_id, "--plan-file", str(plan)).returncode)
        self.assertEqual(0, self.run_script("requirement_session.py", "validate-plan", "--root", str(self.root), "--session-id", session_id).returncode)

        still_blocked = self.run_script("requirement_session.py", "check-write", "--root", str(self.root), "--session-id", session_id, "--file", str(source))
        self.assertNotEqual(0, still_blocked.returncode)
        self.assertEqual(0, self.run_script("requirement_session.py", "approve", "--root", str(self.root), "--session-id", session_id, "--text", "按文档修改").returncode)
        allowed = self.run_script("requirement_session.py", "check-write", "--root", str(self.root), "--session-id", session_id, "--file", str(source))
        self.assertEqual(0, allowed.returncode)
        self.assertEqual("IMPLEMENTING", json.loads(allowed.stdout)["status"])

    def test_generate_plan_writes_outside_root_and_sql_guard_is_read_only(self):
        content = self.root.parent / "content.md"
        content.write_text("【需求分析模式：最小改动技术文档】\n# <准确需求名>技术方案\n\n## 建议 Git 分支名称\n\n<feature/yyyyMMdd-english-short-name 或 fix/yyyyMMdd-english-short-name>\n", encoding="utf-8")
        generated = self.run_script("generate_plan.py", "--root", str(self.root), "--requirement", "新增退费审批", "--content-file", str(content), "--output-dir", str(self.output_dir))
        self.assertEqual(0, generated.returncode)
        output = Path(json.loads(generated.stdout)["file"])
        self.assertTrue(output.is_file())
        self.assertNotIn(str(self.root), str(output))
        self.assertIn("新增退费审批", output.read_text(encoding="utf-8"))

        allowed = self.run_script("sql_guard.py", "--sql", "SELECT id FROM refund_rec")
        self.assertEqual(0, allowed.returncode)
        self.assertEqual("false", json.loads(allowed.stdout)["executed"].__str__().lower())
        rejected = self.run_script("sql_guard.py", "--sql", "UPDATE refund_rec SET status = 1")
        self.assertNotEqual(0, rejected.returncode)

    def test_guards_detect_invalid_plan_and_multiple_test_files(self):
        bad_plan = self.output_dir / "bad.md"
        bad_plan.parent.mkdir()
        bad_plan.write_text("# incomplete\n", encoding="utf-8")
        result = self.run_script("validate_plan.py", str(bad_plan), "--project-root", str(self.root))
        self.assertNotEqual(0, result.returncode)
        self.assertIn("missing section", result.stdout)

        files = self.run_script("test_file_guard.py", "count", "--file", "aTest.java", "--file", "bTest.java")
        self.assertNotEqual(0, files.returncode)
        self.assertEqual(2, json.loads(files.stdout)["count"])

    def test_database_mapping_guard_requires_every_interface_mapping(self):
        interfaces = self.root.parent / "interfaces.json"
        mapping = self.root.parent / "mapping.json"
        interfaces.write_text(json.dumps(["/student/list", "/refund/list"], ensure_ascii=False), encoding="utf-8")
        mapping.write_text(json.dumps({"/student/list": "crm"}, ensure_ascii=False), encoding="utf-8")

        result = self.run_script("db_mapping_guard.py", "--interfaces-file", str(interfaces), "--mapping-file", str(mapping))

        self.assertEqual(3, result.returncode)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["requires_user_confirmation"])
        self.assertEqual(["/refund/list"], payload["missing_interfaces"])


if __name__ == "__main__":
    unittest.main()
