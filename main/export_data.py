"""Save the processed World Bank data as CSV. Run from the repo root: python main/export_data.py"""

from pathlib import Path

import pandas as pd

from progress import YEARS, compare_years, load_world_bank_data

OUT = Path(__file__).resolve().parent / "data"

rows, updates = load_world_bank_data()
OUT.mkdir(exist_ok=True)

# Country-year panel: access rate, population, and the estimated number without electricity.
panel = pd.DataFrame(rows).sort_values(["country", "year"])
panel.to_csv(OUT / "electricity_access_by_country_year.csv", index=False)

# The dashboard's default comparison (2010 vs 2024), with the paradox flag and the population/access split.
pd.DataFrame(compare_years(rows, 2010, 2024)).to_csv(OUT / "paradox_comparison_2010_2024.csv", index=False)

print(f"Saved {len(panel)} country-years ({YEARS}) to {OUT}. World Bank last updated: {updates['access']}.")
