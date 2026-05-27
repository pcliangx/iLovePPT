#!/usr/bin/env python3
"""DASHSCOPE_API_KEY rotation 工具 · P3-18。

CLI:
    rotate_api_key.py --new-key <NEW-KEY>         # 替换 .env 中的 key + 验证
    rotate_api_key.py                              # 同上(从 stdin 读 key)
    rotate_api_key.py --list-backups               # 列已有备份
    rotate_api_key.py --rollback <timestamp>       # 回滚到指定备份
    rotate_api_key.py --validate-only              # 只验证当前 key,不 rotate

行为:
    1. 备份 library/_rag/.env → .env.bak.<ISO timestamp>
    2. 替换 .env 里 DASHSCOPE_API_KEY=<旧> 为新 key(保留其他行不动)
    3. 验证新 key:跑一次 embed_text("test") 测试
    4. 通过 → 报 success;失败 → 自动 rollback(.env.bak 恢复)+ 报 error

不变量:
    - 永不打印完整 key(stdout / stderr / 日志全部只打印前 4 字符 + "..." + 后 4 字符)
    - 备份文件 chmod 0600(防 cat 泄漏)
    - rollback 失败时**不擦除** .env.bak.<ts>(用户可以手动恢复)
"""

from __future__ import annotations

import argparse
import getpass
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
RAG_ROOT = SCRIPT_DIR.parent  # library/_rag/
ENV_FILE = RAG_ROOT / ".env"
KEY_VAR = "DASHSCOPE_API_KEY"


def _mask(key: str) -> str:
    """打印用 masked key。"""
    if not key:
        return "(empty)"
    if len(key) < 12:
        return f"{key[:2]}...{key[-2:]}"
    return f"{key[:4]}...{key[-4:]}"


def _ts() -> str:
    """ISO timestamp(filename-safe)。"""
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _list_backups() -> list[Path]:
    """按时间排序列出所有 .env.bak.<ts> 文件。"""
    backups = sorted(RAG_ROOT.glob(".env.bak.*"))
    return backups


def _read_current_key() -> str | None:
    """从 .env 读当前 key,不存在或没设 → None。"""
    if not ENV_FILE.exists():
        return None
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(f"{KEY_VAR}="):
            return line[len(KEY_VAR) + 1:].strip().strip('"').strip("'")
    return None


def _write_env_with_new_key(new_key: str) -> None:
    """写 .env,替换 DASHSCOPE_API_KEY 行为新值;若行不存在则 append。"""
    if not ENV_FILE.exists():
        # .env 不存在 → 新建,只含 KEY_VAR 行
        ENV_FILE.write_text(f"{KEY_VAR}={new_key}\n", encoding="utf-8")
        os.chmod(ENV_FILE, 0o600)
        return
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
    out_lines = []
    replaced = False
    pattern = re.compile(rf"^\s*{re.escape(KEY_VAR)}\s*=.*$")
    for line in lines:
        if pattern.match(line.rstrip("\n").rstrip("\r")):
            # 保持原行尾换行
            line_end = "\n" if line.endswith("\n") else ""
            out_lines.append(f"{KEY_VAR}={new_key}{line_end}")
            replaced = True
        else:
            out_lines.append(line)
    if not replaced:
        # .env 存在但没 KEY_VAR 行 → append
        if out_lines and not out_lines[-1].endswith("\n"):
            out_lines[-1] += "\n"
        out_lines.append(f"{KEY_VAR}={new_key}\n")
    ENV_FILE.write_text("".join(out_lines), encoding="utf-8")
    os.chmod(ENV_FILE, 0o600)


def _backup_env() -> Path:
    """cp .env → .env.bak.<ts>,return 备份路径。"""
    if not ENV_FILE.exists():
        raise FileNotFoundError(f".env not found: {ENV_FILE}")
    backup_path = RAG_ROOT / f".env.bak.{_ts()}"
    shutil.copy2(ENV_FILE, backup_path)
    os.chmod(backup_path, 0o600)
    return backup_path


