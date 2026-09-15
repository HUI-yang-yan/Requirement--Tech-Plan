# Requirements Tech Plan

用于 Shirley CRM 需求分析、技术方案生成和实现阶段辅助检查的 Codex 插件。

## 功能

- 识别需求中的高影响歧义并生成精简澄清问题。
- 快速召回前端、Controller、Biz、Service、Mapper、Domain、API 和测试代码位置。
- 生成技术方案文件名和建议 Git 分支名称。
- 管理需求分析、方案确认、代码修改和测试生成阶段。
- 校验技术方案中的业务逻辑、涉及表字段、代码行号和测试说明。
- 仅允许检查只读 SQL，不执行 SQL。
- 要求数据库接口和数据库之间的映射明确后才能修改相关代码。
- 默认一个需求只生成一个后端测试文件，并检查生成的测试是否被 Git 暂存。

## 目录结构

```text
requirements-governor/
├── .codex-plugin/plugin.json
├── skills/requirements-tech-plan/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── assets/technical-plan-template.md
│   ├── references/
│   └── scripts/
└── README.md
```

## 脚本

| 脚本 | 用途 |
|---|---|
| `clarify_requirement.py` | 识别需要确认的需求边界 |
| `collect_evidence.py` | 搜索并缓存跨层代码证据 |
| `suggest_names.py` | 生成技术方案文件名和 Git 分支名 |
| `requirement_session.py` | 管理需求阶段并检查源码写入权限 |
| `generate_plan.py` | 在项目根目录外生成技术方案 |
| `validate_plan.py` | 校验技术方案内容和代码行号 |
| `sql_guard.py` | 拒绝修改性 SQL |
| `db_mapping_guard.py` | 检查接口到数据库的明确映射 |
| `test_file_guard.py` | 检查测试文件数量和 Git 暂存状态 |

## 使用

显式调用：

```text
requirements-governor:requirements-tech-plan
```

技术方案、SQL 文件和其他生成文档应输出到项目根目录之外。后端默认只生成测试单元，不编译验证；测试单元需要输出完整业务链路到控制台。

## License

Internal use.
