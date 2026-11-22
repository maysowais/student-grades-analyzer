"""Command-line entry point: python -m grades_analyzer <gradebook>."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, charts, report
from .analysis import (
    Settings,
    at_risk_students,
    class_overview,
    student_summary,
    subject_summary,
)
from .loader import GradebookError, load_gradebook


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="grades-analyzer",
        description="Analyze a class gradebook (CSV or Excel) and produce reports, charts "
        "and a list of students who need follow-up.",
    )
    p.add_argument("gradebook", type=Path, help="CSV or XLSX file: student_id, name, then one column per subject")
    p.add_argument("-o", "--output", type=Path, default=Path("output"), help="output folder (default: output)")
    p.add_argument("--pass-mark", type=float, default=50, help="minimum passing score (default: 50)")
    p.add_argument("--risk-average", type=float, default=60,
                   help="flag students whose average is below this (default: 60)")
    p.add_argument("--max-failed", type=int, default=1,
                   help="flag students who fail more subjects than this (default: 1)")
    p.add_argument("--no-charts", action="store_true", help="skip the PNG charts")
    p.add_argument("--no-cards", action="store_true", help="skip the per-student report cards")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings(
        pass_mark=args.pass_mark,
        risk_average=args.risk_average,
        max_failed_subjects=args.max_failed,
    )

    try:
        book = load_gradebook(args.gradebook)
    except GradebookError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    students = student_summary(book.data, book.subjects, settings)
    subjects = subject_summary(book.data, book.subjects, settings)
    at_risk = at_risk_students(students, book.data, book.subjects, settings)
    overview = class_overview(students, settings)

    out: Path = args.output
    excel_path = report.write_excel(out / "grades_report.xlsx", students, subjects, at_risk,
                                    book.data, book.subjects)
    chart_paths = [] if args.no_charts else charts.save_all(
        book.data, book.subjects, students, subjects, settings.pass_mark, out / "charts"
    )
    card_paths = [] if args.no_cards else report.write_student_cards(
        out / "report_cards", students, at_risk, book.data, book.subjects, subjects, settings
    )

    print(f"\nGradebook: {args.gradebook.name}  ({overview['students']} students, "
          f"{len(book.subjects)} subjects)")
    for warning in book.warnings:
        print(f"  warning: {warning}")
    print(f"\nClass average:     {overview['class_average']}")
    print(f"Highest / lowest:  {overview['highest_average']} / {overview['lowest_average']}")
    print(f"Passing students:  {overview['passing_students_%']}%")
    hardest = subjects.iloc[0]
    print(f"Hardest subject:   {hardest['subject']} (mean {hardest['mean']}, "
          f"pass rate {hardest['pass_rate_%']}%)")

    print("\nTop 3 students:")
    for _, st in students.head(3).iterrows():
        print(f"  {st['rank']}. {st['name']}  {st['average']}")

    print(f"\nNeeds follow-up: {len(at_risk)} student(s)")
    for _, st in at_risk.iterrows():
        print(f"  - {st['name']} ({st['average']}): {st['reasons']}")

    print(f"\nSaved: {excel_path}")
    if chart_paths:
        print(f"       {len(chart_paths)} charts in {out / 'charts'}")
    if card_paths:
        print(f"       {len(card_paths)} report cards in {out / 'report_cards'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
