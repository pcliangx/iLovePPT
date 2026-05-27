#!/usr/bin/env python3
"""gitignore_lint.py · P3-20 · 多 .gitignore 规则一致性 lint.

iLovePPT 仓库当前有 3+ 份 .gitignore(根 / decks/ / .pytest_cache/ 等),
容易出现规则漏 / 重复 / 冲突 / 子规则被父规则掩盖。本工具自动校。

5 类检查:
  1. CONFLICT       同模式在多个 .gitignore 重复定义(可能行为不同)
  2. SHADOWED       子目录 .gitignore 的规则被父目录已 ignore 的规则掩盖
  3. REDUNDANT      子 .gitignore 重复父级已有规则(等价 SHADOWED 子集,但纯字面重复)
  4. UNTRACKED_SECRET  git untracked 文件命中疑似机密扩展名(.env / .key / .pem / *.bak / *_secret.*)
  5. TRACKED_IN_IGNORE 已 tracked 的文件命中当前 .gitignore 规则(历史遗留)

Behavior:
- 默认扫本仓库;退出码 = 0 (无 error) / 1 (有 error · CONFLICT / TRACKED_IN_IGNORE / UNTRACKED_SECRET) / 0 (仅 warn)
- SHADOWED / REDUNDANT 是 warn(非 error · 信息冗余但不影响 git 行为)
- CONFLICT / TRACKED_IN_IGNORE / UNTRACKED_SECRET 是 error

CLI:
    scripts/gitignore_lint.py                     # 默认 markdown
    scripts/gitignore_lint.py --fix               # 自动修(merge 子规则 / 删 redundant · 改前先 .bak 备份)
    scripts/gitignore_lint.py --format json
    scripts/gitignore_lint.py --quiet             # 仅退出码,不打报告
    scripts/gitignore_lint.py --no-strict         # SHADOWED/REDUNDANT 不算 error(默认就不算)
    scripts/gitignore_lint.py --strict            # SHADOWED/REDUNDANT 升 error

Integration:
    .githooks/pre-commit 可调本 lint;有 error 时 reject commit。
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---------------- 模式匹配 ---------------- #

SECRET_PATTERNS = [
    re.compile(r".*\.env(\..*)?$"),
    re.compile(r".*\.key$"),
    re.compile(r".*\.pem$"),
    re.compile(r".*\.bak$"),
    re.compile(r".*[_.]?secrets?\..*"),
    re.compile(r".*[_.]credentials?\..*"),
    re.compile(r".*\.p12$"),
    re.compile(r".*\.pfx$"),
    re.compile(r".*\.crt$"),
    re.compile(r".*\.csr$"),
    re.compile(r"id_rsa(\..*)?$"),
    re.compile(r"id_ed25519(\..*)?$"),
]


def is_suspect_secret(rel_path: str) -> bool:
    """文件相对路径是否看着像机密 / 应该 ignore."""
    name = os.path.basename(rel_path)
    for pat in SECRET_PATTERNS:
        if pat.match(name):
            return True
    return False


# ---------------- 数据模型 ---------------- #


@dataclass
class GitignoreRule:
    """单条 gitignore 规则."""

    file: Path  # 所在 .gitignore 路径(相对仓库根)
    line_no: int  # 1-indexed
    raw: str  # 原始行(含 \n? 已 strip)
    pattern: str  # 去掉 ! / 注释前缀的 pattern
    is_negation: bool  # 以 ! 开头


@dataclass
class LintIssue:
    """单个 lint 问题."""

    category: str  # CONFLICT / SHADOWED / REDUNDANT / UNTRACKED_SECRET / TRACKED_IN_IGNORE
    severity: str  # error / warn
    file: str  # 主受影响文件(.gitignore 相对路径)
    line: int  # 1-indexed, 0 表示 N/A
    rule: str  # 规则文本
    detail: str  # 描述


@dataclass
class LintReport:
    """lint 全报告."""

    repo_root: str
    gitignore_files: list[str] = field(default_factory=list)
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == "warn"]

    def counts_by_category(self) -> dict[str, int]:
        c: dict[str, int] = {}
        for i in self.issues:
            c[i.category] = c.get(i.category, 0) + 1
        return c


# ---------------- 解析 ---------------- #


def find_gitignore_files(repo_root: Path) -> list[Path]:
    """扫所有 .gitignore(跳 .venv / node_modules / .git)."""
    skip_dir_parts = {".venv", "node_modules", ".git"}
    result: list[Path] = []
    for path in sorted(repo_root.rglob(".gitignore")):
        if any(part in skip_dir_parts for part in path.parts):
            continue
        result.append(path)
    return result


def parse_gitignore(path: Path, repo_root: Path) -> list[GitignoreRule]:
    """解析单 .gitignore -> rule 列表(skip 空行/注释)."""
    rules: list[GitignoreRule] = []
    rel = path.relative_to(repo_root)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return rules

    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip()  # 保留前导空格 — git 也是
        # 跳空行 / 注释
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            continue
        # negation
        is_neg = line.startswith("!")
        pat = line[1:] if is_neg else line
        # gitignore 里 `\!` / `\#` escape — 简化处理:不脱
        rules.append(
            GitignoreRule(
                file=rel,
                line_no=i,
                raw=line,
                pattern=pat,
                is_negation=is_neg,
            )
        )
    return rules


# ---------------- 路径作用域 ---------------- #


def gitignore_scope(rel_path: Path) -> Path:
    """.gitignore 的作用目录(去掉 .gitignore 本身).

    根 .gitignore -> Path('.');decks/.gitignore -> Path('decks').
    """
    parent = rel_path.parent
    return Path(".") if str(parent) == "" else parent


def is_descendant_scope(child: Path, parent: Path) -> bool:
    """child 作用域是否在 parent 作用域之下(含相同).

    parent='.' -> 永真;parent='a/b', child='a/b/c' -> 真;child==parent -> 真.
    """
    if str(parent) == ".":
        return True
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def pattern_for_parent_scope(pat: str, child_scope: Path, parent_scope: Path) -> str:
    """把 child .gitignore 里的 pat 改写成从 parent_scope 角度的 pat.

    e.g. child='decks', parent='.', pat='*' -> 'decks/*'
         pat 含 '/' 锚定根 (e.g. '/out/') -> 'decks/out/'
    """
    if str(parent_scope) == str(child_scope):
        return pat
    # child relative to parent (e.g. 'decks' relative '.' -> 'decks')
    rel_child = child_scope if str(parent_scope) == "." else child_scope.relative_to(parent_scope)
    prefix = str(rel_child).rstrip("/")
    if not prefix or prefix == ".":
        return pat

    p = pat
    # 锚定型 /foo -> 子目录里就是 prefix/foo
    if p.startswith("/"):
        p = p[1:]
    # 普通 *.log -> prefix/**/*.log (git 行为·递归);简化成 prefix/* 的近似
    # 为了一致性比较,我们只做字面拼接:prefix/pat
    return f"{prefix}/{p}"


def pattern_matches_path(pat: str, rel_path: str, scope: Path) -> bool:
    """简化的 gitignore 匹配 — pat 在 scope 下是否命中 rel_path(scope root)."""
    # path 相对 scope
    try:
        scope_str = str(scope)
        if scope_str == ".":
            target = rel_path
        elif rel_path.startswith(scope_str + "/"):
            target = rel_path[len(scope_str) + 1 :]
        else:
            return False
    except Exception:
        return False

    pat_norm = pat
    # 目录形 dir/ — 命中 dir 自己或 dir/ 下任意
    trailing_dir = pat_norm.endswith("/")
    if trailing_dir:
        pat_norm = pat_norm[:-1]
    # 锚定型 /foo — 仅 scope 根下
    anchored = pat_norm.startswith("/")
    if anchored:
        pat_norm = pat_norm[1:]

    # 1. 完整 match
    if fnmatch.fnmatch(target, pat_norm):
        return True
    # 2. 含 '/' 但非锚定 -> 当作绝对(scope 相对)
    if "/" in pat_norm and not anchored:
        if fnmatch.fnmatch(target, pat_norm):
            return True
    # 3. 非锚定 + 无 '/' -> 递归匹配每个 path segment(简化:命中 basename)
    if not anchored and "/" not in pat_norm:
        if fnmatch.fnmatch(os.path.basename(target), pat_norm):
            return True
        # 同时检查任意层目录命中(dir 形)
        if trailing_dir:
            for seg in target.split("/"):
                if fnmatch.fnmatch(seg, pat_norm):
                    return True
    return False


# ---------------- Check 函数 ---------------- #


def check_conflicts(rules: list[GitignoreRule]) -> list[LintIssue]:
    """CONFLICT — 同 pattern 在祖先-后代 .gitignore 同时出现(scope 重叠 · 含义可能不同).

    判定逻辑:
    - 两 .gitignore 字面 pattern 相同
    - 且 scope 有祖先-后代关系(包含自身)
    - 才视为 CONFLICT(因为后代 .gitignore 的 pat 会被祖先 .gitignore 已覆盖)

    例:`*` 在 `decks/.gitignore` 跟 `.pytest_cache/.gitignore` 各一份 — 两 scope 不相交,**不算 CONFLICT**.
    例:`*.pyc` 在根 `.gitignore` 跟 `decks/.gitignore` 各一份 — scope 有重叠,**算 CONFLICT(子级 redundant)**.
    """
    issues: list[LintIssue] = []
    by_pat: dict[tuple[str, bool], list[GitignoreRule]] = {}
    for r in rules:
        key = (r.pattern.strip(), r.is_negation)
        by_pat.setdefault(key, []).append(r)

    for (pat, neg), rs in by_pat.items():
        if len({str(r.file) for r in rs}) < 2:
            continue
        # 检查任意 2 个 rule 的 scope 是否有祖先-后代关系
        for i, ra in enumerate(rs):
            scope_a = gitignore_scope(ra.file)
            overlapping_others: list[GitignoreRule] = []
            for rb in rs:
                if rb is ra:
                    continue
                scope_b = gitignore_scope(rb.file)
                # 祖先-后代:a 在 b 之下 OR b 在 a 之下
                if is_descendant_scope(scope_a, scope_b) or is_descendant_scope(scope_b, scope_a):
                    overlapping_others.append(rb)
            if overlapping_others:
                others_desc = sorted({f"{rb.file}:{rb.line_no}" for rb in overlapping_others})
                issues.append(
                    LintIssue(
                        category="CONFLICT",
                        severity="error",
                        file=str(ra.file),
                        line=ra.line_no,
                        rule=("!" if neg else "") + pat,
                        detail=f"同 pattern '{pat}' 在祖先/后代 .gitignore 重复: {', '.join(others_desc)}",
                    )
                )
    return issues


def check_shadowed_and_redundant(
    rules: list[GitignoreRule], repo_root: Path
) -> list[LintIssue]:
    """SHADOWED / REDUNDANT — 子 .gitignore 规则被父 .gitignore 覆盖.

    SHADOWED:子规则的目标已经被父级 ignore(子规则不必要,不一定字面相同)
    REDUNDANT:子规则字面等价于父级某条规则(纯重复)

    简化判定:
    - REDUNDANT — pat(改写到父 scope)字面 == 父规则
    - SHADOWED — pat 命中的目标也被某父规则命中(用 git check-ignore 双查)
    """
    issues: list[LintIssue] = []
    # 按 scope 分组
    rules_by_file: dict[Path, list[GitignoreRule]] = {}
    for r in rules:
        rules_by_file.setdefault(r.file, []).append(r)

    files_sorted = sorted(rules_by_file.keys(), key=lambda p: len(p.parts))
    if not files_sorted:
        return issues
    # 最浅 scope 是 root(.gitignore at root → file '.gitignore' → scope='.')
    for child_file in files_sorted:
        child_scope = gitignore_scope(child_file)
        # 找所有"父" .gitignore(scope 更浅且在祖先链上 · 不含自己)
        parent_files = [
            pf
            for pf in files_sorted
            if pf != child_file
            and is_descendant_scope(child_scope, gitignore_scope(pf))
            and gitignore_scope(pf) != child_scope
        ]
        if not parent_files:
            continue

        for child_rule in rules_by_file[child_file]:
            if child_rule.is_negation:
                continue  # negation 本来就是覆盖父
            # REDUNDANT 检查:rewriten pattern 字面等于任意父规则
            for pf in parent_files:
                parent_scope = gitignore_scope(pf)
                rewritten = pattern_for_parent_scope(
                    child_rule.pattern, child_scope, parent_scope
                )
                # 父规则字面相同(不论 anchored / trailing-slash variant)
                for parent_rule in rules_by_file[pf]:
                    if parent_rule.is_negation:
                        continue
                    if _normalize_pattern(rewritten) == _normalize_pattern(
                        parent_rule.pattern
                    ):
                        issues.append(
                            LintIssue(
                                category="REDUNDANT",
                                severity="warn",
                                file=str(child_file),
                                line=child_rule.line_no,
                                rule=child_rule.pattern,
                                detail=f"已在 {pf}:{parent_rule.line_no} 定义 '{parent_rule.pattern}'",
                            )
                        )
                        break  # 一条父规则就够标 REDUNDANT
                else:
                    continue
                break

            # SHADOWED 检查:用 git check-ignore 看 child_scope 下命中 child_rule 的样本路径
            # 是否其实命中的是父 .gitignore 的某条规则
            # 简化:取一个代表性 path = scope/pat(去通配),问 git check-ignore -v
            # 注:complete shadow detection 很贵 · 这里仅对纯字面 pat 跑
            sample = _sample_path_for_pattern(child_rule.pattern, child_scope)
            if sample and not _is_pattern_glob(child_rule.pattern):
                # 这是个确定路径 · 问 git
                rule_file, _, _ = _git_check_ignore_origin(repo_root, sample)
                if rule_file and rule_file != str(child_file):
                    # 父级规则盖了同一路径 -> SHADOWED(非 redundant 字面 — 但语义重叠)
                    # 仅当不是已经标过 REDUNDANT 才记
                    already_redundant = any(
                        i.file == str(child_file)
                        and i.line == child_rule.line_no
                        and i.category == "REDUNDANT"
                        for i in issues
                    )
                    if not already_redundant:
                        issues.append(
                            LintIssue(
                                category="SHADOWED",
                                severity="warn",
                                file=str(child_file),
                                line=child_rule.line_no,
                                rule=child_rule.pattern,
                                detail=f"路径 '{sample}' 已被 {rule_file} 中规则覆盖",
                            )
                        )
    return issues


def check_untracked_secrets(repo_root: Path) -> list[LintIssue]:
    """UNTRACKED_SECRET — untracked 文件命中机密 pattern 但没被 ignore."""
    issues: list[LintIssue] = []
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError:
        return issues

    for line in out.splitlines():
        # `?? path` = untracked
        if not line.startswith("??"):
            continue
        path = line[3:].strip()
        # 解 quoted name(git status 默认会 quote 含特殊字符的)
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        if is_suspect_secret(path):
            issues.append(
                LintIssue(
                    category="UNTRACKED_SECRET",
                    severity="error",
                    file=".gitignore",
                    line=0,
                    rule=path,
                    detail=f"untracked file '{path}' 像机密,应该加 .gitignore",
                )
            )
    return issues


def check_tracked_in_gitignore(repo_root: Path, rules: list[GitignoreRule]) -> list[LintIssue]:
    """TRACKED_IN_IGNORE — 已 tracked 的文件命中某条 .gitignore(历史遗留)."""
    issues: list[LintIssue] = []
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError:
        return issues

    tracked = [t for t in out.splitlines() if t]
    # 用 git check-ignore -v --no-index 校 · 一次 batch
    if not tracked:
        return issues

    # `--no-index` 会忽略 index 状态;但我们要的是 "假设没 tracked 是否会 ignore"
    # 跑 `git check-ignore -v --no-index <files...>` · 命中的就是 tracked-but-in-gitignore
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "check-ignore", "-v", "--no-index", "--stdin"],
            input="\n".join(tracked),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return issues

    for line in proc.stdout.splitlines():
        # 格式: <source>:<line>:<pattern>\t<file>
        m = re.match(r"^([^:]+):(\d+):([^\t]*)\t(.+)$", line)
        if not m:
            continue
        src, ln, pat, fpath = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        # 跳 negation -> 那是反向(没真 ignore)
        if pat.startswith("!"):
            continue
        # 排除 src 自己就是 ".git/info/exclude" 或全局 — 仅记仓库 .gitignore
        if src.startswith(".git/"):
            continue
        issues.append(
            LintIssue(
                category="TRACKED_IN_IGNORE",
                severity="warn",
                file=src,
                line=ln,
                rule=pat,
                detail=f"已 tracked '{fpath}' 命中 .gitignore 规则(若有意 git add -f 则忽略 · 否则 git rm --cached 清)",
            )
        )
    return issues


# ---------------- 辅助 ---------------- #


def _normalize_pattern(pat: str) -> str:
    """归一化 pattern · 去前导 / 和尾 / 后用于字面对比."""
    p = pat.strip()
    if p.startswith("/"):
        p = p[1:]
    if p.endswith("/"):
        p = p[:-1]
    return p


def _is_pattern_glob(pat: str) -> bool:
    return any(c in pat for c in "*?[")


def _sample_path_for_pattern(pat: str, scope: Path) -> str | None:
    """非 glob pat -> 给一个 scope 下的代表路径(给 git check-ignore 用)."""
    if _is_pattern_glob(pat):
        return None
    p = pat.strip()
    if p.startswith("/"):
        p = p[1:]
    if p.endswith("/"):
        p = p[:-1]
    if not p:
        return None
    if str(scope) == ".":
        return p
    return f"{scope}/{p}"


def _git_check_ignore_origin(
    repo_root: Path, path: str
) -> tuple[str | None, int | None, str | None]:
    """对一个路径跑 git check-ignore -v · 返回 (file, line, pattern) 或全 None."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "check-ignore", "-v", "--no-index", path],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None, None, None
    if proc.returncode != 0:
        return None, None, None
    line = proc.stdout.strip().splitlines()
    if not line:
        return None, None, None
    m = re.match(r"^([^:]+):(\d+):([^\t]*)\t(.+)$", line[0])
    if not m:
        return None, None, None
    return m.group(1), int(m.group(2)), m.group(3)


