import os
from typing import Optional, List, Dict
import pandas as pd


_DATA_CACHE = None


def _data_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "data", "cleaned_zillow_dataset.csv")


def load_data() -> pd.DataFrame:
    """Load the cleaned Zillow dataset (cached)."""
    global _DATA_CACHE
    if _DATA_CACHE is None:
        df = pd.read_csv(_DATA_PATH)
    return _DATA_CACHE
    # NOTE: This function is intentionally kept simple for demonstration.

# Fix variable name (we need a module-level constant)
_DATA_PATH = _DATA_PATH = _DATA_PATH = _data_path()


def load_data() -> pd.DataFrame:
    """Load the cleaned Zillow dataset (cached)."""
    global _DATA_CACHE
    if _DATA_CACHE is None:
        _DATA_CACHE = pd.read_csv(_DATA_PATH)
    return _DATA_CACHE


def filter_by_budget(
    budget: float,
    bedrooms: Optional[int] = None,
    home_type: Optional[str] = None,
    state: Optional[str] = None,
    tier: Optional[str] = None,
    price_multiplier: float = 1.0,
) -> pd.DataFrame:
    """
    Filter metros by an approximate budget.

    Args:
        budget: Either an approximate home price or a monthly rent.
        bedrooms: Optional minimum bedroom count.
        home_type: 'sfr', 'condo', or 'sfr+condo' (case-insensitive).
        state: Optional 2-letter state filter.
        tier: Optional tier string (e.g. '0.33_0.67').
        price_multiplier: If treating budget as monthly rent, multiply to approximate home price.

    Returns:
        Filtered DataFrame sorted from cheapest to most expensive.
    """
    df = load_data().copy()

    # Normalise filters
    max_price = budget * price_multiplier

    df = df[df["Latest_ZHVI"].notna()]

    if bedrooms is not None:
        df = df[(df["Bedrooms"].isna()) | (df["Bedrooms"] >= bedrooms)]

    if home_type:
        home_type = home_type.lower()
        df = df[df["HomeType"].str.lower() == home_type]

    if state:
        state = state.upper()
        df = df[df["State"].fillna("").str.upper() == state]

    if tier:
        df = df[df["Tier"] == tier]

    df = df[df["Latest_ZHVI"] <= max_price]

    df = df.sort_values("Latest_ZHVI", ascending=True)
    return df


def cheapest_metros(limit: int = 10) -> pd.DataFrame:
    """Return the globally cheapest metros by latest ZHVI."""
    df = load_data().copy()
    df = df[df["Latest_ZHVI"].notna()]
    return df.sort_values("Latest_ZHVI", ascending=True).head(limit)


def compare_metros(metro_a: str, metro_b: str) -> Dict[str, Dict]:
    """Compare two metros by RegionName string match.


    Returns a dict with basic info for each metro.
    """
    df = load_data()

    def _find(metro: str):
        exact = df[df["RegionName"].str.lower() == metro.lower()]
        if not exact.empty:
            return exact.iloc[0].to_dict()

        # fallback: contains
        subset = df[df["RegionName"].str.lower().str.contains(metro.lower())]
        if not subset.empty:
            return subset.iloc[0].to_dict()
        return None

    info_a = _find(metro_a)
    info_b = _find(metro_b)

    return {"a": info_a, "b": info_b}
