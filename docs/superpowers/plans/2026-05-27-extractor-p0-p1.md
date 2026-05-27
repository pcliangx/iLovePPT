# Extractor P0+P1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 改造 `iloveppt-template-extractor` agent 让模板入库变 (1) idempotent / resumable (2) mode-aware (3) 自检靠脚本而不是内嵌 bash (4) placeholder_map 由脚本产骨架而非 LLM 猜 (5) 多个 P1 鲁棒性短板修复。

**Architecture:** 3 个新 / 改 .py 脚本 + extractor.md agent prompt 重写 + ingest_workflow.md 文档同步。脚本可单跑 + 有 pytest 覆盖;agent prompt 改动靠 grep + 真实 dry-run 验证。`library/pptx-templates/scripts/` 跟 `_source/` `items/` `INDEX.md` 同层,职能内聚。

**Tech Stack:** Python 3.11 / python-pptx / PyYAML / subprocess + 超时 / pytest。

**Pre-flight 状态确认(已澄清):**
- working tree 上 88 个 `D` 状态文件是用户预期 cleanup,**不动**(不 stage,不 restore)
- 本计划完成后用户会用新版 extractor re-ingest 4 个 _source 模板验证,**不在本计划范围**
- Commit 时 `git add` 精确到本计划新增 / 修改的文件,不用 `git add -A`

---

## File Structure

**新增**:
- `library/pptx-templates/scripts/extractor_self_check.py` — Step 3.3 自检,exit code 驱动
- `library/pptx-templates/scripts/inspect_placeholders.py` — 产 placeholder_map.yaml.draft 骨架(脚本算 tree_path,LLM 只填语义)
- `library/pptx-templates/scripts/__init__.py` — 让 pytest import 友好
- `library/pptx-templates/scripts/tests/test_extractor_self_check.py`
- `library/pptx-templates/scripts/tests/test_inspect_placeholders.py`
- `library/pptx-templates/scripts/tests/fixtures/` — 小 .pptx fixture + 已知坏 yaml 样本

**修改**:
- `.claude/agents/iloveppt-template-extractor.md` — 入参 mode 字段 + Step 0/1/2/3/4 全部改写
- `library/_rag/render_pages.py` — 加 subprocess 超时
- `library/pptx-templates/ingest_workflow.md` — schema 文档同步(mode 字段 / scripts 引用)

---

## Task 1: 写 `extractor_self_check.py` 主体 + 测试

**Files:**
- Create: `library/pptx-templates/scripts/__init__.py`
- Create: `library/pptx-templates/scripts/extractor_self_check.py`
- Create: `library/pptx-templates/scripts/tests/__init__.py`
- Create: `library/pptx-templates/scripts/tests/test_extractor_self_check.py`
- Create: `library/pptx-templates/scripts/tests/fixtures/minimal_template_ok/meta.yaml.draft`
- Create: `library/pptx-templates/scripts/tests/fixtures/minimal_template_ok/pages/01-cover/meta.yaml.draft`
- Create: `library/pptx-templates/scripts/tests/fixtures/bad_enum/pages/01-cover/meta.yaml.draft`
- Create: `library/pptx-templates/scripts/tests/fixtures/bad_yaml/pages/01-cover/meta.yaml.draft`
- Create: `library/pptx-templates/scripts/tests/fixtures/missing_fields/pages/01-cover/meta.yaml.draft`

- [ ] **Step 1.1: 写 minimal_template_ok fixture(全过的样本,后续测试 baseline)**

Create `library/pptx-templates/scripts/tests/fixtures/minimal_template_ok/meta.yaml.draft`:
```yaml
status: draft
provenance:
  schema_version: v1
  embedding_model: tongyi-embedding-vision-plus
  embedding_dim: 1152
  ingested_at: 2026-05-27T10:00:00Z
  source_pptx_sha256: 0000000000000000000000000000000000000000000000000000000000000000
  source_pptx_size_bytes: 12345
extraction:
  declared_pages: 1
  rendered_pages: 1
  discrepancy: 0
  discrepancy_resolution: pending
  low_confidence_pages: []
  failed_pages: []
id: minimal_template_ok
name: "Minimal · 测试样本"
category: enterprise
content_intent:
  - 测试场景
when_to_use:
  - 单元测试
keywords:
  - test
recommended_for:
  - testing
visual_signature:
  - 蓝色
assets:
  total_pages: 1
pages: [01-cover]
implementation:
  tier1_template_slide_reuse:
    ready: false
    coverage: []
    gaps: []
  tier2_python_theme: null
```

Create `library/pptx-templates/scripts/tests/fixtures/minimal_template_ok/pages/01-cover/meta.yaml.draft`:
```yaml
status: draft
confidence: 0.92
needs_manual_review: false
id: minimal_template_ok__01-cover
name: "Cover · 测试封面"
layout_type: cover
content_intent:
  - 封面
when_to_use:
  - 第 1 页
keywords:
  - 封面
native_elements:
  - 标题
template_name: minimal_template_ok
page_number: 1
```

- [ ] **Step 1.2: 写 bad fixtures**

`tests/fixtures/bad_enum/pages/01-cover/meta.yaml.draft` —— 复制 minimal_template_ok 的页 yaml,但把 `layout_type: cover` 改为 `layout_type: comparison_venn`(违反 enum)。

`tests/fixtures/bad_yaml/pages/01-cover/meta.yaml.draft`:
```yaml
status: draft
layout_type: cover
content_intent:
  - "QUOTED" text rest    # YAML 解析失败的经典模式
```

`tests/fixtures/missing_fields/pages/01-cover/meta.yaml.draft` —— 复制 minimal_template_ok 的页 yaml 但删掉 `keywords` 字段。

- [ ] **Step 1.3: 写 failing test**

Create `library/pptx-templates/scripts/tests/test_extractor_self_check.py`:
```python
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "extractor_self_check.py"
FIXTURES = Path(__file__).parent / "fixtures"


def run(name: str, fixture_root: Path) -> tuple[int, str]:
    """运行 self_check 脚本,返回 (exit_code, stdout+stderr)."""
    r = subprocess.run(
        [sys.executable, str(SCRIPT), name, "--items-root", str(fixture_root)],
        capture_output=True, text=True,
    )
    return r.returncode, r.stdout + r.stderr


def test_ok_fixture_passes():
    code, out = run("minimal_template_ok", FIXTURES)
    assert code == 0, f"expected exit 0, got {code}\n{out}"


def test_bad_enum_fails_with_code_1():
    code, out = run("bad_enum", FIXTURES)
    assert code == 1, f"expected exit 1, got {code}\n{out}"
    assert "ENUM_VIOLATION" in out
    assert "comparison_venn" in out


def test_bad_yaml_fails_with_code_3():
    code, out = run("bad_yaml", FIXTURES)
    assert code == 3, f"expected exit 3, got {code}\n{out}"
    assert "YAML_SYNTAX_ERROR" in out


def test_missing_fields_fails_with_code_1():
    code, out = run("missing_fields", FIXTURES)
    assert code == 1, f"expected exit 1, got {code}\n{out}"
    assert "MISSING_PAGE_FIELD" in out
    assert "keywords" in out


def test_nonexistent_template_fails_with_code_4():
    code, out = run("does_not_exist", FIXTURES)
    assert code == 4
    assert "TEMPLATE_NOT_FOUND" in out
```