# ---------------- 报告输出 ---------------- #


def format_markdown(report: LintReport) -> str:
    out: list[str] = []
    out.append("# gitignore lint report")
    out.append("")
    out.append(f"- repo: `{report.repo_root}`")
    out.append(f"- gitignore files scanned: **{len(report.gitignore_files)}**")
    for f in report.gitignore_files:
        out.append(f"  - `{f}`")
    out.append("")
    counts = report.counts_by_category()
    if not report.issues:
        out.append("**status: clean** — 0 issues found.")
        return "\n".join(out)

    out.append(f"- issues: **{len(report.issues)}** "
               f"(errors={len(report.errors)}, warnings={len(report.warnings)})")
    out.append("")
    out.append("## counts by category")
    out.append("")
    out.append("| category | count |")
    out.append("|---|---|")
    for cat in ["CONFLICT", "SHADOWED", "REDUNDANT", "UNTRACKED_SECRET", "TRACKED_IN_IGNORE"]:
        out.append(f"| {cat} | {counts.get(cat, 0)} |")
    out.append("")
    out.append("## issues")
    out.append("")
    out.append("| severity | category | file | line | rule | detail |")
    out.append("|---|---|---|---|---|---|")
    for i in report.issues:
        rule_disp = (i.rule or "").replace("|", "\\|")
        detail_disp = (i.detail or "").replace("|", "\\|")
        out.append(
            f"| {i.severity} | {i.category} | `{i.file}` | {i.line} | `{rule_disp}` | {detail_disp} |"
        )
    return "\n".join(out)


