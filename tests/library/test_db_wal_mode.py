"""P3-6 · 验证 open_db 启用 WAL + busy_timeout + synchronous=NORMAL。

跑:
    library/_rag/.venv/bin/python -m pytest tests/library/test_db_wal_mode.py -v
"""

import importlib.util
import sqlite3
import sys
import threading
import time
from pathlib import Path

import pytest

if importlib.util.find_spec("sqlite_vec") is None:
    pytest.skip("sqlite-vec 未装。用 library/_rag/.venv/bin/python 跑", allow_module_level=True)

RAG_DIR = Path(__file__).resolve().parent.parent.parent / "library" / "_rag"
sys.path.insert(0, str(RAG_DIR))


@pytest.fixture
def db_path(tmp_path):
    """临时 DB 文件,不污染真实 db.sqlite。"""
    return tmp_path / "test_wal.sqlite"


@pytest.fixture
def db(db_path, monkeypatch):
    """已开 WAL + busy_timeout 的临时 connection。"""
    import qwen_embedding as q
    monkeypatch.setattr(q, "DB_PATH", db_path)
    conn = q.open_db()
    yield conn
    conn.close()


def test_journal_mode_is_wal(db):
    """PRAGMA journal_mode 应返回 'wal'(写不阻塞读 · 多 reader / 单 writer 并发)。"""
    mode = db.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal", f"expected wal, got {mode!r}"


def test_busy_timeout_is_10000(db):
    """PRAGMA busy_timeout 应返回 10000 ms(锁竞争时等 10s 而非立即报错)。"""
    timeout = db.execute("PRAGMA busy_timeout").fetchone()[0]
    assert timeout == 10000, f"expected 10000, got {timeout!r}"


def test_synchronous_is_normal(db):
    """PRAGMA synchronous 应返回 1 (=NORMAL,WAL 模式下性能跟 FULL 差不多但快)。"""
    # PRAGMA synchronous 返回数值:0=OFF, 1=NORMAL, 2=FULL, 3=EXTRA
    sync = db.execute("PRAGMA synchronous").fetchone()[0]
    assert sync == 1, f"expected 1 (NORMAL), got {sync!r}"


def test_wal_files_created_on_write(db, db_path):
    """WAL 模式启用后,写操作应触发 db.sqlite-wal / db.sqlite-shm 生成。"""
    # 触发一次写以生成 WAL 文件
    db.execute(
        "INSERT INTO vp_items (id, text_doc, category, updated_at) VALUES (?, ?, ?, ?)",
        ("test_vp_1", "hello", "test", "2026-05-27"),
    )
    db.commit()

    wal_file = db_path.parent / (db_path.name + "-wal")
    shm_file = db_path.parent / (db_path.name + "-shm")
    assert wal_file.exists(), f"WAL file not created at {wal_file}"
    assert shm_file.exists(), f"SHM file not created at {shm_file}"


def test_concurrent_writes_dont_lock(db_path, monkeypatch):
    """模拟 parallel_embed.sh 两进程同时写元数据 · WAL + busy_timeout 应兜住,不报 'database is locked'。

    text_emb / image_emb 实际不冲突,但 tpl_templates / tpl_pages 元数据写可能撞 — 这里测的就是这个场景。
    """
    import qwen_embedding as q
    monkeypatch.setattr(q, "DB_PATH", db_path)

    # 先 open 一次跑 schema
    q.open_db().close()

    errors: list[str] = []
    results: list[str] = []

    def writer(name: str, n: int):
        try:
            # 每个 writer 开自己的 connection · 模拟独立进程
            conn = q.open_db()
            for i in range(n):
                conn.execute(
                    "INSERT INTO tpl_templates (id, name, category, updated_at) VALUES (?, ?, ?, ?)",
                    (f"{name}_{i}", f"name_{i}", "test", "2026-05-27"),
                )
                conn.commit()
            conn.close()
            results.append(name)
        except sqlite3.OperationalError as e:
            errors.append(f"{name}: {e}")

    t1 = threading.Thread(target=writer, args=("text_proc", 20))
    t2 = threading.Thread(target=writer, args=("image_proc", 20))
    start = time.time()
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)
    elapsed = time.time() - start

    assert not errors, f"concurrent writes raised OperationalError (WAL 没生效?): {errors}"
    assert len(results) == 2, f"writers didn't finish · results={results}, elapsed={elapsed:.2f}s"

    # 验证两 writer 的写入都落库了
    conn = q.open_db()
    n = conn.execute("SELECT COUNT(*) FROM tpl_templates").fetchone()[0]
    conn.close()
    assert n == 40, f"expected 40 rows total, got {n}"


def test_open_db_idempotent_wal(db_path, monkeypatch):
    """重复 open_db 不应该报错;journal_mode 一旦切到 WAL 会持久(写入 sqlite header)。"""
    import qwen_embedding as q
    monkeypatch.setattr(q, "DB_PATH", db_path)

    c1 = q.open_db()
    mode1 = c1.execute("PRAGMA journal_mode").fetchone()[0]
    c1.close()

    c2 = q.open_db()
    mode2 = c2.execute("PRAGMA journal_mode").fetchone()[0]
    c2.close()

    assert mode1.lower() == "wal"
    assert mode2.lower() == "wal"