- [ ] **Step 1.4: 运行测试确认全 fail(脚本还没写)**

```bash
cd /Users/pc2026/Documents/DevTools/iLovePPT
.venv/bin/pytest library/pptx-templates/scripts/tests/test_extractor_self_check.py -v
```
Expected: 5 个测试全 fail(脚本不存在或 import error)

- [ ] **Step 1.5: 实现 `extractor_self_check.py`**

Create `library/pptx-templates/scripts/__init__.py` (空文件)
Create `library/pptx-templates/scripts/tests/__init__.py` (空文件)
Create `library/pptx-templates/scripts/extractor_self_check.py`:
```python
"""Extractor Step 3.3 self-check · exit code 驱动 · 替代内嵌 bash.

Exit codes:
  0 = 全过
  1 = 字段缺失 / enum / 格式问题
  2 = placeholder_map tree_path 不能 resolve(此 task 暂不实现,Task 2 补)
  3 = YAML 语法错
  4 = 模板目录不存在
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ALLOWED_LAYOUTS = {
    "cover", "toc", "section_divider", "summary", "closing", "quote",
    "single_focus", "cards", "bullet_list", "data",
    "timeline", "pyramid", "venn", "radial", "process_flow", "quadrant", "comparison",
    "other",
}

REQUIRED_TEMPLATE_FIELDS = [
    "id", "name", "category", "content_intent", "when_to_use",
    "keywords", "recommended_for", "visual_signature",
    "status", "provenance", "extraction",
]

REQUIRED_PAGE_FIELDS = [
    "id", "name", "layout_type", "content_intent", "when_to_use",
    "keywords", "native_elements", "status", "confidence",
]

ID_RE = re.compile(r"^[a-z0-9_-]+__\d{2}-[a-z_]+$")


def load_yaml(path: Path) -> tuple[dict | None, str | None]:
    """返回 (data, error_msg). data is None 时 error_msg 非空."""
    try:
        with open(path) as f:
            return yaml.safe_load(f), None
    except yaml.YAMLError as e:
        return None, str(e).split("\n")[0]
    except FileNotFoundError:
        return None, f"file not found: {path}"


def check(name: str, items_root: Path) -> int:
    tpl_dir = items_root / name
    if not tpl_dir.is_dir():
        print(f"TEMPLATE_NOT_FOUND: {tpl_dir}")
        return 4

    errors: list[str] = []
    syntax_errors: list[str] = []

    # 0. YAML 语法(模板级 + 所有页)
    tpl_meta_path = tpl_dir / "meta.yaml.draft"
    if not tpl_meta_path.exists():
        tpl_meta_path = tpl_dir / "meta.yaml"
    tpl_meta, err = load_yaml(tpl_meta_path)
    if err:
        syntax_errors.append(f"YAML_SYNTAX_ERROR: {tpl_meta_path}: {err}")

    page_paths = sorted(tpl_dir.glob("pages/*/meta.yaml.draft"))
    if not page_paths:
        page_paths = sorted(tpl_dir.glob("pages/*/meta.yaml"))
    page_metas: list[tuple[Path, dict]] = []
    for p in page_paths:
        data, err = load_yaml(p)
        if err:
            syntax_errors.append(f"YAML_SYNTAX_ERROR: {p}: {err}")
        elif data is not None:
            page_metas.append((p, data))

    if syntax_errors:
        for e in syntax_errors:
            print(e)
        return 3

    # 1. 模板级必填字段
    if tpl_meta:
        for f in REQUIRED_TEMPLATE_FIELDS:
            if f not in tpl_meta:
                errors.append(f"MISSING_TEMPLATE_FIELD: {tpl_meta_path}: {f}")

    # 2. 页级必填字段
    for p, data in page_metas:
        for f in REQUIRED_PAGE_FIELDS:
            if f not in data:
                errors.append(f"MISSING_PAGE_FIELD: {p}: {f}")

    # 3. layout_type enum
    for p, data in page_metas:
        lt = data.get("layout_type")
        if lt and lt not in ALLOWED_LAYOUTS:
            errors.append(f"ENUM_VIOLATION: {p}: layout_type={lt}")

    # 4. id 格式 + 唯一性
    ids = []
    for p, data in page_metas:
        page_id = data.get("id", "")
        if not ID_RE.match(page_id):
            errors.append(f"ID_FORMAT_INVALID: {p}: id={page_id!r} (expected <name>__<NN-slug>)")
        ids.append(page_id)
    if len(set(ids)) != len(ids):
        errors.append(f"ID_DUPLICATE: {len(ids)} pages but {len(set(ids))} unique ids")

    # 5. confidence 是数字
    for p, data in page_metas:
        c = data.get("confidence")
        if not isinstance(c, (int, float)):
            errors.append(f"CONFIDENCE_NOT_NUMERIC: {p}: confidence={c!r}")
        elif not 0.0 <= c <= 1.0:
            errors.append(f"CONFIDENCE_OUT_OF_RANGE: {p}: confidence={c}")

    # 6. provenance.embedding_dim == 1152
    if tpl_meta:
        prov = tpl_meta.get("provenance", {})
        if prov.get("embedding_dim") != 1152:
            errors.append(f"EMBEDDING_DIM_WRONG: {tpl_meta_path}: got {prov.get('embedding_dim')}, expected 1152")

    # 7. extraction 算式自洽
    if tpl_meta:
        ext = tpl_meta.get("extraction", {})
        d = ext.get("declared_pages")
        r = ext.get("rendered_pages")
        disc = ext.get("discrepancy")
        if d is not None and r is not None and disc is not None:
            if d - r != disc:
                errors.append(f"EXTRACTION_MATH_INCONSISTENT: declared={d} rendered={r} discrepancy={disc}")

    # 8. template_name 跟父目录名一致
    for p, data in page_metas:
        tn = data.get("template_name")
        if tn and tn != name:
            errors.append(f"TEMPLATE_NAME_MISMATCH: {p}: template_name={tn} != {name}")

    if errors:
        for e in errors:
            print(e)
        return 1

    print(f"OK: {name} · {len(page_metas)} pages · all checks passed")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--items-root", default="library/pptx-templates/items",
                    help="items/ 目录(默认 library/pptx-templates/items)")
    args = ap.parse_args()
    sys.exit(check(args.name, Path(args.items_root)))


if __name__ == "__main__":
    main()
```

