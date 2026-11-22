"""Per-student and per-subject statistics, plus the follow-up (at-risk) list."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .loader import ID_COLUMN, NAME_COLUMN


@dataclass(frozen=True)
class Settings:
    pass_mark: float = 50
    risk_average: float = 60
    max_failed_subjects: int = 1


def letter_grade(score: float, pass_mark: float = 50) -> str:
    """A >= 90, B >= 80, C >= 70, D >= pass mark, F below it."""
    if pd.isna(score):
        return "-"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= pass_mark:
        return "D"
    return "F"


def student_summary(data: pd.DataFrame, subjects: list[str], settings: Settings) -> pd.DataFrame:
    """One row per student: average, letter, rank, failed subjects, best and weakest subject."""
    scores = data[subjects]
    out = data[[ID_COLUMN, NAME_COLUMN]].copy()

    out["average"] = scores.mean(axis=1, skipna=True).round(1)
    out["letter"] = out["average"].apply(letter_grade, pass_mark=settings.pass_mark)
    out["failed_subjects"] = (scores < settings.pass_mark).sum(axis=1)
    out["missing_scores"] = scores.isna().sum(axis=1)

    has_scores = scores.notna().any(axis=1)
    filled_high = scores.fillna(-np.inf)
    filled_low = scores.fillna(np.inf)
    out["best_subject"] = np.where(has_scores, filled_high.idxmax(axis=1), "-")
    out["weakest_subject"] = np.where(has_scores, filled_low.idxmin(axis=1), "-")

    out["rank"] = out["average"].rank(ascending=False, method="min").astype("Int64")
    return out.sort_values(["rank", NAME_COLUMN]).reset_index(drop=True)


def subject_summary(data: pd.DataFrame, subjects: list[str], settings: Settings) -> pd.DataFrame:
    """One row per subject: mean, median, spread, range and pass rate."""
    rows = []
    for subject in subjects:
        s = data[subject].dropna()
        rows.append(
            {
                "subject": subject,
                "students": int(s.size),
                "mean": round(s.mean(), 1) if s.size else np.nan,
                "median": round(s.median(), 1) if s.size else np.nan,
                "std": round(s.std(ddof=0), 1) if s.size else np.nan,
                "min": s.min() if s.size else np.nan,
                "max": s.max() if s.size else np.nan,
                "pass_rate_%": round((s >= settings.pass_mark).mean() * 100, 1) if s.size else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values("mean").reset_index(drop=True)


def at_risk_students(
    students: pd.DataFrame, data: pd.DataFrame, subjects: list[str], settings: Settings
) -> pd.DataFrame:
    """Students who need follow-up, with a plain-language reason for each."""
    by_id = data.set_index(ID_COLUMN)
    rows = []
    for _, st in students.iterrows():
        reasons = []
        if pd.notna(st["average"]) and st["average"] < settings.risk_average:
            reasons.append(f"average {st['average']:g} is below {settings.risk_average:g}")
        if st["failed_subjects"] > settings.max_failed_subjects:
            failed = [
                s for s in subjects
                if pd.notna(by_id.at[st[ID_COLUMN], s]) and by_id.at[st[ID_COLUMN], s] < settings.pass_mark
            ]
            reasons.append(f"failed {len(failed)} subjects ({', '.join(failed)})")
        if st["missing_scores"]:
            reasons.append(f"{st['missing_scores']} missing score(s)")
        if reasons:
            rows.append(
                {
                    ID_COLUMN: st[ID_COLUMN],
                    NAME_COLUMN: st[NAME_COLUMN],
                    "average": st["average"],
                    "weakest_subject": st["weakest_subject"],
                    "reasons": "; ".join(reasons),
                }
            )
    columns = [ID_COLUMN, NAME_COLUMN, "average", "weakest_subject", "reasons"]
    return pd.DataFrame(rows, columns=columns).sort_values("average").reset_index(drop=True)


def class_overview(students: pd.DataFrame, settings: Settings) -> dict[str, float | int]:
    """Headline numbers for the console summary."""
    avg = students["average"].dropna()
    return {
        "students": int(len(students)),
        "class_average": round(float(avg.mean()), 1) if avg.size else float("nan"),
        "highest_average": float(avg.max()) if avg.size else float("nan"),
        "lowest_average": float(avg.min()) if avg.size else float("nan"),
        "passing_students_%": round(float((avg >= settings.pass_mark).mean() * 100), 1) if avg.size else float("nan"),
    }
