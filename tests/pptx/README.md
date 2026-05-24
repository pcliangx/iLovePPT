# tests/pptx/

⚠️ **不要在此目录添加 `__init__.py`** —— 会 shadow `python-pptx` 包,导致测试中 `from pptx import Presentation` 失败。

`${CLAUDE_PROJECT_DIR}/tests/pptx_deck/` 有 `__init__.py` 是安全的（`pptx_deck` 不与任何已安装包冲突）。

pytest 通过 rootdir 探测发现本目录的测试。
