#!/usr/bin/env python3
"""
clip_chapter.py · P3-14 helper

跨 deck 章节复制 · 从 source content.md 抽 `## N. ...` 章节,append 到 target content.md。

Usage:
  # 经典语法
  scripts/clip_chapter.py decks/A/author/deck_v1_content.md --chapter 5 \\
                          --target decks/B/author/deck_v1_content.md

  # URL-fragment 风格(等价)
  scripts/clip_chapter.py decks/A/author/deck_v1_content.md#5 \\
                          --to decks/B/author/deck_v1_content.md

  # 指定插入位置(在 chapter N 之后,而非 append)
  scripts/clip_chapter.py decks/A/.../content.md --chapter 5 \\
                          --target decks/B/.../content.md --insert-after 3

  # 看会做什么
  scripts/clip_chapter.py decks/A/.../content.md --chapter 5 \\
                          --target decks/B/.../content.md --dry-run

行为:
  1. Read source content.md · 找 `## N. ...` chapter heading
  2. 提取该 chapter 完整内容(直到下一个 `## ` 或 EOF)
  3. 拷贝 layout / pattern 注释 + 正文 + 数据 source
  4. 若有图片引用 `![](charts/X.png)`:把 X.png 复制到 target deck 的 author/charts/(同名 · 已存在则跳过 或 --overwrite-images)
  5. append 到 target content.md(或 --insert-after <chapter> 指定位置)
  6. 自动 renumber: 新章节用 target 现有最大 chapter idx + 1(避免数字冲突)
  7. dry-run:print 会做什么 · 不真改

依赖:仅 stdlib · 不调 LLM。
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parent.parent

# Heading regex (与 scripts/derive_plan.py 保持一致)
CHAPTER_HEADING_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$", re.M)
SPECIAL_HEADING_RE = re.compile(r"^##\s+\[([a-z_]+)\]\s*(.*?)\s*$", re.M)
ANY_H2_RE = re.compile(r"^##\s+", re.M)
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


def parse_source_spec(spec: str) -> tuple[Path, Optional[int]]:
    """
    Parse 'path#N' or 'path' into (Path, optional chapter int).
    """
    if "#" in spec:
        path_str, _, frag = spec.partition("#")
        try:
            chap = int(frag)
        except ValueError:
            raise SystemExit(f"ERROR: URL-fragment 必须是 int chapter(got '{frag}')")
        return Path(path_str), chap
    return Path(spec), None


def find_chapter(text: str, chapter_num: int) -> tuple[int, int, str]:
    """
    Return (start_offset_in_body, end_offset_in_body, chapter_title).
    Offsets relative to 'body' (post-frontmatter slice).

    Raises SystemExit if not found.
    """
    fm_m = FRONTMATTER_RE.match(text)
    body_start = fm_m.end() if fm_m else 0
    body = text[body_start:]

    # Find target heading
    target_match = None
    for m in CHAPTER_HEADING_RE.finditer(body):
        if int(m.group(1)) == chapter_num:
            target_match = m
            break
    if target_match is None:
        raise SystemExit(f"ERROR: source 里没找到 '## {chapter_num}. ...' 章节")

    title = target_match.group(2)
    start = target_match.start()

    # Find next ## heading (any kind)
    next_m = ANY_H2_RE.search(body, target_match.end())
    end = next_m.start() if next_m else len(body)

    # offsets are relative to body; caller wants absolute file offset
    return body_start + start, body_start + end, title


def extract_image_refs(chapter_text: str) -> list[tuple[str, str]]:
    """Return list of (alt_text, path) for image refs in chapter."""
    return [(m.group(1), m.group(2)) for m in IMAGE_RE.finditer(chapter_text)]


def get_max_chapter_num(target_text: str) -> int:
    """Get the largest chapter number in target. Returns 0 if none."""
    max_n = 0
    for m in CHAPTER_HEADING_RE.finditer(target_text):
        n = int(m.group(1))
        if n > max_n:
            max_n = n
    return max_n


def renumber_chapter(chapter_text: str, new_num: int) -> str:
    """Replace first `## OLD. ...` heading with `## NEW. ...`."""
    return CHAPTER_HEADING_RE.sub(
        lambda m: f"## {new_num}. {m.group(2)}",
        chapter_text,
        count=1,
    )


def find_insert_position(target_text: str, after_chapter: int) -> int:
    """
    Return offset where chapter content should be inserted (i.e. end of chapter after_chapter).

    If chapter not found · raise SystemExit.
    """
    fm_m = FRONTMATTER_RE.match(target_text)
    body_start = fm_m.end() if fm_m else 0
    body = target_text[body_start:]

    target_match = None
    for m in CHAPTER_HEADING_RE.finditer(body):
        if int(m.group(1)) == after_chapter:
            target_match = m
            break
    if target_match is None:
        raise SystemExit(f"ERROR: target 里没找到 '## {after_chapter}. ...' 章节(--insert-after 失败)")

    # Find next ## heading after this chapter
    next_m = ANY_H2_RE.search(body, target_match.end())
    end = next_m.start() if next_m else len(body)
    return body_start + end


def copy_images(image_refs: list[tuple[str, str]], source_md: Path, target_md: Path,
                dry_run: bool, overwrite: bool) -> list[str]:
    """
    Resolve image paths relative to source_md, copy to <target_md_dir>/<same relative path>.

    Returns list of action strings for logging.
    """
    actions = []
    source_dir = source_md.parent.resolve()
    target_dir = target_md.parent.resolve()
    for alt, raw_path in image_refs:
        # Skip absolute or remote
        if raw_path.startswith(("http://", "https://", "/")):
            actions.append(f"  skip image(abs / remote): {raw_path}")
            continue
        src_img = (source_dir / raw_path).resolve()
        dst_img = (target_dir / raw_path).resolve()
        if not src_img.exists():
            actions.append(f"  WARN: source image not found, skipping: {src_img}")
            continue
        if dst_img.exists() and not overwrite:
            actions.append(f"  image exists, skipping(use --overwrite-images): {dst_img.relative_to(REPO) if REPO in dst_img.parents else dst_img}")
            continue
        actions.append(
            f"  copy image: "
            f"{src_img.relative_to(REPO) if REPO in src_img.parents else src_img} -> "
            f"{dst_img.relative_to(REPO) if REPO in dst_img.parents else dst_img}"
        )
        if not dry_run:
            dst_img.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src_img, dst_img)
        # ALSO try to copy "source" sidecar(.py / .drawio / .mmd / .source.yaml)same stem
        for sidecar_ext in (".py", ".drawio", ".mmd", ".source.yaml"):
            cand = src_img.with_suffix(sidecar_ext)
            if cand.exists():
                dst_side = dst_img.with_suffix(sidecar_ext)
                if dst_side.exists() and not overwrite:
                    actions.append(f"  sidecar exists, skipping: {dst_side.name}")
                    continue
                actions.append(
                    f"  copy sidecar: "
                    f"{cand.relative_to(REPO) if REPO in cand.parents else cand} -> "
                    f"{dst_side.relative_to(REPO) if REPO in dst_side.parents else dst_side}"
                )
                if not dry_run:
                    shutil.copyfile(cand, dst_side)
    return actions


def cmd_clip(source_path: Path, chapter_num: int, target_path: Path,
             insert_after: Optional[int], dry_run: bool, overwrite_images: bool) -> int:
    if not source_path.exists():
        print(f"ERROR: source not found: {source_path}", file=sys.stderr)
        return 2
    if not target_path.exists():
        print(f"ERROR: target not found: {target_path}", file=sys.stderr)
        return 2

    source_text = source_path.read_text(encoding="utf-8")
    target_text = target_path.read_text(encoding="utf-8")

    start, end, title = find_chapter(source_text, chapter_num)
    chapter_text = source_text[start:end].rstrip() + "\n"

    # Decide new chapter number for target
    max_in_target = get_max_chapter_num(target_text)
    new_num = max_in_target + 1
    renumbered = renumber_chapter(chapter_text, new_num)

    # Detect images
    images = extract_image_refs(chapter_text)

    action = "Would" if dry_run else "Will"
    print(f"{action} clip chapter {chapter_num} from {source_path}", file=sys.stderr)
    print(f"  Chapter title       : {title}", file=sys.stderr)
    print(f"  Source heading      : ## {chapter_num}. {title}", file=sys.stderr)
    print(f"  Target renumbered to: ## {new_num}. {title}", file=sys.stderr)
    print(f"  Target file         : {target_path}", file=sys.stderr)
    if insert_after is not None:
        print(f"  Insert after chapter: {insert_after}", file=sys.stderr)
    else:
        print(f"  Insert position     : append to end", file=sys.stderr)
    print(f"  Image refs detected : {len(images)}", file=sys.stderr)

    # Image copy actions
    img_actions = copy_images(images, source_path, target_path, dry_run, overwrite_images)
    for a in img_actions:
        print(a, file=sys.stderr)

    # Compute new target text
    if insert_after is not None:
        insert_pos = find_insert_position(target_text, insert_after)
        # Make sure we have a leading blank line and trailing one
        new_block = "\n" + renumbered.strip() + "\n"
        new_text = target_text[:insert_pos].rstrip() + "\n\n" + new_block.strip() + "\n\n" + target_text[insert_pos:].lstrip()
    else:
        # Append at end · ensure single trailing newline
        sep = "" if target_text.endswith("\n\n") else ("\n" if target_text.endswith("\n") else "\n\n")
        new_text = target_text + sep + renumbered.strip() + "\n"

    if dry_run:
        print("\n--- preview · 将 append/insert 的内容 ---", file=sys.stderr)
        print(renumbered, file=sys.stderr)
        print("(dry-run · 没有真改 target)", file=sys.stderr)
        return 0

    # Write back
    target_path.write_text(new_text, encoding="utf-8")
    print(f"  OK · target updated. {target_path}", file=sys.stderr)
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="clip_chapter.py",
        description="P3-14 · 跨 deck 章节复制 · source `## N. ...` -> target append/insert.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  scripts/clip_chapter.py decks/A/author/deck_v1_content.md \\\n"
            "                          --chapter 5 \\\n"
            "                          --target decks/B/author/deck_v1_content.md\n"
            "  scripts/clip_chapter.py decks/A/author/deck_v1_content.md#5 \\\n"
            "                          --to decks/B/author/deck_v1_content.md\n"
            "  scripts/clip_chapter.py ... --chapter 5 --target ... --insert-after 3\n"
        ),
    )
    parser.add_argument(
        "source",
        help="source content.md(可带 #N URL-fragment 指定 chapter)",
    )
    parser.add_argument(
        "--chapter",
        "-c",
        type=int,
        help="source 里的 chapter 数(若 source 含 #N 可省)",
    )
    # 两个等价 alias: --target / --to
    parser.add_argument(
        "--target",
        "--to",
        "-t",
        required=True,
        dest="target",
        help="target content.md path",
    )
    parser.add_argument(
        "--insert-after",
        type=int,
        help="指定插入位置(在 target 的第 N chapter 之后);省略 = append 到 EOF",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="只打印会做什么 · 不真改",
    )
    parser.add_argument(
        "--overwrite-images",
        action="store_true",
        help="若 target 已有同名图片,覆盖(默认跳过)",
    )

    args = parser.parse_args(argv)

    source_path, frag_chap = parse_source_spec(args.source)
    chapter = args.chapter if args.chapter is not None else frag_chap
    if chapter is None:
        parser.error("缺 chapter:加 --chapter N 或在 source 后加 #N")

    target_path = Path(args.target)

    return cmd_clip(
        source_path=source_path,
        chapter_num=chapter,
        target_path=target_path,
        insert_after=args.insert_after,
        dry_run=args.dry_run,
        overwrite_images=args.overwrite_images,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
