import os
from typing import Optional, Dict, Literal

import pandas as pd

# ---- Configuration ----

# Name of the cleaned rent dataset (you can change this if you rename the file)
_DATA_FILENAME = "new cleaned data.csv"

# Cache for the loaded DataFrame
_DATA_CACHE: Optional[pd.DataFrame] = None


def _get_data_path() -> str:
    """
    Resolve the path to the cleaned rent dataset.

    Assumes this file lives in the same folder as recommender.py and that
    the CSV is inside a 'data' subfolder:

        project_root/
          app.py
          chatbot.py
          recommender.py
          data/
            new cleaned data.csv
    """
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "data", _DATA_FILENAME)


def _compute_growth_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add growth-related columns to the DataFrame in-place and return it.

    Computes:
    - rent_3yr_change
    - rent_3yr_pct_change
    - rent_5yr_change
    - rent_5yr_pct_change
    - trend_label (simple 'rising' / 'flat' / 'falling' based on 3yr % change)
    """
    # We assume yearly columns exist; if not, this will raise clearly.
    # You can guard with `if "2022_Avg_Rent" in df.columns` if needed.
    df = df.copy()

    # 3-year: 2022 -> Current
    if {"2022_Avg_Rent", "Current_Rent"}.issubset(df.columns):
        df["rent_3yr_change"] = df["Current_Rent"] - df["2022_Avg_Rent"]
        df["rent_3yr_pct_change"] = (
            (df["rent_3yr_change"] / df["2022_Avg_Rent"]) * 100.0
        )

    # 5-year: 2021 -> Current
    if {"2021_Avg_Rent", "Current_Rent"}.issubset(df.columns):
        df["rent_5yr_change"] = df["Current_Rent"] - df["2021_Avg_Rent"]
        df["rent_5yr_pct_change"] = (
            (df["rent_5yr_change"] / df["2021_Avg_Rent"]) * 100.0
        )

    # Simple trend label from 3-year % change
    def _label_trend(pct: float) -> str:
        if pd.isna(pct):
            return "unknown"
        if pct > 10:
            return "rising"
        if pct < -5:
            return "falling"
        return "flat"

    if "rent_3yr_pct_change" in df.columns:
        df["trend_label"] = df["rent_3yr_pct_change"].apply(_label_trend)
    else:
        df["trend_label"] = "unknown"

    return df


def load_data() -> pd.DataFrame:
    """
    Load the cleaned rent dataset with growth columns, cached in memory.

    Returns:
        pandas.DataFrame with at least:
            RegionName, StateName, Current_Rent,
            2021_Avg_Rent, 2022_Avg_Rent, 2023_Avg_Rent,
            2024_Avg_Rent, 2025_Avg_Rent
        and computed columns:
            rent_3yr_change, rent_3yr_pct_change,
            rent_5yr_change, rent_5yr_pct_change,
            trend_label
    """
    global _DATA_CACHE
    if _DATA_CACHE is None:
        data_path = _get_data_path()
        df = pd.read_csv(data_path)

        # Normalize column names a bit
        df = df.rename(
            columns={
                "StateName": "State",
            }
        )

        # Ensure numeric columns are floats
        rent_cols = [
            c
            for c in df.columns
            if "Rent" in c or "Avg_Rent" in c or c == "Current_Rent"
        ]
        for col in rent_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = _compute_growth_columns(df)
        _DATA_CACHE = df

    return _DATA_CACHE


def filter_by_budget(
    monthly_budget: float,
    state: Optional[str] = None,
    trend: Optional[Literal["rising", "flat", "falling"]] = None,
    include_us_aggregate: bool = False,
) -> pd.DataFrame:
    """
    Filter metros whose Current_Rent is <= monthly_budget.

    Args:
        monthly_budget: User's monthly rent budget in dollars.
        state: Optional state filter (2-letter code, e.g. 'CA').
        trend: Optional trend filter: 'rising', 'flat', or 'falling'.
        include_us_aggregate: whether to include 'United States' aggregate row.

    Returns:
        DataFrame sorted by Current_Rent ascending.
    """
    df = load_data().copy()

    # Filter out United States aggregate row by default
    if not include_us_aggregate:
        df = df[df["RegionName"] != "United States"]

    df = df[df["Current_Rent"].notna()]
    df = df[df["Current_Rent"] <= monthly_budget]

    if state:
        state = state.upper()
        df = df[df["State"].fillna("").str.upper() == state]

    if trend:
        df = df[df["trend_label"] == trend]

    df = df.sort_values("Current_Rent", ascending=True)
    return df


def cheapest_metros(
    limit: int = 10,
    state: Optional[str] = None,
    include_us_aggregate: bool = False,
) -> pd.DataFrame:
    """
    Return the cheapest metros by Current_Rent.

    Args:
        limit: number of rows to return.
        state: optional state filter.
        include_us_aggregate: whether to include the 'United States' row.

    Returns:
        DataFrame sorted by Current_Rent ascending.
    """
    df = load_data().copy()

    if not include_us_aggregate:
        df = df[df["RegionName"] != "United States"]

    df = df[df["Current_Rent"].notna()]

    if state:
        state = state.upper()
        df = df[df["State"].fillna("").str.upper() == state]

    df = df.sort_values("Current_Rent", ascending=True)
    return df.head(limit)


def most_expensive_metros(
    limit: int = 10,
    state: Optional[str] = None,
    include_us_aggregate: bool = False,
) -> pd.DataFrame:
    """
    Return the most expensive metros by Current_Rent.

    Args:
        limit: number of rows to return.
        state: optional state filter.
        include_us_aggregate: whether to include the 'United States' row.

    Returns:
        DataFrame sorted by Current_Rent descending.
    """
    df = load_data().copy()

    if not include_us_aggregate:
        df = df[df["RegionName"] != "United States"]

    df = df[df["Current_Rent"].notna()]

    if state:
        state = state.upper()
        df = df[df["State"].fillna("").str.upper() == state]

    df = df.sort_values("Current_Rent", ascending=False)
    return df.head(limit)


def best_rent_growth(
    limit: int = 10,
    horizon: Literal["3y", "5y"] = "3y",
    direction: Literal["up", "down"] = "up",
    state: Optional[str] = None,
    include_us_aggregate: bool = False,
) -> pd.DataFrame:
    """
    Return metros with the strongest or weakest rent growth.

    Args:
        limit: number of rows to return.
        horizon: '3y' or '5y' (3-year or 5-year % change).
        direction: 'up' for fastest appreciation, 'down' for biggest declines.
        state: optional state filter.
        include_us_aggregate: whether to include 'United States' row.

    Returns:
        DataFrame sorted by the chosen % change.
    """
    df = load_data().copy()

    if not include_us_aggregate:
        df = df[df["RegionName"] != "United States"]

    if state:
        state = state.upper()
        df = df[df["State"].fillna("").str.upper() == state]

    if horizon == "3y":
        col = "rent_3yr_pct_change"
    else:
        col = "rent_5yr_pct_change"

    df = df[df[col].notna()]

    ascending = direction == "down"
    df = df.sort_values(col, ascending=ascending)

    return df.head(limit)


def compare_metros(metro_a: str, metro_b: str) -> Dict[str, Optional[Dict]]:
    """
    Compare two metros by name.

    The matching is case-insensitive and will first try exact match on RegionName.
    If that fails, it will fall back to 'contains' search.

    Returns:
        {
          "a": { ... row for metro_a ... } or None,
          "b": { ... row for metro_b ... } or None
        }

    Each row dict includes growth metrics and rent columns, so the chatbot or
    LLM layer can format a nice natural-language comparison.
    """
    df = load_data()

    def _find(metro: str) -> Optional[Dict]:
        # Exact match
        exact = df[df["RegionName"].str.lower() == metro.lower()]
        if not exact.empty:
            return exact.iloc[0].to_dict()

        # Contains
        subset = df[df["RegionName"].str.lower().str.contains(metro.lower())]
        if not subset.empty:
            return subset.iloc[0].to_dict()

        return None

    info_a = _find(metro_a)
    info_b = _find(metro_b)

    return {"a": info_a, "b": info_b}
