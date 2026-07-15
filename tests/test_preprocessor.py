"""Tests for line-preserving comment preprocessing."""

from serpentguard.preprocessor import preprocess


def test_comments_are_masked_without_changing_line_mapping() -> None:
    raw = "surf one cyl 0 0 1 % note\r\n/* two\rcomment lines */\rcell a 0 void -one\n"

    source = preprocess(raw, file_name="comments.inp")

    assert "note" not in source.text
    assert "comment lines" not in source.text
    assert source.text.count("\n") == source.original_text.count("\n") == 4
    assert len(source.text) == len(source.original_text)
    assert "cell a 0 void -one" in source.text.splitlines()[3]
    assert source.diagnostics == ()


def test_unterminated_block_comment_reports_opening_line() -> None:
    source = preprocess(
        "surf one cyl 0 0 1\n/* unfinished\nstill hidden",
        file_name="broken.inp",
    )

    diagnostic = source.diagnostics[0]
    assert diagnostic.code == "SG011"
    assert diagnostic.severity == "ERROR"
    assert diagnostic.location.file_name == "broken.inp"
    assert diagnostic.location.line_start == 2
    assert "unfinished" not in diagnostic.message
