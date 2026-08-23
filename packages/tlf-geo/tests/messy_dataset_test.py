"""
Stress-test GeoResolver.resolve_df() against a deliberately messy dataset
mirroring real TLF data-quality issues (casing, suffix variants, Nepali
script, typos, missing values, wrong districts).

Run from packages/tlf-geo/src (or wherever your dev setup already runs
geo_resolver.py from) with:

    python messy_dataset_test.py
"""

import pandas as pd
from tlf_geo import GeoResolver

# widen pandas display so the report doesn't get truncated mid-column
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 40)


def main():
    resolver = GeoResolver()

    df = pd.read_csv("messy_test_dataset.csv")

    print(f"Loaded {len(df)} rows from messy_test_dataset.csv\n")

    result = resolver.resolve_df(
        df,
        name_col="place_name",
        district_col="district_name",
    )

    # ---- Summary: how many rows landed in each geo_status bucket ----
    print("=== geo_status breakdown ===")
    print(result["geo_status"].value_counts(dropna=False))
    print()

    # ---- Full report: every row, status, and why (if it failed) ----
    print("=== Full report ===")
    report_cols = ["place_name", "district_name", "notes",
                   "geo_status", "geo_code", "geo_name", "geo_error_reason"]
    print(result[report_cols].to_string(index=False))
    print()

    # ---- Just the problem rows, for focused review ----
    problems = result[result["geo_status"] != "resolved"]
    print(f"=== {len(problems)} rows needing attention ===")
    print(problems[["place_name", "notes",
          "geo_status", "geo_error_reason"]].to_string(index=False))


if __name__ == "__main__":
    main()
