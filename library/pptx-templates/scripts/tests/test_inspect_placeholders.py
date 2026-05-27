import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).parent.parent / "inspect_placeholders.py"
SAMPLE_PPTX = Path(__file__).parent / "fixtures" / "sample.pptx"


def run(pptx: Path, page_idx: int) -> tuple[int, str, str]:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(pptx), str(page_idx)],
        capture_output=True, text=True,
    )
    return r.returncode, r.stdout, r.stderr


def test_page_0_returns_yaml_with_2_slots():
    code, out, _ = run(SAMPLE_PPTX, 0)
    assert code == 0, out
    data = yaml.safe_load(out)
    assert "slots" in data
    assert len(data["slots"]) == 2  # title + subtitle
    for slot in data["slots"]:
        assert "tree_path" in slot
        assert "raw_text_sample" in slot
        assert "bbox" in slot
        assert "id" in slot  # skeleton has "?"
        assert slot["id"] == "?"


def test_page_1_returns_3_slots():
    code, out, _ = run(SAMPLE_PPTX, 1)
    assert code == 0
    data = yaml.safe_load(out)
    assert len(data["slots"]) == 3
    texts = [s["raw_text_sample"] for s in data["slots"]]
    assert any("卡片 1" in t for t in texts)


def test_page_out_of_range_fails():
    code, _, err = run(SAMPLE_PPTX, 99)
    assert code == 1, err
    assert "PAGE_OUT_OF_RANGE" in err


def test_pptx_not_found_fails():
    code, _, err = run(Path("/tmp/nonexistent.pptx"), 0)
    assert code == 1, err
    assert "PPTX_NOT_FOUND" in err


def test_template_page_index_in_output():
    code, out, _ = run(SAMPLE_PPTX, 0)
    data = yaml.safe_load(out)
    assert data["template_page_index"] == 0


def test_slots_sorted_top_to_bottom():
    code, out, _ = run(SAMPLE_PPTX, 0)
    data = yaml.safe_load(out)
    tops = [s["bbox"]["top"] for s in data["slots"]]
    assert tops == sorted(tops), f"slots not sorted top-to-bottom: {tops}"


def test_shape_id_present_in_each_slot():
    """Every slot must expose a `shape_id` field (int or null)."""
    code, out, _ = run(SAMPLE_PPTX, 0)
    data = yaml.safe_load(out)
    for slot in data["slots"]:
        assert "shape_id" in slot, f"slot missing shape_id: {slot}"
        sid = slot["shape_id"]
        assert sid is None or isinstance(sid, int), f"shape_id must be int|null, got {sid!r}"


def test_shape_ids_unique_within_slide():
    """python-pptx sp.shape_id is unique within a slide. Inspect output should reflect that."""
    code, out, _ = run(SAMPLE_PPTX, 0)
    data = yaml.safe_load(out)
    ids = [s["shape_id"] for s in data["slots"] if s["shape_id"] is not None]
    assert len(ids) == len(set(ids)), f"shape_ids should be unique within a slide: {ids}"
