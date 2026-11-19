import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
PYTHON = os.environ.get("PYTHON", sys.executable)


class WorkflowGuardsTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "project"
        self.root.mkdir()
        self.session_dir = Path(self.temp_dir.name) / "sessions"
        self.output_dir = Path(self.temp_dir.name) / "generated-docs"
        self.env = os.environ.copy()
        self.env["REQUIREMENTS_GOVERNOR_SESSION_DIR"] = str(self.session_dir)
        self.env["PYTHONIOENCODING"] = "utf-8"
        self.env["PYTHONUTF8"] = "1"

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

    def write_valid_plan(self, title, location):
        plan = self.output_dir / f"2026-09-02-{title}技术方案.md"
        plan.parent.mkdir(exist_ok=True)
        plan.write_text(
            f"""【需求分析模式：最小改动技术文档】
# {title}技术方案

## 建议 Git 分支名称

feature/20260902-account-lock

## 1. 需求目标与范围
只修改账号锁定逻辑，不新增页面或数据库。
## 2. 现有业务逻辑
当前入口调用账号服务，缺少目标限制。
## 3. 涉及项目与模块
| 项目 | 模块/职责 | 是否修改 | 修改原因 |
|---|---|---|---|
| identity | account service | 是 | 增加目标限制 |
## 4. 涉及数据存储、字段与关系
| 数据源/表/集合 | 业务用途 | 当前相关字段 | 关联关系 | 本次数据影响 | 结构/历史数据 |
|---|---|---|---|---|---|
| 不涉及 | 内存状态 | locked | account | 更新数据 | 无结构变化 |
## 5. 详细修改逻辑
当前逻辑：入口直接调用服务。
修改后逻辑：服务执行锁定规则。
修改步骤：入口调用服务并返回结果。
异常与边界：重复锁定保持幂等。
最小改动说明：只修改现有服务。
## 6. 接口与核心代码修改点
`{location}:1` 修改现有账号服务。
## 7. 页面、客户端与调用方修改点
不涉及页面，调用参数不变。
## 8. 修改前后页面与交互
修改前：账号保持原状态。
修改后：命中规则后账号锁定。
## 9. 历史数据、兼容性与影响范围
无需历史数据处理，现有调用兼容。
## 10. 测试与回归点
输入/前置条件：给定未锁定账号。
操作链路：入口到账号服务。
预期结果：账号被锁定。
控制台输出：输入、入口、状态变化和断言结果。
""",
            encoding="utf-8",
        )
        return plan

    def test_session_blocks_source_until_validated_plan_and_explicit_approval(self):
        start = self.run_script("requirement_session.py", "start", "--root", str(self.root), "--requirement", "新增账号锁定规则")
        self.assertEqual(0, start.returncode)
        session = json.loads(start.stdout)
        session_id = session["session_id"]
        source = self.root / "identity" / "src" / "account_service.py"
        source.parent.mkdir(parents=True)
        source.write_text("def lock_account(): pass\n", encoding="utf-8")

        blocked = self.run_script("requirement_session.py", "check-write", "--root", str(self.root), "--session-id", session_id, "--file", str(source))
        self.assertNotEqual(0, blocked.returncode)

        plan = self.write_valid_plan("新增账号锁定规则", "identity/src/account_service.py")
        self.assertEqual(0, self.run_script("requirement_session.py", "plan-created", "--root", str(self.root), "--session-id", session_id, "--plan-file", str(plan)).returncode)
        self.assertEqual(0, self.run_script("requirement_session.py", "validate-plan", "--root", str(self.root), "--session-id", session_id).returncode)

        still_blocked = self.run_script("requirement_session.py", "check-write", "--root", str(self.root), "--session-id", session_id, "--file", str(source))
        self.assertNotEqual(0, still_blocked.returncode)
        negated = self.run_script("requirement_session.py", "approve", "--root", str(self.root), "--session-id", session_id, "--text", "现在不可以修改")
        self.assertNotEqual(0, negated.returncode)

        plan.write_text(plan.read_text(encoding="utf-8") + "\n补充说明。\n", encoding="utf-8")
        changed = self.run_script("requirement_session.py", "approve", "--root", str(self.root), "--session-id", session_id, "--text", "按文档修改")
        self.assertNotEqual(0, changed.returncode)
        self.assertEqual(0, self.run_script("requirement_session.py", "plan-created", "--root", str(self.root), "--session-id", session_id, "--plan-file", str(plan)).returncode)
        self.assertEqual(0, self.run_script("requirement_session.py", "validate-plan", "--root", str(self.root), "--session-id", session_id).returncode)
        self.assertEqual(0, self.run_script("requirement_session.py", "approve", "--root", str(self.root), "--session-id", session_id, "--text", "按文档修改").returncode)
        allowed = self.run_script("requirement_session.py", "check-write", "--root", str(self.root), "--session-id", session_id, "--file", str(source))
        self.assertEqual(0, allowed.returncode)
        self.assertEqual("IMPLEMENTING", json.loads(allowed.stdout)["status"])
        completed = self.run_script("requirement_session.py", "complete", "--root", str(self.root), "--session-id", session_id)
        self.assertEqual(0, completed.returncode)
        self.assertEqual("COMPLETED", json.loads(completed.stdout)["status"])
        after_completion = self.run_script("requirement_session.py", "check-write", "--root", str(self.root), "--session-id", session_id, "--file", str(source))
        self.assertNotEqual(0, after_completion.returncode)

    def test_session_rejects_invalid_plan_and_unsafe_session_id(self):
        unsafe = self.run_script(
            "requirement_session.py",
            "start",
            "--root",
            str(self.root),
            "--requirement",
            "新增账号锁定规则",
            "--session-id",
            "../escape",
        )
        self.assertNotEqual(0, unsafe.returncode)

        start = self.run_script("requirement_session.py", "start", "--root", str(self.root), "--requirement", "新增账号锁定规则")
        session_id = json.loads(start.stdout)["session_id"]
        plan = self.output_dir / "2026-09-02-无效方案技术方案.md"
        plan.parent.mkdir(exist_ok=True)
        plan.write_text("plan", encoding="utf-8")
        recorded = self.run_script("requirement_session.py", "plan-created", "--root", str(self.root), "--session-id", session_id, "--plan-file", str(plan))
        self.assertEqual(0, recorded.returncode)

        validated = self.run_script("requirement_session.py", "validate-plan", "--root", str(self.root), "--session-id", session_id)

        self.assertNotEqual(0, validated.returncode)
        self.assertIn("plan validation failed", validated.stderr)

    def test_generate_plan_writes_outside_root_and_sql_guard_is_read_only(self):
        content = self.root.parent / "content.md"
        content.write_text("【需求分析模式：最小改动技术文档】\n# <准确需求名>技术方案\n\n## 建议 Git 分支名称\n\n<feature/yyyyMMdd-english-short-name 或 fix/yyyyMMdd-english-short-name>\n", encoding="utf-8")
        generated = self.run_script("generate_plan.py", "--root", str(self.root), "--requirement", "新增账号锁定规则", "--content-file", str(content), "--output-dir", str(self.output_dir))
        self.assertEqual(0, generated.returncode)
        output = Path(json.loads(generated.stdout)["file"])
        self.assertTrue(output.is_file())
        self.assertNotIn(str(self.root), str(output))
        self.assertIn("新增账号锁定规则", output.read_text(encoding="utf-8"))

        allowed = self.run_script("sql_guard.py", "--sql", "SELECT id FROM refund_rec")
        self.assertEqual(0, allowed.returncode)
        self.assertEqual("false", json.loads(allowed.stdout)["executed"].__str__().lower())
        literal = self.run_script("sql_guard.py", "--sql", "SELECT 'update status' AS message")
        self.assertEqual(0, literal.returncode)
        empty = self.run_script("sql_guard.py", "--sql", "  -- no query")
        self.assertNotEqual(0, empty.returncode)
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

    def test_validates_plan_for_cli_project_without_frontend_or_database(self):
        source = self.root / "src" / "commands" / "report.py"
        source.parent.mkdir(parents=True)
        source.write_text("def generate_report(): return 'ok'\n", encoding="utf-8")
        plan = self.output_dir / "2026-09-02-命令行报表技术方案.md"
        plan.parent.mkdir()
        plan.write_text(
            """【需求分析模式：最小改动技术文档】
# 命令行报表技术方案

## 建议 Git 分支名称

feature/20260902-cli-report

## 1. 需求目标与范围
只修改报表命令，不新增页面或数据库。
## 2. 现有业务逻辑
命令入口调用报表函数，当前缺少目标格式。
## 3. 涉及项目与模块
| 项目 | 模块/职责 | 是否修改 | 修改原因 |
|---|---|---|---|
| cli | report command | 是 | 输出目标格式 |
## 4. 涉及数据存储、字段与关系
| 数据源/表/集合 | 业务用途 | 当前相关字段 | 关联关系 | 本次数据影响 | 结构/历史数据 |
|---|---|---|---|---|---|
| 不涉及 | 内存生成结果 | 不涉及 | 不涉及 | 不涉及 | 不涉及 |
## 5. 详细修改逻辑
当前逻辑：返回旧格式。
修改后逻辑：返回目标格式。
修改步骤：从命令入口调用现有函数并转换结果。
异常与边界：空结果保持空列表。
最小改动说明：仅修改目标函数。
## 6. 接口与核心代码修改点
`src/commands/report.py:1` 修改 generate_report 的返回格式。
## 7. 页面、客户端与调用方修改点
不涉及页面；现有命令参数不变。
## 8. 修改前后页面与交互
修改前：命令输出旧格式。
修改后：命令输出目标格式。
## 9. 历史数据、兼容性与影响范围
无需历史数据处理，命令参数兼容。
## 10. 测试与回归点
输入/前置条件：给定固定报表数据。
操作链路：命令入口到报表函数。
预期结果：输出目标格式。
控制台输出：输入、入口、转换结果和断言结果。
""",
            encoding="utf-8",
        )

        result = self.run_script("validate_plan.py", str(plan), "--project-root", str(self.root))

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])

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

    def test_branch_naming_distinguishes_business_failure_from_bug_and_allows_manual_slug(self):
        feature = self.run_script(
            "suggest_names.py",
            "登录失败后锁定账号",
            "--date",
            "2026-09-02",
        )
        fixed = self.run_script(
            "suggest_names.py",
            "修复登录按钮不生效",
            "--date",
            "2026-09-02",
        )
        manual = self.run_script(
            "suggest_names.py",
            "领域专用能力",
            "--date",
            "2026-09-02",
            "--slug",
            "tenant-policy",
        )

        self.assertEqual(0, feature.returncode)
        self.assertTrue(json.loads(feature.stdout)["branch"].startswith("feature/"))
        self.assertEqual(0, fixed.returncode)
        self.assertTrue(json.loads(fixed.stdout)["branch"].startswith("fix/"))
        self.assertEqual("feature/20260902-tenant-policy", json.loads(manual.stdout)["branch"])


if __name__ == "__main__":
    unittest.main()