def _validate_key(key: str) -> tuple[bool, str]:
    """跑 embed_text("test") 验证新 key。

    Returns:
        (ok, message)
    """
    # 临时把环境变量 set 成新 key(qwen_embedding.load_env 不覆盖已有 env)
    old_env = os.environ.get(KEY_VAR)
    os.environ[KEY_VAR] = key
    try:
        # late import,避免在 --list-backups / --help 等不需要 API 时也走依赖
        sys.path.insert(0, str(RAG_ROOT))
        try:
            from qwen_embedding import embed_text  # noqa: E402
        except ImportError as e:
            return False, f"import qwen_embedding 失败: {e}"
        try:
            vec = embed_text("test", api_key=key, retry=1)
            if not isinstance(vec, list) or len(vec) == 0:
                return False, f"embed_text returned invalid: type={type(vec)}"
            return True, f"embed_text ok · dim={len(vec)}"
        except Exception as e:
            return False, f"embed_text failed: {e}"
    finally:
        # 还原 env
        if old_env is None:
            os.environ.pop(KEY_VAR, None)
        else:
            os.environ[KEY_VAR] = old_env


def cmd_list_backups(args) -> int:
    """列出 .env.bak.<ts> 文件。"""
    backups = _list_backups()
    if not backups:
        print("(no backups)")
        return 0
    print(f"backups in {RAG_ROOT}:")
    for b in backups:
        size = b.stat().st_size
        mtime = datetime.fromtimestamp(b.stat().st_mtime).isoformat()
        print(f"  {b.name}  ({size} bytes, mtime {mtime})")
    return 0


def cmd_rollback(args) -> int:
    """回滚到指定备份。

    args.rollback 可以是:
      - 完整 timestamp(20260527T123456Z)→ .env.bak.20260527T123456Z
      - 完整文件名(.env.bak.<ts>)
      - 'latest'(最新一份)
    """
    backups = _list_backups()
    if not backups:
        print("ERROR: 没有备份,无法回滚", file=sys.stderr)
        return 2
    target_arg = args.rollback
    if target_arg == "latest":
        target = backups[-1]
    else:
        if target_arg.startswith(".env.bak."):
            candidate = RAG_ROOT / target_arg
        else:
            candidate = RAG_ROOT / f".env.bak.{target_arg}"
        if not candidate.exists():
            print(f"ERROR: 备份不存在: {candidate}", file=sys.stderr)
            print(f"可用备份(--list-backups):", file=sys.stderr)
            for b in backups:
                print(f"  {b.name}", file=sys.stderr)
            return 2
        target = candidate
    # 先备份当前 .env(以防 rollback 错了)
    if ENV_FILE.exists():
        pre_rollback = RAG_ROOT / f".env.bak.pre-rollback.{_ts()}"
        shutil.copy2(ENV_FILE, pre_rollback)
        os.chmod(pre_rollback, 0o600)
        print(f"[rollback] saved current .env to {pre_rollback.name}")
    shutil.copy2(target, ENV_FILE)
    os.chmod(ENV_FILE, 0o600)
    print(f"[rollback] restored .env from {target.name}")
    # 验证回滚后的 key
    key = _read_current_key()
    if key:
        print(f"[rollback] current key (masked): {_mask(key)}")
    return 0


def cmd_validate_only(args) -> int:
    """只验证当前 .env 里的 key,不 rotate。"""
    key = _read_current_key()
    if not key:
        print("ERROR: .env 里没有 DASHSCOPE_API_KEY", file=sys.stderr)
        return 2
    print(f"[validate] current key (masked): {_mask(key)}")
    ok, msg = _validate_key(key)
    if ok:
        print(f"[validate] OK · {msg}")
        return 0
    print(f"[validate] FAIL · {msg}", file=sys.stderr)
    return 2