- [ ] **Step 1.6: 跑测试,确认全过**

```bash
.venv/bin/pytest library/pptx-templates/scripts/tests/test_extractor_self_check.py -v
```
Expected: 5 passed

- [ ] **Step 1.7: Commit**

```bash
git add library/pptx-templates/scripts/__init__.py \
        library/pptx-templates/scripts/extractor_self_check.py \
        library/pptx-templates/scripts/tests/
git commit -m "feat(extractor): add self_check.py · exit-code driven · 9 checks"
```

---

## Task 2: 写 `inspect_placeholders.py` 主体 + 测试

**Files:**
- Create: `library/pptx-templates/scripts/inspect_placeholders.py`
- Create: `library/pptx-templates/scripts/tests/test_inspect_placeholders.py`
- Create: `library/pptx-templates/scripts/tests/fixtures/sample.pptx` — 用 python-pptx 构造的 2 页 fixture

- [ ] **Step 2.1: 写 fixture 生成脚本 + sample.pptx**

Create `library/pptx-templates/scripts/tests/fixtures/_build_sample_pptx.py`:
```python
"""一次性脚本:生成 sample.pptx fixture(跑过就 commit 产物,不每次跑)."""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt

p = Presentation()
# Page 1: cover · title + subtitle
slide1 = p.slides.add_slide(p.slide_layouts[5])  # blank
title = slide1.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(1))
title.text_frame.text = "深蓝主标题"
title.text_frame.paragraphs[0].runs[0].font.size = Pt(44)
subtitle = slide1.shapes.add_textbox(Inches(1), Inches(3.2), Inches(8), Inches(0.6))
subtitle.text_frame.text = "副标题占位"

# Page 2: cards · 3 textbox(模拟 3-cols cards)
slide2 = p.slides.add_slide(p.slide_layouts[5])
for i in range(3):
    tb = slide2.shapes.add_textbox(Inches(0.5 + i * 3), Inches(2), Inches(2.5), Inches(2))
    tb.text_frame.text = f"卡片 {i + 1}"

out = Path(__file__).parent / "sample.pptx"
p.save(out)
print(f"wrote {out}")
```

Run once + commit the .pptx:
```bash
.venv/bin/python library/pptx-templates/scripts/tests/fixtures/_build_sample_pptx.py
```

- [ ] **Step 2.2: 写 failing test**

Create `library/pptx-templates/scripts/tests/test_inspect_placeholders.py`:
```python
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).parent.parent / "inspect_placeholders.py"
SAMPLE_PPTX = Path(__file__).parent / "fixtures" / "sample.pptx"


def run(pptx: Path, page_idx: int) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(pptx), str(page_idx)],
        capture_output=True, text=True,
    )
    return r.returncode, r.stdout


def test_page_0_returns_yaml_with_2_slots():
    code, out = run(SAMPLE_PPTX, 0)
    assert code == 0, out
    data = yaml.safe_load(out)
    assert "slots" in data
    assert len(data["slots"]) == 2  # title + subtitle
    for slot in data["slots"]:
        assert "tree_path" in slot
        assert "raw_text_sample" in slot
        assert "bbox" in slot
        assert "id" in slot  # 骨架填 "?"
        assert slot["id"] == "?"


def test_page_1_returns_3_slots():
    code, out = run(SAMPLE_PPTX, 1)
    assert code == 0
    data = yaml.safe_load(out)
    assert len(data["slots"]) == 3
    texts = [s["raw_text_sample"] for s in data["slots"]]
    assert any("卡片 1" in t for t in texts)


def test_page_out_of_range_fails():
    code, out = run(SAMPLE_PPTX, 99)
    assert code != 0


def test_pptx_not_found_fails():
    code, out = run(Path("/tmp/nonexistent.pptx"), 0)
    assert code != 0


def test_template_page_index_in_output():
    code, out = run(SAMPLE_PPTX, 0)
    data = yaml.safe_load(out)
    assert data["template_page_index"] == 0


def test_slots_sorted_top_to_bottom():
    code, out = run(SAMPLE_PPTX, 0)
    data = yaml.safe_load(out)
    tops = [s["bbox"]["top"] for s in data["slots"]]
    assert tops == sorted(tops), f"slots not sorted top-to-bottom: {tops}"
```

- [ ] **Step 2.3: 跑测试确认全 fail**

```bash
.venv/bin/pytest library/pptx-templates/scripts/tests/test_inspect_placeholders.py -v
```
Expected: 6 fail(脚本不存在)

- [ ] **Step 2.4: 实现 `inspect_placeholders.py`**

