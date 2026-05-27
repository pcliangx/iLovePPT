#!/usr/bin/env python3
"""把 library/pptx-templates/_source/<name>.pptx 渲染成每页 PNG。

用法:
    .venv/bin/python render_pages.py <name>
    .venv/bin/python render_pages.py template_golden --dpi 120

会:
    1. soffice --headless --convert-to pdf <pptx> --outdir <tmp>
    2. pdftoppm -png -r <dpi> <pdf> <tmp>/page
    3. 把 page-N.png 复制到 library/pptx-templates/items/<name>/pages/<NN-page>/preview.png
       (NN-page 占位名,ingest agent 后续 rename 为 01-cover 等)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
LIBRARY_ROOT = SCRIPT_DIR.parent
TPL_ROOT = LIBRARY_ROOT / "pptx-templates"


def _which(name: str) -> Path | None:
    p = shutil.which(name)
    return Path(p) if p else None


def render(name: str, dpi: int = 120) -> list[Path]:
    pptx = TPL_ROOT / "_source" / f"{name}.pptx"
    if not pptx.exists():
        print(f"ERROR: 源 .pptx 不存在: {pptx}", file=sys.stderr)
        sys.exit(1)

    if not _which("soffice"):
        print("ERROR: soffice(LibreOffice)未装。bash .claude/skills/pptx/scripts/check_deps.sh", file=sys.stderr)
        sys.exit(1)
    if not _which("pdftoppm"):
        print("ERROR: pdftoppm 未装。", file=sys.stderr)
        sys.exit(1)

    item_dir = TPL_ROOT / "items" / name
    item_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"render_{name}_") as td:
        td_path = Path(td)
        print(f"[render] soffice {pptx.name} → pdf ...", flush=True)
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
        pdf_files = list(td_path.glob("*.pdf"))
        if not pdf_files:
            print("ERROR: soffice 未产 PDF", file=sys.stderr)
            sys.exit(1)
        pdf = pdf_files[0]
        print(f"[render] pdftoppm -r {dpi} {pdf.name} → png ...", flush=True)
        try:
            subprocess.run(
                ["pdftoppm", "-png", "-r", str(dpi), str(pdf), str(td_path / "page")],
                check=True,
                capture_output=True,
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            print("ERROR: pdftoppm 渲染超时 (180s) - RENDER_TIMEOUT", file=sys.stderr)
            sys.exit(2)
        pages = sorted(td_path.glob("page-*.png"))
        if not pages:
            print("ERROR: 无 page-*.png", file=sys.stderr)
            sys.exit(1)

        produced: list[Path] = []
        for i, src in enumerate(pages, 1):
            slot = item_dir / "pages" / f"{i:02d}-page"
            slot.mkdir(parents=True, exist_ok=True)
            dst = slot / "preview.png"
            shutil.copy2(src, dst)
            produced.append(dst)
        print(f"[render] {len(produced)} pages → {item_dir}/pages/", flush=True)
        return produced


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name", help="模板名 · 对应 library/pptx-templates/_source/<name>.pptx")
    p.add_argument("--dpi", type=int, default=120)
    args = p.parse_args()
    render(args.name, args.dpi)


if __name__ == "__main__":
    main()
