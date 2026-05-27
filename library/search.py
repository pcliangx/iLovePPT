#!/usr/bin/env python3
"""跨 kb 检索 router · 唯一入口。

用法:
    library/search.sh --query "..."                                          # 全 kb 搜
    library/search.sh --query "..." --kb visual-patterns                     # 限 vp
    library/search.sh --query "..." --kb pptx-templates --type page          # 限 tpl 页
    library/search.sh --query "..." --preferred-template template_golden     # 优先该模板 · fallback vp

行为:
    若有 --preferred-template:
        1. 在 tpl_pages 查, parent=tpl:<name>
        2. 命中 ≥ top-k 且平均分 ≥ threshold → 直接返回
        3. 否则:fallback 到 visual-patterns + 合并 top-k
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "_rag"))
from qwen_embedding import embed_image, embed_text, get_api_key, open_db  # noqa: E402

DEFAULT_FALLBACK_THRESHOLD = 0.55
DEFAULT_TOP_K = 5
QUERY_LOG_PATH = SCRIPT_DIR / "_rag" / "query_log.jsonl"
INVERSE_CATEGORY_PENALTY = 0.85

# 静态查询扩展表 · 短 query 经常召回不准,撞到关键词触发同领域补词
# 触发词必须是 query 的子串。每次最多补 8 个补词
EXPANSION_HINTS: dict[str, list[str]] = {
    "财务汇报": ["财报", "财务报告", "净利润", "营收", "预算", "CFO", "年度财务"],
    "财务":     ["财报", "营收", "利润", "净利润", "现金流", "ROI", "CFO"],
    "财报":     ["财务报告", "财务数据", "会计", "预算", "CFO"],
    "团队培训": ["团建", "OKR kickoff", "入职", "on-boarding", "讲师", "workshop"],
    "团建":     ["团队建设", "团队培训", "OKR", "入职", "团队精神"],
    "培训":     ["团队培训", "入职", "on-boarding", "课件", "讲师", "workshop"],
    "极光":     ["渐变", "创意", "黑底", "高级感", "aurora", "gradient", "creative"],
    "工作汇报": ["述职", "项目复盘", "季度汇报", "OKR review", "工作总结"],
    "汇报":     ["工作汇报", "述职", "项目复盘", "总结", "PPT"],
    "年报":     ["年度报告", "annual report", "路演", "投资人", "IPO"],
    "年度报告": ["年报", "annual report", "路演", "投资人", "IPO"],
    "路演":     ["投资人", "IPO", "招股", "投融资", "executive briefing"],
    "产品":     ["产品介绍", "feature", "白皮书", "whitepaper", "技术架构", "SaaS"],
    "SaaS":     ["产品", "feature deck", "互联网", "技术", "工具产品"],
    "条纹":     ["几何", "工业", "现代", "硬朗", "斜切", "diagonal"],
    "SWOT":     ["quadrant", "战略分析", "四象限", "工作汇报"],
}


def expand_query(q: str, enabled: bool = True) -> str:
    """触发词 in q → 补同领域词,最多 8 个。"""
    if not enabled or not q:
        return q
    additions: list[str] = []
    for trigger, extras in EXPANSION_HINTS.items():
        if trigger in q:
            additions.extend(extras)
    if not additions:
        return q
    seen = set(q.lower().split())
    seen.update(c for c in q if "一" <= c <= "鿿")
    deduped: list[str] = []
    for x in additions:
        key = x.lower()
        if key in seen or any(key in s for s in seen):
            continue
        seen.add(key)
        deduped.append(x)
        if len(deduped) >= 8:
            break
    return q + " " + " ".join(deduped) if deduped else q


# Category 触发词表 · query 含明确 category 信号时,非该 category 的 hit 软降权(× 0.85)
# 跟 EXPANSION_HINTS 互补:EXPANSION 解决"召回不准",CATEGORY 解决"召回到但排序不对"
CATEGORY_HINTS: dict[str, str] = {
    "财务汇报":   "finance",
    "财务":       "finance",
    "财报":       "finance",
    "财务数据":   "finance",
    "财务分析":   "finance",
    "净利润":     "finance",
    "团建":       "training",
    "团队培训":   "training",
    "培训":       "training",
    "员工培训":   "training",
    "OKR kickoff": "training",
    "极光":       "creative-modern",
    "创意":       "creative-modern",
    "黑底高级感": "creative-modern",
    "渐变":       "creative-modern",
    "高端":       "creative-modern",
    "工作汇报":   "enterprise-modern",
    "述职":       "enterprise-modern",
    "项目复盘":   "enterprise-modern",
    "年报":       "enterprise-modern",
    "年度报告":   "enterprise-modern",
    "路演":       "enterprise-modern",
    "SWOT":       "enterprise-modern",
    "战略分析":   "enterprise-modern",
    "产品介绍":   "enterprise-modern",
    "技术架构":   "enterprise-modern",
    "SaaS":       "enterprise-modern",
    "斜切条纹":   "enterprise-modern",
    "几何工业":   "enterprise-modern",
}


def infer_category(query: str) -> str | None:
    """扫触发词,返回首个 match 的 category(按 dict 插入序)。无 match → None。"""
    if not query:
        return None
    for trigger, cat in CATEGORY_HINTS.items():
        if trigger in query:
            return cat
    return None


def _blob(v: list[float]) -> bytes:
    return struct.pack(f"{len(v)}f", *v)


def _query_table(db, kb_table: str, emb_table: str, q_blob: bytes, where: str, params: tuple, k: int):
    """通用表查询. kb_table ∈ {vp_items, tpl_templates, tpl_pages}, emb_table ∈ {text_emb, image_emb}."""
    sql = f"""SELECT k.id, k.text_doc, k.meta_path, k.preview_path,
                 {'k.category' if kb_table != 'tpl_pages' else 'k.layout_type'} AS cat,
                 {'NULL' if kb_table != 'tpl_pages' else 'k.template_id'} AS parent_id,
                 vec_distance_cosine(e.embedding, ?) AS distance
              FROM {kb_table} k JOIN {emb_table} e ON k.id = e.id
              {where}
              ORDER BY distance ASC
              LIMIT ?"""
    return db.execute(sql, (q_blob,) + params + (k,)).fetchall()


def _query_table_hybrid(
    db, kb_table: str, q_blob: bytes, where: str, params: tuple, k: int,
    text_weight: float, image_weight: float,
):
    """Hybrid · 同 q_blob 跑 text_emb 和 image_emb,按 id 合并 score 重排。

    multimodal embedding (tongyi-embedding-vision-plus dim=1152) 把 text 和 image 编到同一空间,
    所以同一个 query 向量可以查两表。final_score = text_w * (1-text_dist) + image_w * (1-image_dist)。
    """
    cat_col = "k.layout_type" if kb_table == "tpl_pages" else "k.category"
    parent_col = "k.template_id" if kb_table == "tpl_pages" else "NULL"

    def _fetch(emb_table: str):
        sql = f"""SELECT k.id, k.text_doc, k.meta_path, k.preview_path,
                     {cat_col} AS cat, {parent_col} AS parent_id,
                     vec_distance_cosine(e.embedding, ?) AS distance
                  FROM {kb_table} k JOIN {emb_table} e ON k.id = e.id
                  {where}
                  ORDER BY distance ASC
                  LIMIT ?"""
        # 各取 k*3 候选,合并去重
        rows = db.execute(sql, (q_blob,) + params + (k * 3,)).fetchall()
        return {r[0]: r for r in rows}

    text_rows = _fetch("text_emb")
    image_rows = _fetch("image_emb")
    merged: list[tuple] = []
    for rid in text_rows.keys() | image_rows.keys():
        t = text_rows.get(rid)
        i = image_rows.get(rid)
        base = t or i
        text_score = (1.0 - t[6]) if t else 0.0
        image_score = (1.0 - i[6]) if i else 0.0
        combined = text_weight * text_score + image_weight * image_score
        new_row = list(base)
        new_row[6] = 1.0 - combined  # 转回"距离"让外层 sort ASC 仍正确
        merged.append(tuple(new_row))
    merged.sort(key=lambda r: r[6])
    return merged[:k]


def _row_dict(r: tuple, row_type: str) -> dict:
    return {
        "id": r[0],
        "row_type": row_type,
        "category_or_layout": r[4] or "",
        "parent_id": r[5],
        "score": round(1 - r[6], 4),
        "distance": round(r[6], 4),
        "preview_path": r[3] or "",
        "meta_path": r[2] or "",
        "doc_preview": (r[1] or "")[:120] + ("..." if r[1] and len(r[1]) > 120 else ""),
    }


def _apply_inverse_category(results: list[dict], inferred_cat: str | None, mode: str) -> None:
    """对 hits 做 in-place 软降权:非 inferred_cat 的 score × 0.85,distance 反算。

    仅 text / hybrid mode 生效(image mode 走视觉相似,category 信号无意义)。
    只比对 tpl_template 这类带 category 字段的 row;tpl_page 用 layout_type 不参与。
    """
    if not inferred_cat or mode == "image":
        return
    for h in results:
        # tpl_page 的 category_or_layout 是 layout_type(不是 category),跳过
        if h.get("row_type") == "tpl_page":
            continue
        hit_cat = h.get("category_or_layout") or ""
        if not hit_cat or hit_cat == inferred_cat:
            continue
        new_score = h["score"] * INVERSE_CATEGORY_PENALTY
        h["score"] = round(new_score, 4)
        h["distance"] = round(1.0 - new_score, 4)
        h["inverse_category_applied"] = True


def search(
    query: str | None,
    query_image: str | None,
    kb: str,
    type_: str,
    category: str | None,
    preferred_template: str | None,
    top_k: int,
    fallback_threshold: float,
    mode: str,
    text_weight: float = 0.6,
    image_weight: float = 0.4,
    inverse_category: bool = True,
) -> list[dict]:
    api_key = get_api_key()
    db = open_db()

    if query_image:
        q_vec = embed_image(query_image, api_key=api_key)
    elif query:
        q_vec = embed_text(query, api_key=api_key)
    else:
        raise ValueError("必须 --query 或 --query-image")
    q_blob = _blob(q_vec)

    emb_table = "image_emb" if mode == "image" else "text_emb"

    def _run(kb_table: str, where: str, params: tuple, k: int):
        if mode == "hybrid":
            return _query_table_hybrid(db, kb_table, q_blob, where, params, k, text_weight, image_weight)
        return _query_table(db, kb_table, emb_table, q_blob, where, params, k)

    pref_id = f"tpl:{preferred_template}" if preferred_template else None

    inferred_cat = infer_category(query) if (inverse_category and query) else None

    def _do_query(target_kb: str, target_type: str, filter_parent: str | None, k: int):
        out: list[dict] = []
        if target_kb in ("all", "visual-patterns") and target_type in ("any", "item"):
            where = "WHERE 1=1"
            params: tuple = ()
            if category:
                where += " AND k.category = ?"
                params = params + (category,)
            for r in _run("vp_items", where, params, k):
                out.append(_row_dict(r, "vp_item"))
        if target_kb in ("all", "pptx-templates") and target_type in ("any", "template"):
            where = "WHERE 1=1"
            params = ()
            if category:
                where += " AND k.category = ?"
                params = params + (category,)
            for r in _run("tpl_templates", where, params, k):
                out.append(_row_dict(r, "tpl_template"))
        if target_kb in ("all", "pptx-templates") and target_type in ("any", "page"):
            where = "WHERE 1=1"
            params = ()
            if filter_parent:
                where += " AND k.template_id = ?"
                params = params + (filter_parent,)
            if category:
                where += " AND k.layout_type = ?"
                params = params + (category,)
            for r in _run("tpl_pages", where, params, k):
                out.append(_row_dict(r, "tpl_page"))
        return out

    if pref_id:
        primary = _do_query("pptx-templates", "page", pref_id, top_k)
        _apply_inverse_category(primary, inferred_cat, mode)
        primary.sort(key=lambda x: x["distance"])
        for r in primary:
            r["source"] = "preferred-template"
        avg_score = (sum(r["score"] for r in primary) / len(primary)) if primary else 0.0
        if len(primary) >= top_k and avg_score >= fallback_threshold:
            db.close()
            return primary[:top_k]
        fallback = _do_query("visual-patterns", "item", None, top_k)
        _apply_inverse_category(fallback, inferred_cat, mode)
        for r in fallback:
            r["source"] = "visual-patterns"
        combined = primary + fallback
        combined.sort(key=lambda x: x["distance"])
        seen = set()
        deduped: list[dict] = []
        for r in combined:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            deduped.append(r)
        db.close()
        return deduped[:top_k]
    else:
        out = _do_query(kb, type_, None, top_k * 3)
        _apply_inverse_category(out, inferred_cat, mode)
        out.sort(key=lambda x: x["distance"])
        for r in out:
            r["source"] = "preferred-template" if r["row_type"].startswith("tpl_") else "visual-patterns"
        db.close()
        return out[:top_k]


def _log_query(args, expanded_query: str | None, results: list[dict]) -> None:
    """append 一行 JSONL 到 query_log.jsonl。失败 silent,只打 stderr warn。"""
    try:
        hits_brief = [
            {
                "rank": i + 1,
                "id": h.get("id"),
                "row_type": h.get("row_type"),
                "category_or_layout": h.get("category_or_layout") or "",
                "score": h.get("score"),
            }
            for i, h in enumerate(results)
        ]
        record = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "query": args.query,  # 注意:此时 args.query 已被 expand_query 覆写过(若启用)
            "query_image": args.query_image,
            "expanded_query": expanded_query,
            "mode": args.mode,
            "kb": args.kb,
            "type": args.type_,
            "preferred_template": args.preferred_template,
            "top_k": args.top_k,
            "results_count": len(results),
            "hits": hits_brief,
        }
        QUERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(QUERY_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[search.py] WARN: query_log 写失败 — {type(e).__name__}: {e}", file=sys.stderr)


USAGE_EPILOG = """\
三种模式 · 按场景挑:

  A. 语义查模板(默认 · text)
     library/search.sh --kb pptx-templates --type template --query "<brief 主题>"
     例:--query "财务汇报"  →  finance_arrow #1

  B. 视觉风格查模板(hybrid · text+image 融合)
     library/search.sh --kb pptx-templates --type template --query "<视觉描述>" --mode hybrid
     例:--query "极光渐变 黑底高级感" --mode hybrid  →  creative_aurora #1
     适用:用户描述"风格 / 配色 / 元素"为主,语义关键词少时

  C. 图查相似页(image · 用 PNG 反查)
     library/search.sh --kb pptx-templates --type page --query-image <PNG-path> --mode image
     例:--query-image mockup.png --type page  →  视觉最像的 5 张 page
     适用:用户给 inspiration 图 / builder 检查生成 PNG 跟模板偏差

  D. 限定模板内选页(--preferred-template)
     library/search.sh --query "<本页意图>" --preferred-template <name> --type page
     例:--query "5 阶段串行" --preferred-template enterprise_skyline --type page
     适用:author 拓写时给当前 brief.theme 选具体页

