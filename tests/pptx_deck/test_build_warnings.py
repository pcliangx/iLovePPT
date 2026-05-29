"""组件 A(P0-3)· builder 静默吞错 → fail-loud 可见性测试。"""
import importlib

base = importlib.import_module("builder.base")


def test_warn_appends_and_prints(capsys):
    base.BUILD_WARNINGS.clear()
    base._warn("builder.token-extract", "示例消息")
    captured = capsys.readouterr()
    assert base.BUILD_WARNINGS == ["[builder.token-extract] WARN 示例消息"]
    assert "[builder.token-extract] WARN 示例消息" in captured.err
    assert captured.out == ""  # 必须走 stderr 不污染 stdout


def test_extract_design_tokens_bad_path_warns_not_raises():
    base.BUILD_WARNINGS.clear()
    # 不存在的 .pptx → Presentation() 抛 → 必须被 catch 且回落空 dict + warn
    tokens = base._extract_design_tokens("/nonexistent/does-not-exist.pptx")
    assert tokens == {}
    assert any("token-extract" in w for w in base.BUILD_WARNINGS)


def test_parse_red_line_words_bad_yaml_block_warns(tmp_path):
    base.BUILD_WARNINGS.clear()
    brief = tmp_path / "brief.md"
    # 损坏的 yaml fence 排在第一个,触发 warn + continue
    # 合法 fence 排在第二个,仍能解析出 red_line_words
    # 无 front-matter,确保迭代不会在 front-matter 阶段 early-return
    brief.write_text(
        "```yaml\n"
        "foo: [unclosed\n"
        "```\n\n"
        "```yaml\n"
        "constraints:\n"
        "  red_line_words: [禁词1]\n"
        "```\n",
        encoding="utf-8",
    )
    words = base._parse_red_line_words(str(brief))
    # 合法 fence 仍解析出禁词
    assert "禁词1" in words
    # 损坏 fence 被 warn 而非静默 continue
    assert any("red-line" in w for w in base.BUILD_WARNINGS)