Create `library/pptx-templates/scripts/inspect_placeholders.py`:
```python
"""产 placeholder_map.yaml.draft 骨架 · 脚本算 tree_path,LLM 只填语义.

Usage:
    inspect_placeholders.py <pptx_path> <page_idx>      # page_idx 0-indexed

Output (stdout, YAML):
    template_page_index: 0
    layout_class: "?"          # extractor 跟 meta.yaml.draft.layout_type 同步
    slots:
      - id: "?"                # extractor 填 "title" / "tier_1" / "card_1_body"
        tree_path: '3'
        raw_text_sample: "深蓝主标题"
        bbox: { left: 1.0, top: 2.0, width: 8.0, height: 1.0 }   # inches
        font_size_pt: 44
        capacity_chars: "?"    # extractor 估
        text_color_override: null

Exit codes:
  0 = OK
  1 = pptx not found / page out of range
  2 = pptx parse error
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pptx import Presentation
from pptx.util import Emu


def walk_shapes(shapes, prefix: str = "") -> list[dict]:
    """递归 walk shapes,返回所有含文字的 leaf shape 信息."""
    out = []
    for i, shape in enumerate(shapes):
        path = f"{prefix}{i}" if not prefix else f"{prefix}.{i}"
        if shape.shape_type == 6:  # group
            try:
                out.extend(walk_shapes(shape.shapes, prefix=path))
            except (AttributeError, ValueError):
                pass
        else:
            if not getattr(shape, "has_text_frame", False):
                continue
            tf = shape.text_frame
            text = tf.text.strip() if tf.text else ""
            if not text:
                continue
            font_size = None
            try:
                run = tf.paragraphs[0].runs[0]
                if run.font.size:
                    font_size = run.font.size.pt
            except (IndexError, AttributeError):
                pass
            out.append({
                "tree_path": path,
                "raw_text_sample": text[:60],
                "bbox": {
                    "left": round(Emu(shape.left).inches, 2) if shape.left else 0.0,
                    "top": round(Emu(shape.top).inches, 2) if shape.top else 0.0,
                    "width": round(Emu(shape.width).inches, 2) if shape.width else 0.0,
                    "height": round(Emu(shape.height).inches, 2) if shape.height else 0.0,
                },
                "font_size_pt": font_size,
            })
    return out


def inspect(pptx_path: Path, page_idx: int) -> dict:
    if not pptx_path.exists():
        print(f"PPTX_NOT_FOUND: {pptx_path}", file=sys.stderr)
        sys.exit(1)
    try:
        p = Presentation(str(pptx_path))
    except Exception as e:
        print(f"PPTX_PARSE_ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    if page_idx < 0 or page_idx >= len(p.slides):
        print(f"PAGE_OUT_OF_RANGE: page_idx={page_idx}, total={len(p.slides)}", file=sys.stderr)
        sys.exit(1)

    slide = p.slides[page_idx]
    leaves = walk_shapes(slide.shapes)
    # 按几何位置排序:top 优先,然后 left
    leaves.sort(key=lambda s: (s["bbox"]["top"], s["bbox"]["left"]))

    slots = []
    for leaf in leaves:
        slots.append({
            "id": "?",
            "tree_path": leaf["tree_path"],
            "raw_text_sample": leaf["raw_text_sample"],
            "bbox": leaf["bbox"],
            "font_size_pt": leaf["font_size_pt"],
            "capacity_chars": "?",
            "text_color_override": None,
        })

    return {
        "template_page_index": page_idx,
        "layout_class": "?",
        "slots": slots,
    }


def main():
    if len(sys.argv) != 3:
        print("Usage: inspect_placeholders.py <pptx_path> <page_idx>", file=sys.stderr)
        sys.exit(1)
    result = inspect(Path(sys.argv[1]), int(sys.argv[2]))
    print(yaml.safe_dump(result, sort_keys=False, allow_unicode=True))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2.5: 跑测试**

```bash
.venv/bin/pytest library/pptx-templates/scripts/tests/test_inspect_placeholders.py -v
```
Expected: 6 passed

- [ ] **Step 2.6: 给 self_check.py 加 tree_path resolve 校验(exit code 2)**

Edit `library/pptx-templates/scripts/extractor_self_check.py`:在 `check()` 函数末尾,errors 检查之前加:

```python
    # 9. placeholder_map tree_path 能 resolve(若 placeholder_map 存在 + 源 .pptx 在)
    source_pptx = items_root.parent / "_source" / f"{name}.pptx"
    if source_pptx.exists():
        from pptx import Presentation as _Pres
        try:
            pres = _Pres(str(source_pptx))
            for p in tpl_dir.glob("pages/*/placeholder_map.yaml.draft"):
                pmap, err = load_yaml(p)
                if err or not pmap:
                    continue
                idx = pmap.get("template_page_index")
                if idx is None or idx >= len(pres.slides):
                    errors.append(f"PMAP_PAGE_INDEX_INVALID: {p}: template_page_index={idx}")
                    continue
                slide = pres.slides[idx]
                for slot in pmap.get("slots", []):
                    tp = slot.get("tree_path", "")
                    if not _resolve_tree_path(slide.shapes, tp):
                        errors.append(f"PMAP_TREE_PATH_UNRESOLVABLE: {p}: tree_path={tp!r}")
        except Exception as e:
            errors.append(f"PMAP_CHECK_FAILED: {e}")

    if any("PMAP_" in e for e in errors) and not any(
        not e.startswith(("PMAP_",)) for e in errors
    ):
        # 仅有 PMAP 错 → exit 2
        for e in errors:
            print(e)
        return 2
```

加 helper 函数(文件顶部 import 后):
```python
def _resolve_tree_path(shapes, tree_path: str) -> bool:
    """tree_path 形如 '3' / '3.16' / '3.16.0' · 能 walk 到则 True."""
    if not tree_path:
        return False
    parts = tree_path.split(".")
    current = list(shapes)
    for i, part in enumerate(parts):
        try:
            idx = int(part)
        except ValueError:
            return False
        if idx >= len(current):
            return False
        node = current[idx]
        if i == len(parts) - 1:
            return True
        try:
            current = list(node.shapes)
        except AttributeError:
            return False
    return True
```

- [ ] **Step 2.7: 加 placeholder_map 测试 case**

Edit `library/pptx-templates/scripts/tests/test_extractor_self_check.py`,加:
```python
def test_pmap_tree_path_unresolvable_returns_2(tmp_path):
    """构造一个 placeholder_map.draft 指向不存在的 tree_path,验证 exit code 2."""
    import shutil
    # 复制 minimal_template_ok 作为基础
    src = FIXTURES / "minimal_template_ok"
    dst = tmp_path / "minimal_template_ok"
    shutil.copytree(src, dst)
    # 在 _source/ 放 sample.pptx
    (tmp_path.parent / "_source").mkdir(exist_ok=True)
    shutil.copy(
        Path(__file__).parent / "fixtures" / "sample.pptx",
        tmp_path.parent / "_source" / "minimal_template_ok.pptx",
    )
    # 写坏 placeholder_map.draft(tree_path 99 不存在)
    pmap_path = dst / "pages" / "01-cover" / "placeholder_map.yaml.draft"
    pmap_path.write_text(
        "template_page_index: 0\n"
        "layout_class: cover\n"
        "slots:\n"
        "  - id: title\n"
        "    tree_path: '99'\n"
        "    capacity_chars: 24\n"
    )
    code, out = run("minimal_template_ok", tmp_path)
    assert code == 2, f"{code}\n{out}"
    assert "PMAP_TREE_PATH_UNRESOLVABLE" in out
```

- [ ] **Step 2.8: 跑全测试**

```bash
.venv/bin/pytest library/pptx-templates/scripts/tests/ -v
```
Expected: 12 passed(5 old + 6 new + 1 pmap)

- [ ] **Step 2.9: Commit**

```bash
git add library/pptx-templates/scripts/inspect_placeholders.py \
        library/pptx-templates/scripts/extractor_self_check.py \
        library/pptx-templates/scripts/tests/test_inspect_placeholders.py \
        library/pptx-templates/scripts/tests/test_extractor_self_check.py \
        library/pptx-templates/scripts/tests/fixtures/sample.pptx \
        library/pptx-templates/scripts/tests/fixtures/_build_sample_pptx.py
