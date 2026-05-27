#!/usr/bin/env python3
"""Check sha256 drift between approved meta.yaml and the live _source .pptx (P3-15).

Walks every template under `library/pptx-templates/items/<name>/meta.yaml`,
reads `provenance.source_pptx_sha256`, computes sha256 of the matching
`library/pptx-templates/_source/<name>.pptx`, and emits a markdown table.

Useful for CI (`exit 1` when any template drifted) or manual drift sweeps.

Exit codes:
  0 = all templates match (or no templates found)
  1 = at least one template has sha drift / missing source
  2 = items/_source layout invalid
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import yaml

DEFAULT_TEMPLATES_ROOT = Path(__file__).resolve().parents[2] / "pptx-templates"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_meta(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        return None


def check(templates_root: Path) -> tuple[list[dict], int]:
    items_root = templates_root / "items"
    source_root = templates_root / "_source"
    if not items_root.is_dir() or not source_root.is_dir():
        print(f"LAYOUT_INVALID: items={items_root} source={source_root}", file=sys.stderr)
        return [], 2

    rows: list[dict] = []
    overall_exit = 0

    for meta_path in sorted(items_root.glob("*/meta.yaml")):
        name = meta_path.parent.name
        source_pptx = source_root / f"{name}.pptx"
        row = {
            "name": name,
            "declared_sha": None,
            "actual_sha": None,
            "declared_version": None,
            "status": "?",
            "note": "",
        }

        meta = load_meta(meta_path)
        if not isinstance(meta, dict):
            row["status"] = "META_INVALID"
            row["note"] = f"could not parse {meta_path}"
            overall_exit = 1
            rows.append(row)
            continue

        prov = meta.get("provenance") or {}
        declared_sha = prov.get("source_pptx_sha256")
        declared_version = prov.get("source_pptx_version")
        row["declared_sha"] = declared_sha
        row["declared_version"] = declared_version

        if not source_pptx.exists():
            row["status"] = "SOURCE_MISSING"
            row["note"] = f"missing {source_pptx.relative_to(templates_root)}"
            overall_exit = 1
            rows.append(row)
            continue

        actual_sha = sha256_of(source_pptx)
        row["actual_sha"] = actual_sha

        if not declared_sha:
            row["status"] = "NO_DECLARED_SHA"
            row["note"] = "meta.yaml missing provenance.source_pptx_sha256"
            overall_exit = 1
        elif declared_sha != actual_sha:
            row["status"] = "DRIFT"
            row["note"] = (
                "source .pptx changed since ingest — re-run inspect_placeholders.py "
                "and bump source_pptx_version"
            )
            overall_exit = 1
        else:
            row["status"] = "OK"

        rows.append(row)

    return rows, overall_exit


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "| Template | Status | Declared SHA | Actual SHA | Version | Note |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        d = (r["declared_sha"] or "")[:12] or "—"
        a = (r["actual_sha"] or "")[:12] or "—"
        v = r["declared_version"] or "—"
        lines.append(
            f"| `{r['name']}` | **{r['status']}** | `{d}` | `{a}` | {v} | {r['note']} |"
        )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Check template .pptx sha drift")
    ap.add_argument("--templates-root", type=Path, default=DEFAULT_TEMPLATES_ROOT,
                    help="library/pptx-templates root (default: relative to this script)")
    ap.add_argument("--format", choices=("markdown", "plain"), default="markdown")
    args = ap.parse_args()

    rows, exit_code = check(args.templates_root)
    if not rows:
        print("No templates found.")
        sys.exit(exit_code)

    if args.format == "markdown":
        print(render_markdown(rows))
    else:
        for r in rows:
            print(f"{r['name']}\t{r['status']}\t{r['note']}")

    # Trailing summary line for shell consumers
    ok = sum(1 for r in rows if r["status"] == "OK")
    print(f"\n_Summary: {ok}/{len(rows)} OK · exit={exit_code}_")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
