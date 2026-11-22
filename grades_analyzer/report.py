"""Excel report and one Markdown report card per student."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .analysis import Settings, letter_grade
from .loader import ID_COLUMN, NAME_COLUMN

HEADER_FILL = PatternFill("solid", fgColor="7B3B6E")
RISK_FILL = PatternFill("solid", fgColor="F8DDE6")


def _format_sheet(ws, highlight_rows: set[int] | None = None) -> None:
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
    ws.freeze_panes = "A2"
    for col_idx, column in enumerate(ws.columns, start=1):
        width = max(len(str(c.value)) if c.value is not None else 0 for c in column)
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max(width + 2, 10), 60)
    for row_idx in highlight_rows or ():
        for cell in ws[row_idx]:
            cell.fill = RISK_FILL


def write_excel(
    path: Path,
    students: pd.DataFrame,
    subject_stats: pd.DataFrame,
    at_risk: pd.DataFrame,
    data: pd.DataFrame,
    subjects: list[str],
) -> Path:
    """Write Students, Subjects, Follow-up and Scores sheets. At-risk students are highlighted."""
    path.parent.mkdir(parents=True, exist_ok=True)
    risk_ids = set(at_risk[ID_COLUMN])
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        students.to_excel(writer, sheet_name="Students", index=False)
        subject_stats.to_excel(writer, sheet_name="Subjects", index=False)
        at_risk.to_excel(writer, sheet_name="Follow-up", index=False)
        data[[ID_COLUMN, NAME_COLUMN, *subjects]].to_excel(writer, sheet_name="Scores", index=False)

        highlight = {i + 2 for i, sid in enumerate(students[ID_COLUMN]) if sid in risk_ids}
        _format_sheet(writer.sheets["Students"], highlight)
        _format_sheet(writer.sheets["Subjects"])
        _format_sheet(writer.sheets["Follow-up"])
        _format_sheet(writer.sheets["Scores"])
    return path


def _safe_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_") or "student"


def write_student_cards(
    out_dir: Path,
    students: pd.DataFrame,
    at_risk: pd.DataFrame,
    data: pd.DataFrame,
    subjects: list[str],
    subject_stats: pd.DataFrame,
    settings: Settings,
) -> list[Path]:
    """One Markdown file per student with their scores next to the class average."""
    out_dir.mkdir(parents=True, exist_ok=True)
    by_id = data.set_index(ID_COLUMN)
    class_mean = subject_stats.set_index("subject")["mean"]
    reasons = dict(zip(at_risk[ID_COLUMN], at_risk["reasons"]))
    total = len(students)
    paths = []

    for _, st in students.iterrows():
        sid = st[ID_COLUMN]
        lines = [
            f"# Report card: {st[NAME_COLUMN]}",
            "",
            f"- **Student ID:** {sid}",
            f"- **Average:** {st['average']:g} ({st['letter']})",
            f"- **Class rank:** {st['rank']} of {total}",
            f"- **Strongest subject:** {st['best_subject']}",
            f"- **Needs the most work:** {st['weakest_subject']}",
            "",
            "| Subject | Score | Grade | Class average | Difference |",
            "|:--|--:|:-:|--:|--:|",
        ]
        for subject in subjects:
            score = by_id.at[sid, subject]
            avg = class_mean[subject]
            if pd.isna(score):
                lines.append(f"| {subject} | missing | - | {avg:g} | - |")
            else:
                diff = score - avg
                lines.append(
                    f"| {subject} | {score:g} | {letter_grade(score, settings.pass_mark)} "
                    f"| {avg:g} | {diff:+.1f} |"
                )
        lines.append("")
        if sid in reasons:
            lines.append(f"> **Follow-up needed:** {reasons[sid]}.")
        else:
            lines.append("> No follow-up needed.")
        lines.append("")

        path = out_dir / f"{sid}_{_safe_filename(st[NAME_COLUMN])}.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        paths.append(path)
    return paths