Query 静态扩展:短 query 自动撞库补词(财务 → +财报+营收+CFO 等),--no-expand 关。
权重调:--text-weight 0.6 --image-weight 0.4(默认),hybrid 模式生效。
"""


def main():
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="跨 kb 检索 router · pptx-templates / visual-patterns 唯一入口",
        epilog=USAGE_EPILOG,
    )
    p.add_argument("--query")
    p.add_argument("--query-image")
    p.add_argument("--mode", default="text", choices=["text", "image", "hybrid"],
                   help="text(默认 · 语义查询最稳)/ image(纯图)/ hybrid(text+image 融合 · 视觉风格查询用)")
    p.add_argument("--text-weight", type=float, default=0.6, help="hybrid 模式 text 权重(默认 0.6)")
    p.add_argument("--image-weight", type=float, default=0.4, help="hybrid 模式 image 权重(默认 0.4)")
    p.add_argument("--no-expand", action="store_true", help="关闭 query 静态扩展(默认开)")
    p.add_argument("--no-inverse-category", action="store_true",
                   help="关闭 inverse-category 软降权(默认开 · 仅 text/hybrid mode 生效)")
    p.add_argument("--no-log", action="store_true", help="关闭 query 日志写入(便于 batch 测试不污染)")
    p.add_argument("--kb", default="all", choices=["visual-patterns", "pptx-templates", "all"])
    p.add_argument("--type", dest="type_", default="any", choices=["item", "template", "page", "any"])
    p.add_argument("--category", default=None)
    p.add_argument("--preferred-template", default=None)
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p.add_argument("--fallback-threshold", type=float, default=DEFAULT_FALLBACK_THRESHOLD)
    p.add_argument("--format", default="json", choices=["json", "text"])
    args = p.parse_args()

    if not args.query and not args.query_image:
        p.error("必须提供 --query 或 --query-image")

    original_query = args.query
    if args.query:
        args.query = expand_query(args.query, enabled=not args.no_expand)

    results = search(
        query=args.query,
        query_image=args.query_image,
        kb=args.kb,
        type_=args.type_,
        category=args.category,
        preferred_template=args.preferred_template,
        top_k=args.top_k,
        fallback_threshold=args.fallback_threshold,
        mode=args.mode,
        text_weight=args.text_weight,
        image_weight=args.image_weight,
        inverse_category=not args.no_inverse_category,
    )

    if not args.no_log:
        # log 原 query + 扩展后 query 分开记
        log_args = argparse.Namespace(**vars(args))
        log_args.query = original_query
        _log_query(log_args, expanded_query=args.query, results=results)

    if args.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            src = r.get("source", "?")
            print(f"{r['score']:.3f}  [{src:>20}] [{r['row_type']:<12}] {r['id']:<50}")
            print(f"          {r['doc_preview']}")


if __name__ == "__main__":
    main()
