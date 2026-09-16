#!/usr/bin/env python3
"""Collect fast, traceable requirement evidence with safe caching.

The cache narrows candidate files only. Callers must still read the current
source around returned locations before using them in a technical plan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable


ALIAS_GROUPS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("用户", "账号", "账户"), ("user", "account", "profile")),
    (("登录", "认证"), ("login", "auth", "authenticate")),
    (("锁定", "冻结"), ("lock", "locked", "disabled")),
    (("订单",), ("order", "orderId", "order_id")),
    (("支付", "付款"), ("payment", "pay", "paid")),
    (("优惠券",), ("coupon", "voucher")),
    (("核销",), ("redeem", "redemption", "consume")),
    (("新增", "创建"), ("create", "add", "insert")),
    (("更新", "修改", "编辑"), ("update", "modify", "edit")),
    (("查询", "搜索", "筛选"), ("query", "search", "filter")),
    (("导入", "上传"), ("import", "upload")),
    (("导出", "下载"), ("export", "download")),
    (("通知", "消息"), ("notification", "notify", "message")),
    (("配置", "设置"), ("config", "configuration", "setting")),
    (("失败", "错误", "异常"), ("fail", "failed", "error", "exception")),
    (("退款",), ("refund", "refund_id")),
    (("申诉",), ("appeal", "dispute")),
    (("审批",), ("approval", "approve", "reqContent", "reqMap")),
    (("拒绝", "驳回"), ("reject", "rejected", "refuse")),
    (("作废", "撤回", "取消"), ("cancel", "cancelled", "void", "invalid")),
    (("删除",), ("delete", "remove", "delOne")),
    (("权限",), ("permission", "authority", "role")),
    (("库存",), ("stock", "inventory", "remain")),
    (("归属", "负责人", "责任人"), ("owner", "ownerId", "responsible")),
    (("同步",), ("sync", "synchronize")),
    (("页面", "列表", "详情"), ("page", "list", "detail")),
)

SOURCE_SUFFIXES = {
    ".java",
    ".vue",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".xml",
    ".sql",
    ".yml",
    ".yaml",
    ".properties",
    ".py", ".go", ".rs", ".cs", ".kt", ".kts", ".php",
    ".rb", ".swift", ".c", ".h", ".cpp", ".hpp",
    ".svelte", ".html", ".css", ".scss", ".json", ".toml",
    ".sh", ".bash", ".ps1", ".proto", ".graphql", ".gql",
    ".tf", ".lua", ".ex", ".exs", ".dart",
}

IGNORED_PARTS = {
    ".git",
    ".idea",
    ".vscode",
    "cache",
    "dist",
    "node_modules",
    "target",
    ".venv", "venv", "__pycache__", "build", ".next",
    ".gradle", "coverage", "out", "vendor",
}

LAYER_ORDER = {
    "frontend": 0,
    "controller": 1,
    "biz": 2,
    "service": 3,
    "mapper": 4,
    "domain": 5,
    "api": 6,
    "test": 7,
    "other": 8,
}

CACHE_SCHEMA_VERSION = 4


def normalize_requirement(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def build_search_terms(requirement: str) -> list[str]:
    lowered = requirement.lower()
    terms: list[str] = []

    for triggers, aliases in ALIAS_GROUPS:
        if any(trigger.lower() in lowered for trigger in triggers):
            terms.extend(triggers)
            terms.extend(aliases)

    for word in re.findall(r"[A-Za-z][A-Za-z0-9_./-]{2,}", requirement):
        terms.append(word)
    for quoted in re.findall(r"[`\"“”']([^`\"“”']{2,80})[`\"“”']", requirement):
        terms.append(quoted)
    # Preserve short Chinese literals outside the optional alias vocabulary.
    terms.extend(term for term in re.findall(r"[\u4e00-\u9fff]{2,10}", requirement) if len(term) <= 10)

    seen: set[str] = set()
    unique: list[str] = []
    for term in terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            unique.append(term)
    return unique


def resolve_search_roots(root: Path, values: Iterable[str] | None) -> list[Path]:
    if not values:
        return [root]

    roots: list[Path] = []
    seen: set[str] = set()
    for value in values:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise ValueError(f"search root must stay inside project root: {candidate}") from error
        if not candidate.is_dir():
            raise ValueError(f"search root does not exist: {candidate}")
        key = str(candidate).lower()
        if key not in seen:
            roots.append(candidate)
            seen.add(key)
    return roots


def is_source_file(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    return path.suffix.lower() in SOURCE_SUFFIXES and not lowered_parts.intersection(IGNORED_PARTS)


def iter_source_files(root: Path, search_roots: Iterable[Path]) -> list[Path]:
    rg = shutil.which("rg")
    files: list[Path] = []
    if rg:
        targets = [str(path.relative_to(root)) for path in search_roots]
        completed = subprocess.run(
            [rg, "--files", *targets],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode in (0, 1):
            for line in completed.stdout.splitlines():
                candidate = root / line
                if candidate.is_file() and is_source_file(candidate.relative_to(root)):
                    files.append(candidate)
            return sorted(files)

    for search_root in search_roots:
        files.extend(path for path in search_root.rglob("*") if path.is_file() and is_source_file(path.relative_to(root)))
    return sorted(files)


def repository_fingerprint(root: Path, files: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        stat = path.stat()
        relative = path.relative_to(root).as_posix()
        digest.update(f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode("utf-8"))
    return digest.hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_layer(relative_path: str) -> str:
    path = "/" + relative_path.replace("\\", "/").lower()
    parts = set(path.split("/"))
    filename = path.rsplit("/", 1)[-1]
    if (parts.intersection({"test", "tests", "__tests__", "spec", "specs"})
            or filename.startswith("test_")
            or re.search(r"(?:[._](?:test|spec)|_test)\.", filename)):
        return "test"
    if (parts.intersection({"frontend", "components", "pages", "views"})
            or Path(filename).suffix in {".vue", ".jsx", ".tsx", ".svelte", ".html", ".css", ".scss"}):
        return "frontend"
    for layer, names in (
        ("controller", {"controller", "controllers", "routes", "handlers"}),
        ("biz", {"biz", "usecases"}),
        ("service", {"service", "services"}),
        ("mapper", {"mapper", "mappers", "dao", "repositories"}),
        ("domain", {"domain", "models", "entities"}),
        ("api", {"api", "dto", "schemas"}),
    ):
        if parts.intersection(names):
            return layer
    stem = Path(filename).stem
    for layer, pattern in (
        ("controller", r"(?:controller|handler|routes?|endpoint)$"),
        ("biz", r"(?:usecase|interactor|biz)$"),
        ("service", r"service$"),
        ("mapper", r"(?:repository|repo|mapper|dao)$"),
        ("domain", r"(?:model|entity|domain)$"),
        ("api", r"(?:dto|schema|request|response|api)$"),
    ):
        if re.search(pattern, stem):
            return layer
    if "/web/src/main/java/" in path:
        return "controller"
    if "/biz/src/main/java/" in path:
        return "biz"
    if "/service/src/main/java/" in path:
        return "service"
    if "/domain/src/main/java/" in path:
        return "domain"
    if "/api/src/main/java/" in path:
        return "api"
    if "/mapper/" in path or "/dao/" in path:
        return "mapper"
    return "other"


def matched_terms(line: str, terms: Iterable[str]) -> list[str]:
    lowered = line.lower()
    return [term for term in terms if term.lower() in lowered]


def collect_with_rg(root: Path, search_roots: list[Path], terms: list[str]) -> list[dict[str, object]]:
    rg = shutil.which("rg")
    if not rg or not terms:
        return collect_with_python(root, search_roots, terms)

    pattern = "|".join(re.escape(term) for term in sorted(terms, key=len, reverse=True))
    targets = [str(path.relative_to(root)) for path in search_roots]
    command = [
        rg,
        "--json",
        "-n",
        "-S",
        "--max-count",
        "8",
        "-g",
        "!**/node_modules/**",
        "-g",
        "!**/target/**",
        "-g",
        "!**/dist/**",
        pattern,
        *targets,
    ]
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise RuntimeError(completed.stderr.strip() or "rg evidence search failed")

    matches: list[dict[str, object]] = []
    seen: set[tuple[str, int]] = set()
    for raw_line in completed.stdout.splitlines():
        event = json.loads(raw_line)
        if event.get("type") != "match":
            continue
        data = event["data"]
        relative = Path(data["path"]["text"]).as_posix()
        path = root / relative
        if not path.is_file() or not is_source_file(path.relative_to(root)):
            continue
        line_number = int(data["line_number"])
        key = (relative.lower(), line_number)
        if key in seen:
            continue
        seen.add(key)
        text = data["lines"]["text"].rstrip("\r\n")
        matches.append(make_evidence(relative, line_number, text, terms))
    return matches


def collect_with_python(root: Path, search_roots: list[Path], terms: list[str]) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    for path in iter_source_files(root, search_roots):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        file_matches = 0
        for line_number, line in enumerate(lines, start=1):
            if matched_terms(line, terms):
                relative = path.relative_to(root).as_posix()
                matches.append(make_evidence(relative, line_number, line, terms))
                file_matches += 1
                if file_matches >= 8:
                    break
    return matches


def make_evidence(relative: str, line_number: int, text: str, terms: list[str]) -> dict[str, object]:
    layer = classify_layer(relative)
    hits = matched_terms(text, terms)
    layer_bonus = 2 if layer in {"controller", "biz", "service", "mapper"} else 1
    return {
        "path": relative,
        "line": line_number,
        "layer": layer,
        "matched_terms": hits,
        "score": len(hits) + layer_bonus,
        "preview": text.strip()[:300],
    }


def default_cache_dir() -> Path:
    configured = os.environ.get("REQUIREMENTS_GOVERNOR_CACHE")
    if configured:
        return Path(configured)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Codex" / "requirements-governor"
    return Path.home() / ".codex" / "cache" / "requirements-governor"


def cache_file(
    cache_dir: Path,
    root: Path,
    requirement: str,
    max_evidence: int,
    search_roots: Iterable[Path],
) -> Path:
    root_key = hashlib.sha256(str(root.resolve()).lower().encode("utf-8")).hexdigest()[:16]
    scope = "\0".join(sorted(path.relative_to(root).as_posix().lower() for path in search_roots))
    cache_key = f"{requirement}\0{max_evidence}\0{scope}\0{CACHE_SCHEMA_VERSION}"
    requirement_key = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()[:16]
    return cache_dir / root_key / f"{requirement_key}.json"


def select_balanced_evidence(evidence: list[dict[str, object]], maximum: int) -> list[dict[str, object]]:
    ordered = sorted(evidence, key=lambda item: (-int(item["score"]), str(item["path"]), int(item["line"])))
    if len(ordered) <= maximum:
        return ordered

    by_layer: dict[str, list[dict[str, object]]] = {}
    for item in ordered:
        by_layer.setdefault(str(item["layer"]), []).append(item)

    layer_count = max(1, len(by_layer))
    floor = max(1, min(8, maximum // (layer_count * 3)))
    selected: list[dict[str, object]] = []
    selected_keys: set[tuple[str, int]] = set()

    for layer in sorted(by_layer, key=lambda value: LAYER_ORDER.get(value, 99)):
        for item in by_layer[layer][:floor]:
            key = (str(item["path"]), int(item["line"]))
            selected.append(item)
            selected_keys.add(key)

    for item in ordered:
        if len(selected) >= maximum:
            break
        key = (str(item["path"]), int(item["line"]))
        if key not in selected_keys:
            selected.append(item)
            selected_keys.add(key)

    return sorted(selected, key=lambda item: (-int(item["score"]), str(item["path"]), int(item["line"])))


def calculate_confidence(layers: list[str], evidence_count: int) -> tuple[float, bool]:
    meaningful = {layer for layer in layers if layer not in {"other", "test"}}
    if not evidence_count:
        return 0.0, True
    confidence = min(0.95, 0.2 + len(meaningful) * 0.16 + min(evidence_count, 20) * 0.01)
    requires_deep_search = evidence_count < 3 or len(meaningful) < 2
    return round(confidence, 2), requires_deep_search


def collect(
    root: Path,
    requirement: str,
    cache_dir: Path,
    max_evidence: int,
    requested_search_roots: Iterable[str] | None = None,
) -> dict[str, object]:
    requirement = normalize_requirement(requirement)
    if not requirement:
        raise ValueError("requirement must not be empty")
    if not root.is_dir():
        raise ValueError(f"project root does not exist: {root}")

    search_roots = resolve_search_roots(root, requested_search_roots)
    files = iter_source_files(root, search_roots)
    fingerprint = repository_fingerprint(root, files)
    target_cache = cache_file(cache_dir, root, requirement, max_evidence, search_roots)

    if target_cache.is_file():
        cached = json.loads(target_cache.read_text(encoding="utf-8"))
        if (
            cached.get("cache_schema_version") == CACHE_SCHEMA_VERSION
            and cached.get("repository_fingerprint") == fingerprint
        ):
            cached["cache_hit"] = True
            return cached

    terms = build_search_terms(requirement)
    evidence = collect_with_rg(root, search_roots, terms)
    evidence = select_balanced_evidence(evidence, max_evidence)

    hashes: dict[str, str] = {}
    for item in evidence:
        relative = str(item["path"])
        hashes.setdefault(relative, file_sha256(root / relative))
        item["file_sha256"] = hashes[relative]

    layers = sorted({str(item["layer"]) for item in evidence}, key=lambda layer: LAYER_ORDER.get(layer, 99))
    confidence, requires_deep_search = calculate_confidence(layers, len(evidence))
    next_steps = ["read_candidate_context", "verify_live_source"]
    if requires_deep_search:
        next_steps.insert(0, "full_repository_search")

    result: dict[str, object] = {
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "requirement": requirement,
        "project_root": str(root.resolve()),
        "search_roots": [path.relative_to(root).as_posix() for path in search_roots],
        "repository_fingerprint": fingerprint,
        "cache_hit": False,
        "search_terms": terms,
        "matched_layers": layers,
        "confidence": confidence,
        "requires_deep_search": requires_deep_search,
        "recommended_next_steps": next_steps,
        "evidence": evidence,
        "usage_note": "Heuristic candidates only, not a parsed call graph. Read current source around each location before citing it in a plan.",
    }
    target_cache.parent.mkdir(parents=True, exist_ok=True)
    target_cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Project root to search, including all source modules.")
    parser.add_argument("--requirement", required=True, help="Original requirement text.")
    parser.add_argument(
        "--search-root",
        action="append",
        help="Optional project-relative module directory to search; repeat for multiple modules.",
    )
    parser.add_argument("--cache-dir", default=str(default_cache_dir()), help="Evidence cache directory.")
    parser.add_argument("--max-evidence", type=int, default=160, help="Maximum evidence rows to return.")
    args = parser.parse_args()

    try:
        result = collect(
            Path(args.root).resolve(),
            args.requirement,
            Path(args.cache_dir).resolve(),
            max(20, min(args.max_evidence, 500)),
            args.search_root,
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2) from error

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
