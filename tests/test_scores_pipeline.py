import pytest

from src.scores_pipeline import StudentScore, average_score, create_bar_chart, parse_scores


def test_parse_and_average_scores() -> None:
    students = parse_scores(
        {"students": [{"name": "  Asha  ", "score": 80}, {"name": "Dev", "score": 90.5}]}
    )

    assert students == [StudentScore("Asha", 80.0), StudentScore("Dev", 90.5)]
    assert average_score(students) == 85.25


def test_parse_scores_rejects_out_of_range_value() -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        parse_scores({"students": [{"name": "Asha", "score": 101}]})


def test_create_bar_chart_writes_png(tmp_path) -> None:
    output = create_bar_chart([StudentScore("Asha", 80.0)], tmp_path / "scores.png")

    assert output.exists()
    assert output.read_bytes().startswith(b"\x89PNG")