from pathlib import Path

import pandas as pd
import pytest

from grades_analyzer.analysis import (
    Settings,
    at_risk_students,
    letter_grade,
    student_summary,
    subject_summary,
)
from grades_analyzer.cli import main
from grades_analyzer.loader import GradebookError, load_gradebook

SETTINGS = Settings(pass_mark=50, risk_average=60, max_failed_subjects=1)


def write_csv(tmp_path: Path, text: str, name: str = "grades.csv") -> Path:
    path = tmp_path / name
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


@pytest.fixture
def gradebook(tmp_path):
    path = write_csv(
        tmp_path,
        """
Student ID,Name,Python,Math,English
S1,Lina,95,90,85
S2,Omar,40,45,70
S3,Sara,80,,90
S4,Zaid,55,48,62
""",
    )
    return load_gradebook(path)


# ---------- loader ----------

def test_loader_normalises_headers_and_keeps_subject_labels(gradebook):
    assert list(gradebook.data.columns[:2]) == ["student_id", "name"]
    assert gradebook.subjects == ["Python", "Math", "English"]


def test_loader_reports_missing_scores(gradebook):
    assert gradebook.warnings == ["1 missing score(s) in 'Math'"]


def test_loader_reads_excel(tmp_path, gradebook):
    path = tmp_path / "grades.xlsx"
    gradebook.data.to_excel(path, index=False)
    assert load_gradebook(path).subjects == gradebook.subjects


@pytest.mark.parametrize(
    "csv, message",
    [
        ("name,Python\nLina,90", "Missing required column"),
        ("student_id,name\nS1,Lina", "No subject columns"),
        ("student_id,name,Python\nS1,Lina,abc", "Non-numeric"),
        ("student_id,name,Python\nS1,Lina,120", "outside 0-100"),
        ("student_id,name,Python\nS1,Lina,90\nS1,Omar,80", "Duplicate student_id"),
    ],
)
def test_loader_rejects_bad_files(tmp_path, csv, message):
    with pytest.raises(GradebookError, match=message):
        load_gradebook(write_csv(tmp_path, csv))


def test_loader_rejects_unknown_file_type(tmp_path):
    path = tmp_path / "grades.txt"
    path.write_text("x")
    with pytest.raises(GradebookError, match="Unsupported file type"):
        load_gradebook(path)


# ---------- analysis ----------

@pytest.mark.parametrize(
    "score, expected",
    [(95, "A"), (90, "A"), (89.9, "B"), (80, "B"), (70, "C"), (50, "D"), (49.9, "F"), (float("nan"), "-")],
)
def test_letter_grade_boundaries(score, expected):
    assert letter_grade(score, pass_mark=50) == expected


def test_student_summary(gradebook):
    students = student_summary(gradebook.data, gradebook.subjects, SETTINGS).set_index("student_id")

    assert students.loc["S1", "average"] == 90.0
    assert students.loc["S1", "rank"] == 1
    assert students.loc["S1", "best_subject"] == "Python"

    # Sara has a missing Math score: average uses the two scores she has
    assert students.loc["S3", "average"] == 85.0
    assert students.loc["S3", "missing_scores"] == 1

    assert students.loc["S2", "failed_subjects"] == 2
    assert students.loc["S2", "weakest_subject"] == "Python"
    assert students.loc["S2", "letter"] == "D"


def test_subject_summary(gradebook):
    subjects = subject_summary(gradebook.data, gradebook.subjects, SETTINGS).set_index("subject")
    assert subjects.loc["Python", "mean"] == 67.5
    assert subjects.loc["Python", "pass_rate_%"] == 75.0
    assert subjects.loc["Math", "students"] == 3
    # sorted hardest first
    assert subjects.index[0] == "Math"


def test_at_risk_reasons(gradebook):
    students = student_summary(gradebook.data, gradebook.subjects, SETTINGS)
    risk = at_risk_students(students, gradebook.data, gradebook.subjects, SETTINGS).set_index("student_id")

    assert set(risk.index) == {"S2", "S3", "S4"}
    assert "below 60" in risk.loc["S2", "reasons"]
    assert "failed 2 subjects (Python, Math)" in risk.loc["S2", "reasons"]
    assert risk.loc["S3", "reasons"] == "1 missing score(s)"
    assert "below 60" in risk.loc["S4", "reasons"]  # 55 average, only one failed subject


def test_risk_settings_change_the_list(gradebook):
    strict = Settings(pass_mark=50, risk_average=86, max_failed_subjects=0)
    students = student_summary(gradebook.data, gradebook.subjects, strict)
    risk = at_risk_students(students, gradebook.data, gradebook.subjects, strict)
    assert set(risk["student_id"]) == {"S2", "S3", "S4"}

    relaxed = Settings(pass_mark=40, risk_average=40, max_failed_subjects=5)
    students = student_summary(gradebook.data, gradebook.subjects, relaxed)
    risk = at_risk_students(students, gradebook.data, gradebook.subjects, relaxed)
    assert set(risk["student_id"]) == {"S3"}  # only the missing score is left


# ---------- command line ----------

def test_cli_end_to_end(tmp_path, capsys):
    src = write_csv(tmp_path, "student_id,name,Python,Math\nS1,Lina,90,80\nS2,Omar,30,40")
    out = tmp_path / "out"

    assert main([str(src), "-o", str(out)]) == 0

    printed = capsys.readouterr().out
    assert "Needs follow-up: 1 student(s)" in printed
    assert (out / "grades_report.xlsx").exists()
    assert len(list((out / "charts").glob("*.png"))) == 3
    assert len(list((out / "report_cards").glob("*.md"))) == 2

    sheets = pd.read_excel(out / "grades_report.xlsx", sheet_name=None)
    assert set(sheets) == {"Students", "Subjects", "Follow-up", "Scores"}
    assert sheets["Follow-up"]["name"].tolist() == ["Omar"]


def test_cli_skip_flags(tmp_path):
    src = write_csv(tmp_path, "student_id,name,Python\nS1,Lina,90")
    out = tmp_path / "out"
    assert main([str(src), "-o", str(out), "--no-charts", "--no-cards"]) == 0
    assert not (out / "charts").exists()
    assert not (out / "report_cards").exists()


def test_cli_bad_file_returns_error(tmp_path, capsys):
    assert main([str(tmp_path / "missing.csv")]) == 1
    assert "File not found" in capsys.readouterr().err
