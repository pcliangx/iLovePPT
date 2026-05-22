# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

iLovePPT is a **Claude Code skill library** — not a standalone application. The deliverable is the `skills/` directory: three skills (`pptx-deck`, `pptx`, `diagram`), each consisting of a `SKILL.md` entry doc, child `.md` docs, and Python helper modules. When installed into a project's `.claude/skills/`, Claude reads these docs at runtime to generate PowerPoint decks end-to-end.

The repo is consumed two ways: (1) as a skill library other projects link into `.claude/skills/`; (2) directly via `python3 skills/pptx-deck/workflow.py <brief.yaml>`.

## Commands

```bash
# Run all tests (35 tests; pythonpath auto-configured via pyproject.toml)
python3 -m pytest tests/ -v

# Run a single test
python3 -m pytest tests/pptx/test_helpers.py::test_set_font_writes_ea_typeface -v

# Check external dependencies (python-pptx, soffice, pdftoppm, fonts)
bash skills/pptx/scripts/check_deps.sh

# End-to-end: generate a deck from a brief
python3 skills/pptx-deck/workflow.py skills/pptx-deck/examples/demo_brief.yaml

# Smoke tests (exercise the helper + render pipeline)
python3 skills/pptx/examples/minimal_deck.py     # → /tmp/iloveppt_minimal.pptx
bash skills/diagram/examples/render.sh           # → skills/diagram/examples/minimal.png

# Render a .pptx for visual inspection
soffice --headless --convert-to pdf <file>.pptx --outdir /tmp/
pdftoppm -jpeg -r 120 /tmp/<file>.pdf /tmp/slide
```

No build step and no linter are configured.

## Architecture

### Three-skill layering

```
pptx-deck  ── orchestrator: brief.yaml → complete .pptx
   ├── calls → pptx     (helpers.py, office scripts, render pipeline)
   └── calls → diagram  (draw.io / mermaid / matplotlib → PNG)
pptx       ── low-level .pptx read/write; also usable standalone
diagram    ── diagram generation; also usable standalone
```

### Python files are runnable skeletons; Claude supplies the intelligence

The most important thing to understand: the `.py` files implement the **mechanical pipeline**, not the content intelligence.

- `workflow.py:generate_outline()` returns a fixed, simplified structure. The *real* per-page content expansion is performed by Claude following the prompt templates in `content-writing.md`.
- `workflow.py:vision_check()` is a placeholder returning `[]`. The *real* per-page visual QA is performed by Claude reading the rendered PNG against the 12-point checklist in `visual-qa.md`.
- `workflow.py:fix_slide()` handles only 2 mechanical fixes (font-size reduction, margin reset); anything else needs Claude.

When improving generation *quality*, edit the prompt docs (`content-writing.md`, `visual-qa.md`), not just the Python.

### SSOT standard — helpers.py is the single source of truth

`skills/pptx/helpers.py` is the authoritative definition for two things; nothing downstream may redefine them, only reference or extend:

1. **Low-level pptx operations** — every font/shape/table primitive (`set_font`, `_fix_ph_font`, `card`, `bullets`, `table_modern`, `section_header`, etc.). Theme modules build their `make_*` layout functions on top of these; never duplicate font/shape logic into a theme.
2. **Design tokens** — fonts (`FONT_CN`, `FONT_NUM`), brand colors (`BRAND_PRIMARY`, `BRAND_DARK`, `BRAND_TINT`, `ACCENT`), grays, and slide dimensions (`SLIDE_W`, `SLIDE_H`). `tech_blue.py` does **not** redefine these — it aliases them (`PRIMARY = H.BRAND_PRIMARY`, `FONT_HEADER = H.FONT_CN`). `workflow.py` uses `H.SLIDE_W/H` rather than hardcoded `Inches(...)`.

Consequences for changes:
- Changing a color or font = editing `helpers.py` in **one** place; it propagates to the theme and every helper default.
- Markdown docs cannot import, so hex values in `design-system.md` / `diagram/*.md` are **labelled copies** — they cite `helpers.py` as authoritative and must be re-synced by hand if the palette changes.
- A genuinely different theme (e.g. a future `party_red.py`) may define its own palette — that is a new SSOT scope, not a duplication. The rule forbids re-stating the *same* value, not having distinct themes.

### Skill docs are the product

The `SKILL.md` + child `.md` files are not auxiliary documentation — they are what Claude reads at runtime to know how to generate decks. Editing them changes product behavior. They cross-reference each other with `[[skill-name]]` syntax.

`skills/pptx/scripts/office/` is vendored verbatim from Anthropic's pptx skill — do not modify it.

## Core principle — 一图胜千文 (a picture beats a thousand words)

Content that expresses structure, flow, relationships, or data comparison should become a **diagram**, not a wall of bullet text. When generating or reviewing a deck, actively use AI drawing capability (the `diagram` skill) for such content; when in doubt, draw it. This principle is enforced operationally by the `plan_diagrams` step (workflow Step 3) and documented in `skills/pptx-deck/diagram-planning.md`. Any change to generation behavior should preserve this bias toward visuals.

## Critical invariants

- **Chinese fonts must be written via lxml `<a:ea>` + `<a:cs>`** (`helpers.py:set_font`). python-pptx's default `font.name` only writes `<a:latin>`, so Chinese text falls back to an ugly font cross-platform. This is the #1 source of broken output.
- **Default font is Microsoft YaHei** (a deliberate project decision). `PingFang SC` / `Heiti SC` appear only in the fallback chain, never as a default. macOS needs Microsoft YaHei installed for LibreOffice rendering to match Windows PowerPoint.
- **Placeholder fonts need `_fix_ph_font`, not `set_font`.** Placeholders inherit `<a:ea>` from the slide master; run-level `set_font` cannot reach that layer.
- **Tests verify structure, not visuals.** They check shape counts and font attributes — a layout can render visually broken and still pass. After any layout/helper change, render to PNG and inspect.

## Conventions

- Commit messages use conventional commits with a scope: `feat(pptx-deck):`, `fix(pptx):`, `docs(diagram):`, `refactor:`, `test(pptx):`, `chore:`.
- `pyproject.toml` sets `pythonpath = ["skills/pptx", "skills/pptx-deck"]`, so tests import `helpers` / `themes.tech_blue` / `workflow` directly with no `sys.path` hacks. Non-test modules keep an idempotent `sys.path.insert` for direct script execution.
- The design spec and implementation plan live in `docs/superpowers/specs/` and `docs/superpowers/plans/` — read them for the rationale behind the three-skill split and the per-page visual-QA loop.
