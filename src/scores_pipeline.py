"""Fetch student scores from an HTTP JSON endpoint and create a bar chart."""

from __future__ import annotations

import argparse
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import requests

DEFAULT_URL = "http://127.0.0.1:8000/student_scores.json"


@dataclass(frozen=True)
class StudentScore:
    name: str
    score: float


def parse_scores(payload: dict[str, Any]) -> list[StudentScore]:
    """Validate an API payload before using it in calculations or a chart."""
    students = payload.get("students")
    if not isinstance(students, list) or not students:
        raise ValueError("Expected a non-empty 'students' list")

    parsed: list[StudentScore] = []
    for item in students:
        if not isinstance(item, dict):
            raise ValueError("Each student must be a JSON object")
        name = item.get("name")
        score = item.get("score")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Each student needs a non-empty name")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError(f"Score for {name!r} must be numeric")
        score = float(score)
        if not math.isfinite(score) or not 0 <= score <= 100:
            raise ValueError(f"Score for {name!r} must be between 0 and 100")
        parsed.append(StudentScore(" ".join(name.split())[:100], score))
    return parsed


def fetch_scores(url: str, timeout: float = 10.0) -> list[StudentScore]:
    """Request one JSON document from the supplied API URL."""
    response = requests.get(
        url,
        headers={"Accept": "application/json"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Expected the API response to be a JSON object")
    return parse_scores(payload)


def average_score(students: list[StudentScore]) -> float:
    """Return the arithmetic mean without rounding away calculation precision."""
    if not students:
        raise ValueError("Cannot calculate an average for an empty list")
    return statistics.fmean(student.score for student in students)


def create_bar_chart(students: list[StudentScore], output_path: str | Path) -> Path:
    """Save a labelled PNG chart, including an average reference line."""
    if not students:
        raise ValueError("Cannot chart an empty list")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    mean = average_score(students)

    figure, axis = plt.subplots(figsize=(9, 5))
    bars = axis.bar(
        [student.name for student in students],
        [student.score for student in students],
        color="#2563eb",
        edgecolor="#1e3a8a",
    )
    axis.axhline(mean, color="#dc2626", linestyle="--", linewidth=1.5, label=f"Average: {mean:.2f}")
    axis.bar_label(bars, labels=[f"{student.score:g}" for student in students], padding=3)
    axis.set(title="Student Test Scores", xlabel="Student", ylabel="Score", ylim=(0, 105))
    axis.grid(axis="y", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="HTTP URL that returns the score JSON")
    parser.add_argument("--output", type=Path, default=Path("outputs/student_scores.png"))
    args = parser.parse_args()

    students = fetch_scores(args.url)
    mean = average_score(students)
    chart = create_bar_chart(students, args.output)
    print(f"Fetched {len(students)} student score(s). Average score: {mean:.2f}")
    print(f"Saved chart to {chart}")


if __name__ == "__main__":
    main()