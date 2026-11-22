"""Generate the fictional sample gradebook in sample_data/.

All names and scores are made up. Run from the project root:

    python scripts/make_sample_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

FIRST_NAMES = [
    "Ahmad", "Lina", "Omar", "Sara", "Yousef", "Rania", "Khaled", "Dana",
    "Hamza", "Noor", "Zaid", "Leen", "Faris", "Tala", "Bilal", "Hala",
    "Majd", "Rawan", "Sami", "Jana", "Tariq", "Aya", "Laith", "Mira",
    "Kareem", "Salma", "Nabil", "Yara", "Adam", "Huda",
]
LAST_NAMES = ["Haddad", "Khalil", "Nasser", "Saleh", "Qasem", "Mansour", "Hamdan", "Darwish"]
SUBJECTS = {
    # subject: (mean, spread)
    "Python": (74, 14),
    "Math": (68, 16),
    "Databases": (72, 12),
    "Web Development": (78, 11),
    "English": (80, 9),
}


def main() -> None:
    rng = np.random.default_rng(seed=2026)
    rows = []
    for i, first in enumerate(FIRST_NAMES, start=1):
        ability = rng.normal(-2, 11)  # some students are stronger across the board
        row = {"student_id": f"S{i:03d}", "name": f"{first} {rng.choice(LAST_NAMES)}"}
        for subject, (mean, spread) in SUBJECTS.items():
            score = rng.normal(mean + ability, spread)
            row[subject] = int(np.clip(round(score), 0, 100))
        rows.append(row)

    df = pd.DataFrame(rows)
    # a couple of missing scores, as real gradebooks have
    df.loc[6, "Math"] = np.nan
    df.loc[19, "Databases"] = np.nan

    out = Path(__file__).resolve().parent.parent / "sample_data"
    out.mkdir(exist_ok=True)
    df.to_csv(out / "class_grades.csv", index=False)
    df.to_excel(out / "class_grades.xlsx", index=False)
    print(f"Wrote {len(df)} students to {out}")


if __name__ == "__main__":
    main()
