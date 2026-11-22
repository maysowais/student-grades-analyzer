"""Read a gradebook from CSV or Excel and check that it is usable."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ID_COLUMN = "student_id"
NAME_COLUMN = "name"
MIN_SCORE = 0
MAX_SCORE = 100


class GradebookError(ValueError):
    """Raised when the input file cannot be used as a gradebook."""


@dataclass
class Gradebook:
    data: pd.DataFrame
    subjects: list[str]
    warnings: list[str]


def _read_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(path, engine="openpyxl")
    raise GradebookError(f"Unsupported file type '{suffix}'. Use .csv or .xlsx.")


def _normalise_header(name: object) -> str:
    return str(name).strip().lower().replace(" ", "_")


def load_gradebook(path: str | Path) -> Gradebook:
    """Load a gradebook with one row per student and one column per subject.

    Required columns: ``student_id`` and ``name`` (any case, spaces allowed).
    Every other column is treated as a subject and must hold scores from 0 to 100.
    Empty cells are kept as missing scores and reported as warnings.
    """
    path = Path(path)
    if not path.exists():
        raise GradebookError(f"File not found: {path}")

    raw = _read_file(path)
    raw = raw.dropna(how="all")
    if raw.empty:
        raise GradebookError("The file has no student rows.")

    original_headers = {_normalise_header(c): str(c).strip() for c in raw.columns}
    raw.columns = [_normalise_header(c) for c in raw.columns]

    missing = [c for c in (ID_COLUMN, NAME_COLUMN) if c not in raw.columns]
    if missing:
        raise GradebookError(f"Missing required column(s): {', '.join(missing)}")

    if raw[ID_COLUMN].duplicated().any():
        dupes = raw.loc[raw[ID_COLUMN].duplicated(), ID_COLUMN].astype(str).tolist()
        raise GradebookError(f"Duplicate student_id values: {', '.join(dupes)}")

    subject_keys = [c for c in raw.columns if c not in (ID_COLUMN, NAME_COLUMN)]
    if not subject_keys:
        raise GradebookError("No subject columns found next to student_id and name.")

    warnings: list[str] = []
    data = raw[[ID_COLUMN, NAME_COLUMN]].copy()
    data[ID_COLUMN] = data[ID_COLUMN].astype(str).str.strip()
    data[NAME_COLUMN] = data[NAME_COLUMN].astype(str).str.strip()

    subjects: list[str] = []
    for key in subject_keys:
        label = original_headers[key]
        scores = pd.to_numeric(raw[key], errors="coerce")

        not_numeric = raw[key].notna() & scores.isna()
        if not_numeric.any():
            bad = raw.loc[not_numeric, key].astype(str).tolist()
            raise GradebookError(f"Non-numeric score(s) in '{label}': {', '.join(bad)}")

        out_of_range = scores.notna() & ((scores < MIN_SCORE) | (scores > MAX_SCORE))
        if out_of_range.any():
            bad = scores[out_of_range].tolist()
            raise GradebookError(
                f"Score(s) outside {MIN_SCORE}-{MAX_SCORE} in '{label}': {bad}"
            )

        blank = int(scores.isna().sum())
        if blank:
            warnings.append(f"{blank} missing score(s) in '{label}'")

        data[label] = scores
        subjects.append(label)

    return Gradebook(data=data.reset_index(drop=True), subjects=subjects, warnings=warnings)
