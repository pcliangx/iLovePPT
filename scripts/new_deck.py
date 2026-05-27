#!/usr/bin/env python3
"""
new_deck.py · P3-8 helper

从 library/deck-skeletons/ 起新 deck workspace · 可选指定 skeleton。

Usage:
  # 用 quarterly_finance_report skeleton 起新 deck
  scripts/new_deck.py 2026-q2-report --skeleton quarterly_finance_report

  # 看会做什么(不真建)
  scripts/new_deck.py 2026-q2-report --skeleton quarterly_finance_report --dry-run

  # 不带 --skeleton(空白 deck workspace)
  scripts/new_deck.py my-deck

  # 看可用 skeleton 列表
  scripts/new_deck.py --list-skeletons

行为(--skeleton 模式):
  1. mkdir decks/<name>/{brainstorm,author,critic,builder,audience}
  2. cp library/deck-skeletons/<skeleton>/skeleton.yaml -> decks/<name>/brainstorm/skeleton_used.yaml
  3. cp library/deck-skeletons/<skeleton>/outline.md.tmpl -> decks/<name>/author/deck_v1_outline.md.draft
  4. 打印 next-step 指引

行为(无 --skeleton):
  1. mkdir decks/<name>/{brainstorm,author,critic,builder,audience}
  2. 打印 next-step 指引(让 brainstorm 自由收 brief)

不调用 LLM · 不依赖第三方包(只 stdlib + 仓库已有 yaml)。
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parent.parent
SKELETONS_DIR = REPO / "library" / "deck-skeletons"
DECKS_DIR = REPO / "decks"

WORKSPACE_SUBDIRS = ["brainstorm", "author", "critic", "builder", "audience"]


def list_skeletons() -> list[Path]:
    """Return sorted list of skeleton dirs (each must contain skeleton.yaml + outline.md.tmpl)."""
    if not SKELETONS_DIR.exists():
        return []
    found = []
    for child in sorted(SKELETONS_DIR.iterdir()):
        if not child.is_dir():
            continue
        if (child / "skeleton.yaml").exists() and (child / "outline.md.tmpl").exists():
            found.append(child)
    return found


def cmd_list_skeletons() -> int:
    skeletons = list_skeletons()
    if not skeletons:
        print(f"(no skeletons found under {SKELETONS_DIR})", file=sys.stderr)
        return 1
    print(f"Available skeletons under {SKELETONS_DIR.relative_to(REPO)}:")
    for s in skeletons:
        # First non-comment 'description:' line as short label
        desc = "(no description)"
        yaml_path = s / "skeleton.yaml"
        try:
            for line in yaml_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("description:"):
                    desc = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                    break
        except OSError:
            pass
        print(f"  - {s.name:30s}  {desc}")
    return 0


def parse_skeleton_yaml(skeleton_yaml: Path) -> dict:
    """
    Minimal yaml reader · top-level scalar + simple list (one-per-line `- value`) fields.
    Avoids depending on PyYAML for the helper script.

    Supports:
      key: value           -> str
      key:
        - a
        - b                -> ["a", "b"]
    """
    info: dict = {}
    if not skeleton_yaml.exists():
        return info
    lines = skeleton_yaml.read_text(encoding="utf-8").splitlines()
    current_list_key: Optional[str] = None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Continuation of a list collected for current_list_key
        if current_list_key and (line.startswith(" ") or line.startswith("\t")):
            if stripped.startswith("- "):
                item = stripped[2:].strip().strip('"').strip("'")
                info.setdefault(current_list_key, []).append(item)
                continue
            # nested non-list → end list collection
            current_list_key = None
            continue
        # Top-level key
        if line.startswith(" ") or line.startswith("\t"):
            continue
        if ":" not in line:
            current_list_key = None
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if not value:
            # next lines may be a list
            current_list_key = key
            continue
        # Strip inline yaml-style quoting
        value = value.strip('"').strip("'")
        info[key] = value
        current_list_key = None
    return info


def emit_next_step_message(deck_name: str, skeleton_name: Optional[str], skeleton_info: dict) -> str:
    deck_rel = Path("decks") / deck_name
    lines = [
        "",
        f"  Deck workspace ready: {deck_rel}/",
        "",
    ]
    if skeleton_name:
        lines += [
            f"  Skeleton: {skeleton_name}",
        ]
        if "name" in skeleton_info:
            lines.append(f"    {skeleton_info['name']}")
        if "description" in skeleton_info:
            lines.append(f"    {skeleton_info['description']}")
        sa = skeleton_info.get("suggested_audience")
        st = skeleton_info.get("suggested_theme")
        sd = skeleton_info.get("suggested_duration_min")
        sm = skeleton_info.get("suggested_presentation_mode")
        sa_render = ", ".join(sa) if isinstance(sa, list) else sa
        lines.append("")
        if sa or st or sd or sm:
            lines.append("  Suggested defaults (brainstorm 会确认):")
            if sa:
                lines.append(f"    audience           = [{sa_render}]" if isinstance(sa, list) else f"    audience           = {sa}")
            if st:
                lines.append(f"    theme              = {st}")
            if sd:
                lines.append(f"    duration_min       = {sd}")
            if sm:
                lines.append(f"    presentation_mode  = {sm}")
            lines.append("")
        lines += [
            "  Files placed:",
            f"    {deck_rel}/brainstorm/skeleton_used.yaml",
            f"    {deck_rel}/author/deck_v1_outline.md.draft",
            "",
        ]
    lines += [
        "  Next step:",
        f'    cd {deck_rel}',
        '    跟主线程说 "做 PPT"' + (" · 用 skeleton" if skeleton_name else ""),
        "",
        "  brainstorm 会读取 skeleton_used.yaml(如有) · 跟你确认 / 调整 brief 字段。",
        "",
    ]
    return "\n".join(lines)


def create_workspace(deck_dir: Path, dry_run: bool) -> list[str]:
    created = []
    for sub in WORKSPACE_SUBDIRS:
        target = deck_dir / sub
        if target.exists():
            continue
        created.append(str(target.relative_to(REPO)))
        if not dry_run:
            target.mkdir(parents=True, exist_ok=True)
    return created


def cmd_new_deck(name: str, skeleton: Optional[str], dry_run: bool, force: bool) -> int:
    deck_dir = DECKS_DIR / name
    if deck_dir.exists() and any(deck_dir.iterdir()) and not force:
        print(
            f"ERROR: decks/{name}/ already exists and is non-empty.",
            f"  Use --force to overwrite skeleton files,",
            "  or pick a new name.",
            sep="\n",
            file=sys.stderr,
        )
        return 2

    skeleton_dir: Optional[Path] = None
    if skeleton:
        skeleton_dir = SKELETONS_DIR / skeleton
        if not (skeleton_dir / "skeleton.yaml").exists():
            print(
                f"ERROR: skeleton '{skeleton}' not found under {SKELETONS_DIR.relative_to(REPO)}/.",
                "  Run with --list-skeletons to see available skeletons.",
                sep="\n",
                file=sys.stderr,
            )
            return 3

    action = "Would" if dry_run else "Will"
    print(f"{action} create deck workspace at decks/{name}/", file=sys.stderr)

    # 1. workspace
    created = create_workspace(deck_dir, dry_run)
    for path in created:
        print(f"  {action} mkdir  {path}/", file=sys.stderr)

    skeleton_info: dict = {}
    if skeleton_dir is not None:
        # 2. copy skeleton.yaml -> brainstorm/skeleton_used.yaml
        src_yaml = skeleton_dir / "skeleton.yaml"
        dst_yaml = deck_dir / "brainstorm" / "skeleton_used.yaml"
        print(f"  {action} copy   {src_yaml.relative_to(REPO)} -> {dst_yaml.relative_to(REPO)}", file=sys.stderr)
        if not dry_run:
            dst_yaml.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src_yaml, dst_yaml)

        # 3. copy outline.md.tmpl -> author/deck_v1_outline.md.draft
        src_tmpl = skeleton_dir / "outline.md.tmpl"
        dst_tmpl = deck_dir / "author" / "deck_v1_outline.md.draft"
        print(f"  {action} copy   {src_tmpl.relative_to(REPO)} -> {dst_tmpl.relative_to(REPO)}", file=sys.stderr)
        if not dry_run:
            dst_tmpl.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src_tmpl, dst_tmpl)

        skeleton_info = parse_skeleton_yaml(src_yaml)

    msg = emit_next_step_message(name, skeleton, skeleton_info)
    print(msg)

    if dry_run:
        print("(dry-run · 没有真建任何东西)", file=sys.stderr)
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="new_deck.py",
        description="P3-8 · 起新 deck workspace · 可选用 skeleton 预填。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  scripts/new_deck.py 2026-q2-report --skeleton quarterly_finance_report\n"
            "  scripts/new_deck.py 2026-q2-report --skeleton quarterly_finance_report --dry-run\n"
            "  scripts/new_deck.py my-deck\n"
            "  scripts/new_deck.py --list-skeletons\n"
        ),
    )
    parser.add_argument(
        "name",
        nargs="?",
        help="deck slug (建在 decks/<name>/). 跟 --list-skeletons 二选一",
    )
    parser.add_argument(
        "--skeleton",
        "-s",
        help="skeleton 名(在 library/deck-skeletons/ 下). 不传 = 起空白 deck",
    )
    parser.add_argument(
        "--list-skeletons",
        action="store_true",
        help="列出可用 skeletons 然后退出",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="只打印将做什么 · 不真改文件",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="若 decks/<name>/ 已存在,允许覆盖 skeleton 文件(workspace 目录不删)",
    )

    args = parser.parse_args(argv)

    if args.list_skeletons:
        return cmd_list_skeletons()

    if not args.name:
        parser.error("缺 deck name(或加 --list-skeletons 列 skeleton)")

    return cmd_new_deck(args.name, args.skeleton, args.dry_run, args.force)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
