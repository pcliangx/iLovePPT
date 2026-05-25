"""tests/library/ · 各测试文件在顶部用 try-import 自行 module-level skip。

不同测试需要不同 venv:
- test_load_theme_path 需要 python-pptx
- 其他 lib 测试需要 sqlite-vec + pyyaml

跑全部 lib 测试:
    library/_rag/.venv/bin/python -m pytest tests/library/ -v
    python3 -m pytest tests/library/test_load_theme_path.py -v
"""
