"""Unit tests for ML text preprocessing."""

from triage.ml.preprocess import (
    preprocess_text,
    remove_html_comments,
    replace_code_blocks,
    replace_stack_traces,
    replace_urls,
    truncate_body,
)


def test_remove_html_comments():
    text = "Bug report <!-- please fill this out --> with details <!-- another comment -->."
    cleaned = remove_html_comments(text)
    assert "<!--" not in cleaned
    assert "please fill this out" not in cleaned
    assert "Bug report with details ." in " ".join(cleaned.split())


def test_replace_code_blocks():
    text = "Here is my code:\n```python\ndef foo():\n    return 42\n```\nIt fails."
    cleaned = replace_code_blocks(text)
    assert "<CODE>" in cleaned
    assert "def foo():" not in cleaned
    assert "It fails." in cleaned


def test_replace_urls():
    text = "Check documentation at https://example.com/docs/guide and http://test.org."
    cleaned = replace_urls(text)
    assert "<URL>" in cleaned
    assert "https://example.com" not in cleaned
    assert "http://test.org" not in cleaned


def test_replace_stack_traces():
    text = (
        "Got an error:\n"
        "Traceback (most recent call last):\n"
        '  File "test.py", line 12, in run\n'
        "ValueError: invalid literal\n"
        "Please fix."
    )
    cleaned = replace_stack_traces(text)
    assert "<TRACE>" in cleaned
    assert "ValueError: invalid literal" not in cleaned
    assert "Please fix." in cleaned


def test_truncate_body():
    short_body = "Short content"
    assert truncate_body(short_body, max_chars=100) == short_body

    long_body = "A" * 50 + "B" * 50
    truncated = truncate_body(long_body, max_chars=40)
    assert len(truncated) < len(long_body)
    assert truncated.startswith("A" * 20)
    assert truncated.endswith("B" * 20)
    assert "..." in truncated


def test_preprocess_text_integration():
    title = "Crash when clicking button"
    body = (
        "<!-- template note -->\n"
        "Repro at https://repro.io:\n"
        "```js\nconsole.log(err);\n```\n"
        "Traceback (most recent call last):\n"
        '  File "app.py", line 1, in <module>\n'
        "RuntimeError: failed\n"
        "End of report."
    )
    result = preprocess_text(title, body, max_chars=1000)

    assert "Crash when clicking button" in result
    assert "template note" not in result
    assert "<URL>" in result
    assert "<CODE>" in result
    assert "<TRACE>" in result
    assert "End of report." in result
