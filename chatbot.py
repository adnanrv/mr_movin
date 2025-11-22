import re
from typing import Optional, Tuple
from recommender import filter_by_budget, cheapest_metros, compare_metros


def _parse_budget(text: str) -> Optional[float]:
    """Extract a numeric budget from user text.

    Assumes the first reasonable positive number is the budget.
    """
    # Remove commas and $
    cleaned = text.replace(",", "").replace("$", " ")
    nums = re.findall(r"(\d+\.?\d*)", cleaned)
    if not nums:
        return None
    try:
        value = float(nums[0])
        if value <= 0:
            return None
        return value
    except ValueError:
        return None


def _parse_bedrooms(text: str) -> Optional[int]:
    """Try to extract a bedroom count from text."""
    match = re.search(r"(\d+)\s*(bed|br|bedroom)", text, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _looks_like_monthly_rent(budget: float) -> bool:
    """Heuristic: values between ~500 and ~10000 look like monthly rent."""
    return 500 <= budget <= 10000


def _parse_compare_request(text: str) -> Optional[Tuple[str, str]]:
    """Rough parsing of 'compare X and Y' type requests."""
    if "compare" not in text.lower():
        return None
    # Try to split on ' and '
    parts = re.split(r"\band\b", text, flags=re.IGNORECASE)
    if len(parts) < 2:
        return None
    # Take last two segments as candidate city strings
    a = parts[-2].strip()
    b = parts[-1].strip()
    # Remove leading 'compare' word if present
    a = re.sub(r"^compare", "", a, flags=re.IGNORECASE).strip(", .")
    b = b.strip(", .")
    if not a or not b:
        return None
    return a, b


def chat(message: str, history=None) -> str:
    """Core chat handler.

    This is intentionally simple: it parses the message for budget/bedrooms
    or a compare intent, calls the recommender, and returns a text reply.
    """
    message = message.strip()
    if not message:
        return "Hi! Tell me about your budget and what you're looking for in a metro area."

    # 1) Check if this is a compare request
    compare_pair = _parse_compare_request(message)
    if compare_pair:
        a, b = compare_pair
        result = compare_metros(a, b)
        info_a, info_b = result["a"], result["b"]

        if not info_a and not info_b:
            return "I couldn't find either of those metros in the dataset. Try using the exact metro names like 'Seattle, WA'."
        if not info_a or not info_b:
            missing = a if not info_a else b
            return f"I could only find one of those metros in the dataset. I couldn't locate '{missing}'. Try using the format 'City, ST'."

        def fmt(info):
            zhvi = info.get("Latest_ZHVI", "?")
            home_type = info.get("HomeType", "unknown")
            beds = info.get("Bedrooms", "any")
            state = info.get("State", "")
            name = info.get("RegionName", "(unknown)")
            return f"{name} ({state}) — ~${zhvi:,.0f} median for {home_type}, bedrooms: {beds}"

        text_a = fmt(info_a)
        text_b = fmt(info_b)

        diff = info_b["Latest_ZHVI"] - info_a["Latest_ZHVI"]
        more = "more" if diff > 0 else "less"
        diff_abs = abs(diff)

        return (
            "Here's a quick comparison based on the latest Zillow home value estimates (ZHVI):\n\n"
            f"- {text_a}\n"
            f"- {text_b}\n\n"
            f"{info_b['RegionName']} is about ${diff_abs:,.0f} {more} expensive than {info_a['RegionName']} based on this dataset."
        )

    # 2) Otherwise, try to interpret as a budgeted search
    budget = _parse_budget(message)
    bedrooms = _parse_bedrooms(message)

    if budget is None:
        # No budget: just show cheapest metros
        df = cheapest_metros(limit=10)
        lines = [
            "Here are some of the cheapest metros in the dataset by median home value (ZHVI):\n"
        ]
        for _, row in df.iterrows():
            lines.append(
                f"- {row['RegionName']} ({row.get('State','')}) — ~${row['Latest_ZHVI']:,.0f}"
            )
        lines.append("\nYou can also tell me your budget and preferred bedroom count, and I'll narrow this list down.")
        return "\n".join(lines)

    # Determine if budget looks like monthly rent, and pick a multiplier accordingly
    if _looks_like_monthly_rent(budget):
        multiplier = 100.0  # very rough heuristic for demo
        budget_type_desc = "(interpreted as monthly rent; approximating a home price using 100x)"
    else:
        multiplier = 1.0
        budget_type_desc = "(interpreted as a home price budget)"

    df = filter_by_budget(
        budget=budget,
        bedrooms=bedrooms,
        price_multiplier=multiplier,
    )

    if df.empty:
        return (
            f"I couldn't find metros with median home values under your budget {budget_type_desc}.\n"
            "Try increasing your budget, or ask me to 'show some of the cheapest metros'."
        )

    # Show top 10 matches
    df = df.head(10)
    lines = [
        f"Here are some metros with median home values roughly under your budget {budget_type_desc}:\n"
    ]
    for _, row in df.iterrows():
        lines.append(
            f"- {row['RegionName']} ({row.get('State','')}) — ~${row['Latest_ZHVI']:,.0f}"
        )

    if bedrooms:
        lines.append(f"\nThese results allow for at least {bedrooms} bedrooms when that information is available.")
    else:
        lines.append("\nYou can also mention how many bedrooms you need (e.g. '3 bedroom').")

    return "\n".join(lines)