def cmd_rotate(args) -> int:
    """完整 rotation:backup → write new key → validate → rollback on failure。"""
    # 1. 拿到新 key(arg / stdin / prompt)
    if args.new_key:
        new_key = args.new_key.strip()
    elif not sys.stdin.isatty():
        new_key = sys.stdin.read().strip()
    else:
        new_key = getpass.getpass(prompt="新 API key (hidden): ").strip()
    if not new_key:
        print("ERROR: 新 key 为空", file=sys.stderr)
        return 2
    if not new_key.startswith("sk-") and not args.force:
        print(
            f"WARNING: key 不以 'sk-' 开头(got: {_mask(new_key)})。"
            "DashScope key 通常 sk- 开头。"
            "若确定 key 格式正确,加 --force 跳过校验。",
            file=sys.stderr,
        )
        return 2

    # 2. 现有 key + .env 状态
    cur_key = _read_current_key()
    print(f"[rotate] current key (masked): {_mask(cur_key)}")
    print(f"[rotate] new key     (masked): {_mask(new_key)}")
    if cur_key == new_key:
        print("WARNING: 新 key 跟当前一致,不做 rotation", file=sys.stderr)
        return 0

    # 3. 备份当前 .env
    if ENV_FILE.exists():
        backup = _backup_env()
        print(f"[rotate] backed up .env → {backup.name}")
    else:
        backup = None
        print("[rotate] .env not found · 将创建新文件")

    # 4. 写新 key 到 .env
    try:
        _write_env_with_new_key(new_key)
        print(f"[rotate] wrote new key to .env")
    except Exception as e:
        print(f"ERROR: 写 .env 失败: {e}", file=sys.stderr)
        return 2

    # 5. 验证新 key
    print("[rotate] validating new key (embed_text('test')) ...")
    ok, msg = _validate_key(new_key)
    if ok:
        print(f"[rotate] SUCCESS · {msg}")
        print(f"[rotate] 旧 key 备份保留在 {backup.name if backup else '(no backup, was fresh install)'};"
              " 季度 rotation 后可清理")
        return 0

    # 6. 验证失败 → 自动 rollback
    print(f"[rotate] validation FAILED · {msg}", file=sys.stderr)
    if backup and backup.exists():
        try:
            shutil.copy2(backup, ENV_FILE)
            os.chmod(ENV_FILE, 0o600)
            print(f"[rotate] AUTO-ROLLBACK · restored .env from {backup.name}", file=sys.stderr)
        except Exception as e:
            print(
                f"ERROR: AUTO-ROLLBACK 也失败:{e}\n"
                f"  手动恢复:cp {backup} {ENV_FILE}",
                file=sys.stderr,
            )
            return 3  # 严重错误
    else:
        print(
            "ERROR: 无备份可回滚(.env 之前不存在 / 备份消失)。\n"
            f"  当前 .env 已写入新 key(但新 key 不工作)。\n"
            f"  手动恢复:echo 'DASHSCOPE_API_KEY=<旧 key>' > {ENV_FILE}",
            file=sys.stderr,
        )
        return 3
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="DASHSCOPE_API_KEY rotation 工具(P3-18)",
        epilog="文档:docs/security/api-key-rotation.md",
    )
    parser.add_argument("--new-key", help="新 API key(也支持 stdin pipe / 交互输入)")
    parser.add_argument("--force", action="store_true", help="跳过 'sk-' 前缀校验")
    parser.add_argument("--list-backups", action="store_true", help="列出已有备份")
    parser.add_argument("--rollback", metavar="TS", help="回滚到指定 timestamp / 文件名 / 'latest'")
    parser.add_argument("--validate-only", action="store_true", help="只验证当前 key,不 rotate")
    args = parser.parse_args()

    # 互斥子命令分发
    if args.list_backups:
        return cmd_list_backups(args)
    if args.rollback:
        return cmd_rollback(args)
    if args.validate_only:
        return cmd_validate_only(args)
    return cmd_rotate(args)


if __name__ == "__main__":
    sys.exit(main())