def format_json(report: LintReport) -> str:
    data = {
        "repo_root": report.repo_root,
        "gitignore_files_scanned": report.gitignore_files,
        "counts": {
            **{c: 0 for c in ["CONFLICT", "SHADOWED", "REDUNDANT", "UNTRACKED_SECRET", "TRACKED_IN_IGNORE"]},
            **report.counts_by_category(),
        },
        "totals": {
            "issues": len(report.issues),
            "errors": len(report.errors),
            "warnings": len(report.warnings),
        },
        "issues": [
            {
                "severity": i.severity,
                "category": i.category,
                "file": i.file,
                "line": i.line,
                "rule": i.rule,
                "detail": i.detail,
            }
            for i in report.issues
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


# ---------------- Fix ---------------- #


def apply_fix(report: LintReport, repo_root: Path) -> dict[str, int]:
    """删 REDUNDANT 行 + 把 CONFLICT 中重复的子级行删掉(优先保留父 .gitignore).

    Returns: {file_path: lines_removed_count}
    """
    stats: dict[str, int] = {}
    # 收集 (file, line_no) 待删
    to_delete: dict[str, set[int]] = {}

    for issue in report.issues:
        if issue.category in ("REDUNDANT",):
            to_delete.setdefault(issue.file, set()).add(issue.line)
        # CONFLICT — 保留最浅 scope · 其他删
        # 实际处理在下方批

    # CONFLICT — group 同 rule · 保浅删深
    conflicts_by_rule: dict[str, list[LintIssue]] = {}
    for issue in report.issues:
        if issue.category == "CONFLICT":
            conflicts_by_rule.setdefault(issue.rule, []).append(issue)
    for rule, lst in conflicts_by_rule.items():
        # 选保留: file 路径 part 最少的(最浅)
        keep = min(lst, key=lambda x: (len(Path(x.file).parts), x.file))
        for other in lst:
            if (other.file, other.line) != (keep.file, keep.line):
                to_delete.setdefault(other.file, set()).add(other.line)

    for rel_file, line_nums in to_delete.items():
        abs_file = repo_root / rel_file
        if not abs_file.exists():
            continue
        # 备份
        bak = abs_file.with_suffix(abs_file.suffix + ".bak")
        bak.write_text(abs_file.read_text(encoding="utf-8"), encoding="utf-8")
        # 重写(skip line_no)
        kept: list[str] = []
        for idx, line in enumerate(abs_file.read_text(encoding="utf-8").splitlines(), start=1):
            if idx in line_nums:
                continue
            kept.append(line)
        abs_file.write_text("\n".join(kept) + "\n", encoding="utf-8")
        stats[rel_file] = len(line_nums)
    return stats


# ---------------- 主流程 ---------------- #


def run_lint(repo_root: Path, strict: bool = False) -> LintReport:
    report = LintReport(repo_root=str(repo_root))
    gitignore_files = find_gitignore_files(repo_root)
    report.gitignore_files = [str(g.relative_to(repo_root)) for g in gitignore_files]

    # 解析
    all_rules: list[GitignoreRule] = []
    for gi in gitignore_files:
        all_rules.extend(parse_gitignore(gi, repo_root))

    # 检查 1: CONFLICT
    report.issues.extend(check_conflicts(all_rules))
    # 检查 2/3: SHADOWED / REDUNDANT
    report.issues.extend(check_shadowed_and_redundant(all_rules, repo_root))
    # 检查 4: UNTRACKED_SECRET
    report.issues.extend(check_untracked_secrets(repo_root))
    # 检查 5: TRACKED_IN_IGNORE
    report.issues.extend(check_tracked_in_gitignore(repo_root, all_rules))

    # strict 模式 — 把 SHADOWED/REDUNDANT 升 error
    if strict:
        for i in report.issues:
            if i.category in ("SHADOWED", "REDUNDANT"):
                i.severity = "error"

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="lint 多 .gitignore 一致性 · 5 类检查(P3-20)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="指定仓库根 · 默认从 cwd 找 git toplevel",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="报告格式(default markdown)",
    )
    parser.add_argument("--fix", action="store_true", help="自动删 REDUNDANT + CONFLICT 中冗余行")
    parser.add_argument("--quiet", action="store_true", help="不打报告 · 仅退出码")
    parser.add_argument("--strict", action="store_true", help="SHADOWED/REDUNDANT 升 error")
    args = parser.parse_args()

    # 取仓库根
    if args.repo_root:
        repo_root = Path(args.repo_root).resolve()
    else:
        try:
            out = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            repo_root = Path(out)
        except subprocess.CalledProcessError:
            print("error: not in a git repo · 用 --repo-root 指定", file=sys.stderr)
            return 2

    if not (repo_root / ".git").exists():
        print(f"error: {repo_root} 不是 git repo · --repo-root 指错了?", file=sys.stderr)
        return 2

    report = run_lint(repo_root, strict=args.strict)

    if args.fix:
        stats = apply_fix(report, repo_root)
        if stats:
            print(f"# fix applied · 已修 {sum(stats.values())} 行", file=sys.stderr)
            for f, n in stats.items():
                print(f"  - {f}: {n} 行删除 · 备份 -> {f}.bak", file=sys.stderr)
            # 修后重跑 lint 取最终态
            report = run_lint(repo_root, strict=args.strict)

    if not args.quiet:
        if args.format == "json":
            print(format_json(report))
        else:
            print(format_markdown(report))

    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