git commit -m "feat(extractor): add inspect_placeholders.py + self_check tree_path resolve"
```

---

## Task 3: `render_pages.py` 加 subprocess 超时

**Files:**
- Modify: `library/_rag/render_pages.py:50-67` — 2 处 `subprocess.run` 加 `timeout=300`

- [ ] **Step 3.1: 改 render_pages.py**

Edit `library/_rag/render_pages.py`,把:
```python
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", str(pptx), "--outdir", str(td_path)],
            check=True,
            capture_output=True,
        )
```
改为:
```python
        try:
            subprocess.run(
                ["soffice", "--headless", "--convert-to", "pdf", str(pptx), "--outdir", str(td_path)],
                check=True,
                capture_output=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            print("ERROR: soffice 转 PDF 超时 (300s) - RENDER_TIMEOUT", file=sys.stderr)
            sys.exit(2)
```

同样把第二个 subprocess.run(pdftoppm)加 `timeout=180` 和对应 TimeoutExpired 分支(exit 2)。

- [ ] **Step 3.2: 手动验证(用现有 .pptx)**

```bash
ls library/pptx-templates/_source/ | head -1   # 拿到第一个模板名
.venv/bin/python library/_rag/render_pages.py <name> --dpi 120
# Expected: 正常完成,日志含 soffice/pdftoppm 行
```

- [ ] **Step 3.3: Commit**

```bash
git add library/_rag/render_pages.py
git commit -m "fix(render): soffice/pdftoppm 加 timeout · 防 LibreOffice hang"
```

---

## Task 4: extractor.md 入参契约 + Step 0 校验改写

**Files:**
- Modify: `.claude/agents/iloveppt-template-extractor.md` § 入参契约 + § Step 0

- [ ] **Step 4.1: 改入参契约**

Find `## 入参契约` 段(第 60-66 行附近),替换为:
```yaml
working_dir: /abs/path/to/deck-工作目录    # 必填
template_path: /abs/path/to/company_a.pptx # 入参 mode=full / re_render_only / dry_run 必填;mode=placeholder_map_only 可省
name: company_a                            # 可选, 默认 = Path(template_path).stem;mode=placeholder_map_only 必填
mode: full                                 # 可选: full(默认) | placeholder_map_only | dry_run | re_render_only
overwrite: false                           # 可选 · items/<name>/meta.yaml 已存在时是否允许覆盖
```

加 mode 语义说明:
```markdown
**mode 语义**:
- `full` — Step 0 → 5 全跑
- `placeholder_map_only` — 跳 Step 1/2/2.5/3.1/3.2,**只**对每页跑 Step 3.1.5 生成 placeholder_map.yaml.draft(回填工程用,要求 meta.yaml 已存在)
- `dry_run` — Step 0 → 2.5,return 数字 + 预估时间,不写任何 .draft 文件
- `re_render_only` — Step 0 → 2.5,**保留** items/<name>/pages/*/meta.yaml,只重渲染 PNG(LibreOffice 升级 / dpi 调整)
```

- [ ] **Step 4.2: 改 Step 0 校验**

Find `### Step 0 · 校验` 段(第 70-76 行附近),替换:
```markdown
### Step 0 · 校验

1. 入参 mode 校验:`mode in {full, placeholder_map_only, dry_run, re_render_only}` · 否则 return `code: INVALID_MODE`
2. 入参 path 校验:
   - mode != placeholder_map_only:`template_path` 文件存在
   - 任何 mode:`<name>` 不含 `__` / `/` / `..` / 空格(reject `code: NAME_INVALID_CHARS`)
3. 计算 `<name>`(若入参没给则 `Path(template_path).stem`)
4. disk space precheck:`df -k library/pptx-templates/items` 可用 ≥ 500MB · 否则 return `code: DISK_LOW`
5. 已入库检查:
   - `items/<name>/meta.yaml`(无 .draft 后缀)已存在 + mode=full + overwrite=false → return `code: ALREADY_INGESTED`,提示用户加 `overwrite: true` 或换 name
   - `items/<name>/meta.yaml` 不存在 + mode=placeholder_map_only → return `code: META_NOT_FOUND`(回填工程需要已 ingest 的模板)
```

- [ ] **Step 4.3: 验证 grep**

```bash
grep -nE "^mode:" .claude/agents/iloveppt-template-extractor.md
grep -nE "INVALID_MODE|NAME_INVALID_CHARS|DISK_LOW|ALREADY_INGESTED|META_NOT_FOUND" .claude/agents/iloveppt-template-extractor.md
```
Expected: 至少 1 个 `^mode:` + 5 个错误码

- [ ] **Step 4.4: Commit**

```bash
git add .claude/agents/iloveppt-template-extractor.md
git commit -m "feat(extractor): 入参加 mode/overwrite · Step 0 校验加危险字符+disk space+已入库"
```

---

## Task 5: extractor.md Step 1 idempotent(sha256)

**Files:**
- Modify: `.claude/agents/iloveppt-template-extractor.md` § Step 1

- [ ] **Step 5.1: 改 Step 1**

Find `### Step 1 · 复制 .pptx 到 _source/` 段(第 78-82 行附近),替换为:
```markdown
### Step 1 · 复制 .pptx 到 _source/(idempotent · sha256 守门)

**mode=placeholder_map_only 跳过此 step**。

```bash
SRC_SHA=$(shasum -a 256 <template_path> | awk '{print $1}')
DEST=library/pptx-templates/_source/<name>.pptx

if [ -f "$DEST" ]; then
  DEST_SHA=$(shasum -a 256 $DEST | awk '{print $1}')
  if [ "$SRC_SHA" = "$DEST_SHA" ]; then
    echo "[step1] _source/<name>.pptx 已存在且 sha256 一致 · skip cp"
  elif [ "<overwrite>" = "true" ]; then
    echo "[step1] _source/<name>.pptx sha256 mismatch + overwrite=true · 覆盖"
    cp <template_path> $DEST
  else
    # return error · 不静默覆盖
    return code: SOURCE_SHA_MISMATCH · message: "_source/<name>.pptx 已存在但 sha256 不同 · 用 overwrite=true 或换 name"
  fi
else
  cp <template_path> $DEST
fi
```

`source_pptx_sha256` 字段(Step 3.2 写)取 cp 后的 sha,确保 provenance 跟实际 .pptx 一致。
```

- [ ] **Step 5.2: 验证**

```bash
grep -nE "SOURCE_SHA_MISMATCH|sha256 一致" .claude/agents/iloveppt-template-extractor.md
```

- [ ] **Step 5.3: Commit**

```bash
git add .claude/agents/iloveppt-template-extractor.md
git commit -m "feat(extractor): Step 1 sha256 idempotent · 防同名异内容覆盖"
```

---

## Task 6: extractor.md Step 2 + 2.5 idempotent

**Files:**
- Modify: `.claude/agents/iloveppt-template-extractor.md` § Step 2 + § Step 2.5

- [ ] **Step 6.1: 改 Step 2**

Find `### Step 2 · 渲染每页 PNG`(第 83-89 行),替换为:
```markdown
### Step 2 · 渲染每页 PNG(idempotent)

**mode=placeholder_map_only 跳过此 step**。

**Idempotency check**:
```bash
DECLARED=$(unzip -p library/pptx-templates/_source/<name>.pptx ppt/presentation.xml | grep -oc '<p:sldId ')
EXISTING=$(ls library/pptx-templates/items/<name>/pages/*/preview.png 2>/dev/null | wc -l | tr -d ' ')
if [ "$EXISTING" -gt 0 ] && [ "$EXISTING" = "$DECLARED" ] && [ "<mode>" != "re_render_only" ]; then
  echo "[step2] $EXISTING PNG 已存在 = declared · skip render"
else
  library/_rag/.venv/bin/python library/_rag/render_pages.py <name> --dpi 120
fi
```

`render_pages.py` 内部 soffice / pdftoppm 已加 timeout=300s/180s(见 Task 3),超时 return `code: RENDER_TIMEOUT`。
```

- [ ] **Step 6.2: Step 2.5 增加 mode=dry_run return 出口**

Find `### Step 2.5 · 页数对账`(第 91 行附近),在 step 末尾增加:
```markdown
**mode=dry_run 出口**:Step 2.5 完成后,**不进 Step 3**,直接 return:
```yaml
status: ok
next_action: dry_run_preview
declared_pages: <N>
rendered_pages: <M>
discrepancy: <N-M>
estimated_full_run_minutes: <M * 0.5>   # 每页 LLM 视觉分析 ~30s 经验值
artifacts:
  - path: library/pptx-templates/items/<name>/pages/*/preview.png
    kind: rendered_preview
```
```

- [ ] **Step 6.3: Commit**

```bash
git add .claude/agents/iloveppt-template-extractor.md
git commit -m "feat(extractor): Step 2 idempotent + Step 2.5 dry_run 出口"
```

---

## Task 7: extractor.md Step 3.1 idempotency + confidence 标定锚

**Files:**
- Modify: `.claude/agents/iloveppt-template-extractor.md` § Step 3.1

- [ ] **Step 7.1: 改 Step 3.1 头部加 idempotency**

Find `#### Step 3.1 · 逐页处理(NN 升序)`(第 134 行附近),在"对每张 preview.png"之前插入:
```markdown
**Idempotency check(进每页之前)**:
- 该页 `meta.yaml.draft` 已存在 + `status: draft` → skip Step 3.1 该页(已写过)
- 该页 `meta.yaml`(无 .draft)已存在 → skip(用户审过的不再覆盖)
- 仅 `pages/NN-page/preview.png` 存在(占位名)→ 跑全套
- mode=re_render_only → skip 所有 Step 3.1(只重渲染,不重写 meta)
```

- [ ] **Step 7.2: 在 confidence 字段说明里加标定锚**

Find `3. **confidence 必须是 0.0-1.0 数字**:`(第 156 行附近),替换为:
```markdown
3. **confidence 必须是 0.0-1.0 数字**(标定锚 · 防过度自信):
   - 0.92-0.98 — 完美匹配 enum 的标准页(标准 cover · 标准 toc · 3-cols cards)
   - 0.85-0.92 — 清晰但有小歧义(标准 process_flow 但箭头风格特殊)
   - 0.7-0.85 — 中等(几何像 timeline 但 label 像 process_flow)
   - 0.6-0.7 — 弱(2 个 enum 候选都成立 · 必须在 yaml 注释列出候选)
   - < 0.6 — 拿不准 → **必须 `needs_manual_review: true`** + 注释说明歧义点
   - **🚫 不允许字符串值** `high` / `medium` / `low`(过去翻车 42 次)
   - **样本要求**:若总页数 ≥ 20,**至少 10% 的页应当 < 0.85**(强制 LLM 不全过)
```

- [ ] **Step 7.3: 验证**

```bash
grep -nE "Idempotency check|0.92-0.98|至少 10%" .claude/agents/iloveppt-template-extractor.md
```

- [ ] **Step 7.4: Commit**

```bash
git add .claude/agents/iloveppt-template-extractor.md
git commit -m "feat(extractor): Step 3.1 idempotent + confidence 标定锚 · 防过度自信"
```

---

## Task 8: extractor.md Step 3.1.5 用 inspect_placeholders.py 骨架

**Files:**
- Modify: `.claude/agents/iloveppt-template-extractor.md` § Step 3.1.5

- [ ] **Step 8.1: 改 Step 3.1.5 「实操」段**

Find `**实操**:`(在 Step 3.1.5 段内,第 230 行附近),替换为:
```markdown
**实操(脚本产骨架,LLM 填语义)**:

1. 调脚本拿骨架:
   ```bash
   library/_rag/.venv/bin/python \
     library/pptx-templates/scripts/inspect_placeholders.py \
     library/pptx-templates/_source/<name>.pptx \
     <NN_minus_1>   # 0-indexed page idx
   ```
   产物:含 `template_page_index` / `layout_class: "?"` / `slots[].tree_path` / `slots[].raw_text_sample` / `slots[].bbox` / `slots[].font_size_pt` 的骨架 YAML

2. LLM **只**做这 3 件事(不再算 tree_path):
   - 把每个 `slot.id` 从 `"?"` 改为语义命名(`title` / `tier_1` / `card_1_body` / `step_2_callout`)
   - 把 `slot.capacity_chars` 从 `"?"` 改为字数估算(参考 bbox 几何 + font_size)
   - 浅底色 tier 加 `text_color_override: '#0B2A4A'`
   - 顶层 `layout_class` 跟 meta.yaml.draft.layout_type 同步

3. 写到 `pages/<NN-layout>/placeholder_map.yaml.draft`

**严禁**:LLM 自己写 tree_path / 自己 walk shapes / 不调脚本就编 YAML。

**Idempotency**:`placeholder_map.yaml.draft` 已存在 + `status: draft` → skip(不重生成);`placeholder_map.yaml`(用户审过的)→ 任何 mode 都不动。
```

- [ ] **Step 8.2: Commit**

```bash
git add .claude/agents/iloveppt-template-extractor.md
git commit -m "feat(extractor): Step 3.1.5 改用 inspect_placeholders.py 产骨架"
```

---

## Task 9: extractor.md Step 3.3 改调 self_check.py

**Files:**
- Modify: `.claude/agents/iloveppt-template-extractor.md` § Step 3.3

- [ ] **Step 9.1: 改 Step 3.3 整段**

Find `#### Step 3.3 · self-check 验收`(第 333 行附近),整段替换为:
```markdown
#### Step 3.3 · self-check 验收(写完所有 draft 后跑)

进 Step 4 前**必须**跑外部 self-check 脚本:

```bash
library/_rag/.venv/bin/python \
  library/pptx-templates/scripts/extractor_self_check.py <name>
echo "exit_code=$?"
```

Exit code:
- `0` = 全过 · 继续 Step 4
- `1` = 字段 / enum / id 格式 / confidence / extraction 算式 / embedding_dim / template_name 错(详见 stdout) → `code: SCHEMA_VALIDATION_FAILED`
- `2` = placeholder_map.yaml.draft tree_path 不能 resolve(builder tier1 路径会失效)→ `code: PMAP_TREE_PATH_UNRESOLVABLE`
- `3` = YAML 语法错(常见 `- "QUOTED" rest` 模式)→ `code: YAML_SYNTAX_ERROR`
- `4` = 模板目录不存在 → `code: TEMPLATE_NOT_FOUND`

Self-check 的具体校验项见 `library/pptx-templates/scripts/extractor_self_check.py` 头部 docstring。

**🚫 严禁**:自行 grep / sed / 内嵌 bash 模拟 self-check · 必须调脚本拿 exit code · 否则 校验缺失。

任一非 0 exit → `status: error` + 把 stdout 贴进 errors[].message · 等用户决策 · **不允许**自动重试修复。
```

- [ ] **Step 9.2: 验证 self_check 脚本可被调用**

```bash
.venv/bin/python library/pptx-templates/scripts/extractor_self_check.py minimal_template_ok \
  --items-root library/pptx-templates/scripts/tests/fixtures
echo "exit=$?"   # Expected: exit=0
```

- [ ] **Step 9.3: Commit**

```bash
git add .claude/agents/iloveppt-template-extractor.md
git commit -m "feat(extractor): Step 3.3 改调 self_check.py · exit-code driven"
```

---

## Task 10: extractor.md Step 4 cover 选页改 layout-aware

**Files:**
- Modify: `.claude/agents/iloveppt-template-extractor.md` § Step 4

- [ ] **Step 10.1: 改 Step 4**

Find `### Step 4 · 复制 cover 缩略`(第 388 行附近),替换:
```markdown
### Step 4 · 复制 cover 缩略(layout-aware · 不依赖 NN 顺序)

```bash
# 找 layout_type==cover 的页(模板设计师常把 cover 放第 2/3 页)
COVER_DIR=$(grep -lE "^layout_type: cover$" \
  library/pptx-templates/items/<name>/pages/*/meta.yaml.draft 2>/dev/null \
  | head -1 | xargs dirname)

if [ -n "$COVER_DIR" ]; then
  cp $COVER_DIR/preview.png library/pptx-templates/items/<name>/preview.png
else
  # 兜底:用 NN 最小的页(通常 01-*)
  FALLBACK=$(ls library/pptx-templates/items/<name>/pages/01-*/preview.png 2>/dev/null | head -1)
  [ -n "$FALLBACK" ] && cp "$FALLBACK" library/pptx-templates/items/<name>/preview.png
fi
```

若都失败 · skip · 不阻塞 Step 5 return。
```

- [ ] **Step 10.2: Commit**

```bash
git add .claude/agents/iloveppt-template-extractor.md
git commit -m "feat(extractor): Step 4 cover 选页改 layout-aware · 不依赖 NN 顺序"
```

---

## Task 11: extractor.md 整体 mode 分发图

**Files:**
- Modify: `.claude/agents/iloveppt-template-extractor.md` —— 在 「## 流程」段顶部插入分发图

- [ ] **Step 11.1: 插入 mode 分发图**

Find `## 流程`(第 68 行附近),在标题下、Step 0 之前插入:
```markdown
**mode 分发图**:

```
mode=full              → Step 0 · 1 · 2 · 2.5 · 3.0 · 3.1 · 3.1.5 · 3.2 · 3.3 · 4 · 5
mode=re_render_only    → Step 0 · 1 · 2 · 2.5 · 5           (skip Step 3 - 保留 meta)
mode=dry_run           → Step 0 · 1 · 2 · 2.5 · 5(dry_run_preview return)
mode=placeholder_map_only → Step 0 · 3.0(TodoWrite per page) · 3.1.5 · 3.3 · 5
                              (skip Step 1/2/2.5/3.1/3.2/4 - 假设 meta.yaml 已 final)
```

每个 Step 头部会说明 「mode=X 跳过此 step」。
```

- [ ] **Step 11.2: Commit**

```bash
git add .claude/agents/iloveppt-template-extractor.md
git commit -m "docs(extractor): 在流程段顶部加 mode 分发图"
```

---

## Task 12: ingest_workflow.md 同步

**Files:**
- Modify: `library/pptx-templates/ingest_workflow.md`

- [ ] **Step 12.1: 加 mode 字段说明**

Find `由 \`iloveppt-template-extractor\` agent 主导,主线程 dispatch.` 行,在下面加:
```markdown
## 模式

| mode | 用途 | step 范围 |
|---|---|---|
| `full` | 默认 · 完整 ingest 新模板 | 0-5 全跑 |
| `placeholder_map_only` | 回填工程 · 给已 ingest 模板补 placeholder_map.yaml.draft | Step 0 / 3.0 / 3.1.5 / 3.3 / 5 |
| `dry_run` | 看模板有几页 · 不写任何 draft | Step 0-2.5 + return preview |
| `re_render_only` | 只重渲染 PNG · 保留 meta(LibreOffice 升级 / dpi 调整) | Step 0-2.5,skip Step 3 |
```

- [ ] **Step 12.2: 加 scripts 引用说明**

在 `## 步骤` 段顶部,加:
```markdown
**关键脚本**:
- `library/pptx-templates/scripts/inspect_placeholders.py` —— Step 3.1.5 产 placeholder_map.yaml.draft 骨架
- `library/pptx-templates/scripts/extractor_self_check.py` —— Step 3.3 自检 · exit code 0/1/2/3/4
- `library/_rag/render_pages.py` —— Step 2 渲染 PNG(soffice/pdftoppm 已加 timeout)
```

- [ ] **Step 12.3: 把验收 checklist 段改为引用脚本**

Find `## 验收 checklist(extractor 跑完 self-check)`(第 186 行附近),整段替换为:
```markdown
## 验收 checklist(extractor 跑完 self-check)

不再内嵌 bash · 跑外部脚本:
```bash
library/_rag/.venv/bin/python \
  library/pptx-templates/scripts/extractor_self_check.py <name>
```

Exit code: 0=全过 / 1=字段 enum 错 / 2=pmap tree_path 错 / 3=YAML 语法 / 4=目录不存在。
脚本会校验 9 项(YAML 语法 / 模板字段 / 页字段 / enum / id 格式 + 唯一 / confidence 数字+范围 / embedding_dim==1152 / extraction 算式 / pmap tree_path resolve)。
```

- [ ] **Step 12.4: Commit**

```bash
git add library/pptx-templates/ingest_workflow.md
git commit -m "docs(ingest_workflow): 同步 mode 字段 + scripts 引用 + self-check 改外部脚本"
```

---

## Task 13: 集成测试 — self_check.py 单跑 + dry_run 路径

**Files:**(只跑命令,不改文件)

- [ ] **Step 13.1: 跑 pytest 全套**

```bash
.venv/bin/pytest library/pptx-templates/scripts/tests/ -v
```
Expected: 12+ passed

- [ ] **Step 13.2: 手动验证 self_check 能跑 + 输出正确**

```bash
# 全过样本
.venv/bin/python library/pptx-templates/scripts/extractor_self_check.py minimal_template_ok \
  --items-root library/pptx-templates/scripts/tests/fixtures
echo "exit=$?"   # Expected: 0

# enum 错样本
.venv/bin/python library/pptx-templates/scripts/extractor_self_check.py bad_enum \
  --items-root library/pptx-templates/scripts/tests/fixtures
echo "exit=$?"   # Expected: 1,stdout 含 ENUM_VIOLATION
```

- [ ] **Step 13.3: 手动验证 inspect_placeholders 能跑**

```bash
.venv/bin/python library/pptx-templates/scripts/inspect_placeholders.py \
  library/pptx-templates/scripts/tests/fixtures/sample.pptx 0
# Expected: YAML 输出含 slots[] · tree_path · raw_text_sample
```

- [ ] **Step 13.4: 手动验证 render_pages 超时不影响正常路径**

```bash
SAMPLE_PPTX=$(ls library/pptx-templates/_source/*.pptx 2>/dev/null | head -1)
if [ -n "$SAMPLE_PPTX" ]; then
  NAME=$(basename "$SAMPLE_PPTX" .pptx)
  # 不 ingest 进 items/,只验证 render 链路 OK
  echo "render test on $NAME"
  # 实际跑会写文件,这里只 dry-check 命令构造 OK
  library/_rag/.venv/bin/python library/_rag/render_pages.py --help 2>&1 | head -3
fi
```

---

## Task 14: 集成测试 — agent prompt 改动 grep 验证

**Files:**(只跑命令,不改文件)

- [ ] **Step 14.1: grep 关键字段都在**

```bash
F=.claude/agents/iloveppt-template-extractor.md
echo "=== mode 入参 ==="
grep -nE "^mode:" $F | head
echo "=== 4 个 mode 值 ==="
for m in full placeholder_map_only dry_run re_render_only; do
  count=$(grep -c "$m" $F)
  echo "$m: $count occurrences"
done
echo "=== Step 0 错误码 ==="
grep -nE "INVALID_MODE|NAME_INVALID_CHARS|DISK_LOW|ALREADY_INGESTED|META_NOT_FOUND|SOURCE_SHA_MISMATCH|RENDER_TIMEOUT" $F
echo "=== self_check / inspect_placeholders 脚本引用 ==="
grep -nE "extractor_self_check.py|inspect_placeholders.py" $F
echo "=== confidence 标定锚 ==="
grep -nE "0.92-0.98|至少 10%" $F
```

Expected: 每段都至少 1 个命中 · 无空 grep。

- [ ] **Step 14.2: 在 audited file 上跑 self_check(应该无入库数据 · exit 4)**

```bash
.venv/bin/python library/pptx-templates/scripts/extractor_self_check.py template_golden
echo "exit=$?"   # Expected: 4 (TEMPLATE_NOT_FOUND · 因当前 items/ 已被 cleanup)
```

- [ ] **Step 14.3: 最终 git status 检查**

```bash
git status --short | grep -vE "^ D library/pptx-templates/items/" | head -30
```

应只看到本计划新增 / 修改的文件,**不**应看到 `M library/pptx-templates/items/...`(没污染 cleanup 区)。

---

## Self-Review

**Spec coverage:**
- ✅ P0.1 Resumable extraction → Task 5/6/7(Step 1/2/3 各加 idempotency check)
- ✅ P0.2 mode 字段 → Task 4(入参契约)+ Task 11(分发图)+ Task 6(dry_run 出口)
- ✅ P0.3 Self-check 抽脚本 + 9 项校验 → Task 1(主体)+ Task 2.6/2.7(tree_path)+ Task 9(prompt 改调)
- ✅ P0.4 inspect_placeholders.py → Task 2(主体)+ Task 8(prompt 改调)
- ✅ P1.5 Step 0 校验加危险字符 / disk space / overwrite → Task 4
- ✅ P1.6 Step 1 sha256 idempotent → Task 5
- ✅ P1.7 render_pages.py 超时 → Task 3
- ✅ P1.8 Step 4 cover 选页 layout-aware → Task 10
- ✅ P1.9 confidence 标定锚 → Task 7

**Placeholder scan:** 全部代码块都是完整可执行内容 · 无 TBD / "implement later" / "add validation"。

**Type consistency:**
- `extractor_self_check.py` 的 exit code(0/1/2/3/4)在 Task 1 / 2 / 9 / 14 全部一致
- `inspect_placeholders.py` 的输出 schema(`template_page_index` / `layout_class` / `slots[].tree_path` 等)在 Task 2 / 8 一致
- mode enum(`full` / `placeholder_map_only` / `dry_run` / `re_render_only`)在 Task 4 / 6 / 7 / 11 / 12 都用同一拼写

**P2 范围内未做的(预期):**
- Telemetry(耗时 / token) — 用户没选
- Anti-pattern 补 2 条 — 用户没选
- enum 颗粒度 / variant 强 schema — 用户没选(等下次 sprint 数据驱动)
- embed_text.py / embed_image.py 加 status==approved gate — 不在 extractor 范围 · 是 P0.2 数据层问题

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-27-extractor-p0-p1.md`. Two execution options:

**1. Subagent-Driven (recommended)** — 主线程 dispatch 一个 fresh subagent 跑 1 个 task,我 review,再下一个。隔离 + 快速迭代。

**2. Inline Execution** — 当前 session 顺序跑,中间几个 checkpoint 让你 review。

哪个?
