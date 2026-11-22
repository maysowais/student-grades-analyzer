"""Charts saved as PNG files."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to files, no window needed
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

PRIMARY = "#7B3B6E"
SECONDARY = "#D2668A"
MUTED = "#B8A9B5"
GRID = "#E6E0E5"


def _style(ax: plt.Axes, title: str) -> None:
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", color="#2B2130")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def average_distribution(students: pd.DataFrame, pass_mark: float, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bins = list(range(0, 101, 5))
    ax.hist(students["average"].dropna(), bins=bins, color=PRIMARY, edgecolor="white")
    ax.axvline(pass_mark, color=SECONDARY, linestyle="--", linewidth=1.5)
    ax.text(pass_mark + 1, ax.get_ylim()[1] * 0.92, f"pass mark ({pass_mark:g})", color=SECONDARY)
    ax.set_xlabel("Student average")
    ax.set_ylabel("Number of students")
    ax.set_xlim(0, 100)
    _style(ax, "How student averages are spread")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def subject_boxplot(data: pd.DataFrame, subjects: list[str], pass_mark: float, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    series = [data[s].dropna() for s in subjects]
    box = ax.boxplot(series, tick_labels=subjects, patch_artist=True, widths=0.55)
    for patch in box["boxes"]:
        patch.set(facecolor="#EBD9E6", edgecolor=PRIMARY)
    for key in ("whiskers", "caps"):
        for line in box[key]:
            line.set(color=PRIMARY)
    for line in box["medians"]:
        line.set(color=SECONDARY, linewidth=2)
    ax.axhline(pass_mark, color=SECONDARY, linestyle="--", linewidth=1)
    ax.set_ylabel("Score")
    ax.set_ylim(0, 100)
    _style(ax, "Score range by subject")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def pass_rates(subject_stats: pd.DataFrame, path: Path) -> Path:
    stats = subject_stats.sort_values("pass_rate_%")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = [SECONDARY if r < 80 else PRIMARY for r in stats["pass_rate_%"]]
    bars = ax.barh(stats["subject"], stats["pass_rate_%"], color=colors)
    ax.bar_label(bars, fmt="%.0f%%", padding=4, color="#2B2130")
    ax.set_xlim(0, 110)
    ax.set_xlabel("Students who passed (%)")
    _style(ax, "Pass rate by subject")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def save_all(
    data: pd.DataFrame,
    subjects: list[str],
    students: pd.DataFrame,
    subject_stats: pd.DataFrame,
    pass_mark: float,
    out_dir: Path,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return [
        average_distribution(students, pass_mark, out_dir / "average_distribution.png"),
        subject_boxplot(data, subjects, pass_mark, out_dir / "subject_scores.png"),
        pass_rates(subject_stats, out_dir / "pass_rates.png"),
    ]
