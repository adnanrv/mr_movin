import re
from typing import Optional, Tuple, Literal, List

from recommender import (
    filter_by_budget,
    cheapest_metros,
    most_expensive_metros,
    best_rent_growth,
    compare_metros,
)

from llm_helpers import polish_response


# --- Helpers to parse user intent & entities --- #

_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
}


def _parse_budget(text: str) -> Optional[float]:
    """
    Extract a numeric monthly budget from text.

    Heuristic: the first positive number that looks like a realistic
    monthly rent (roughly 300–20,000) is treated as the budget.
    """
    cleaned = text.replace(",", "").replace("$", " ")
    nums = re.findall(r"(\d+\.?\d*)", cleaned)
    if not nums:
        return None

    for n in nums:
        try:
            value = float(n)
        except ValueError:
            continue
        # Heuristic bounds for monthly rent
        if 300 <= value <= 20000:
            return value

    # If nothing in that range, fall back to the first number
    try:
        return float(nums[0])
    except ValueError:
        return None


def _parse_state(text: str) -> Optional[str]:
    """
    Try to pull a US state code from the text.

    Looks for patterns like 'in CA', 'in Texas' (TX), etc.
    For simplicity, we only support 2-letter codes directly.
    """
    # Direct 2-letter codes
    possible = re.findall(r"\b([A-Z]{2})\b", text.upper())
    for code in possible:
        if code in _US_STATES:
            return code

    # Simple patterns like 'in ca'
    match = re.search(r"\bin\s+([A-Za-z]{2})\b", text, flags=re.IGNORECASE)
    if match:
        code = match.group(1).upper()
        if code in _US_STATES:
            return code

    return None


def _parse_compare_request(text: str) -> Optional[Tuple[str, str]]:
    """
    Rough parsing of 'compare X and Y' type requests.

    Example:
        'Compare Seattle, WA and Austin, TX'
    """
    if "compare" not in text.lower():
        return None

    # Try to split on ' and '
    parts = re.split(r"\band\b", text, flags=re.IGNORECASE)
    if len(parts) < 2:
        return None

    a = parts[-2].strip()
    b = parts[-1].strip()

    a = re.sub(r"^compare", "", a, flags=re.IGNORECASE).strip(",. ")
    b = b.strip(",. ")

    if not a or not b:
        return None

    return a, b


def _is_cheapest_request(text: str) -> bool:
    text_l = text.lower()
    return any(
        kw in text_l
        for kw in [
            "cheapest",
            "low cost",
            "least expensive",
            "affordable metros",
            "most affordable",
        ]
    )


def _is_most_expensive_request(text: str) -> bool:
    text_l = text.lower()
    return any(
        kw in text_l
        for kw in [
            "most expensive",
            "high cost",
            "priciest",
            "top expensive",
        ]
    )


def _parse_growth_intent(
    text: str,
) -> Optional[Tuple[Literal["3y", "5y"], Literal["up", "down"]]]:
    """
    Detect if the user is asking about up-and-coming or declining markets.

    Returns:
        (horizon, direction) or None
        horizon in {"3y", "5y"}, direction in {"up", "down"}.
    """
    t = text.lower()

    # Direction: up (rising) or down (declining)
    if any(kw in t for kw in ["up-and-coming", "up and coming", "rising", "growing"]):
        direction = "up"
    elif any(kw in t for kw in ["declining", "falling", "going down", "cooling"]):
        direction = "down"
    else:
        return None

    # Horizon: 3y vs 5y
    if "5 year" in t or "five year" in t or "5-year" in t:
        horizon = "5y"
    else:
        # default to 3y
        horizon = "3y"

    return horizon, direction


# --- Core chat handler --- #


def chat(message: str, history: Optional[List[tuple]] = None) -> str:
    """
    Main chat handler.

    This function:
      - Parses the user's message for:
          * compare intent
          * budget / state
          * cheapest / most expensive
          * growth (up-and-coming / declining) intent
      - Calls the recommender functions to get structured results
      - Builds a draft text response
      - Polishes that response with an LLM (polish_response)

    Returns:
      A final natural-language reply as a string.
    """
    message = message.strip()
    if not message:
        raw = (
            "Hi! I’m your relocation assistant. "
            "Tell me your monthly rent budget, ask me for the cheapest metros, "
            "or ask me to compare two metros like 'Compare Seattle, WA and Austin, TX'."
        )
        try:
            # return polish_response(raw, message)
            print("DEBUG RAW REPLY:\n", raw)
            return raw
        except Exception:
            return raw

    # 1) Compare intent
    compare_pair = _parse_compare_request(message)
    if compare_pair:
        metro_a, metro_b = compare_pair
        results = compare_metros(metro_a, metro_b)
        info_a, info_b = results["a"], results["b"]

        if not info_a and not info_b:
            raw = (
                "I couldn't find either of those metros in the dataset. "
                "Try using the exact metro names like 'Seattle, WA'."
            )
            try:
                #return polish_response(raw, message)
                print("DEBUG RAW REPLY:\n", raw)
                return raw
            except Exception:
                return raw

        if not info_a or not info_b:
            missing = metro_a if not info_a else metro_b
            raw = (
                f"I could only find one of those metros in the dataset. "
                f"I couldn't locate '{missing}'. Try using the format 'City, ST'."
            )
            try:
                #return polish_response(raw, message)
                print("DEBUG RAW REPLY:\n", raw)
                return raw
            except Exception:
                return raw

        def fmt(meta: dict) -> str:
            name = meta.get("RegionName", "(unknown)")
            state = meta.get("State", "") or ""
            current = meta.get("Current_Rent", None)

            r3 = meta.get("rent_3yr_pct_change", None)
            r5 = meta.get("rent_5yr_pct_change", None)

            pieces = []
            if current is not None:
                pieces.append(f"~${current:,.0f} current avg monthly rent")
            if r3 is not None:
                pieces.append(f"{r3:+.1f}% over the last 3 years")
            if r5 is not None:
                pieces.append(f"{r5:+.1f}% over the last 5 years")

            details = "; ".join(pieces) if pieces else "no growth data available"
            if state:
                return f"{name} ({state}) — {details}"
            else:
                return f"{name} — {details}"

        text_a = fmt(info_a)
        text_b = fmt(info_b)

        diff = info_b.get("Current_Rent", 0) - info_a.get("Current_Rent", 0)
        more = "more" if diff > 0 else "less"
        diff_abs = abs(diff)

        raw = (
            "Here's a quick comparison based on the latest average monthly rent estimates:\n\n"
            f"- {text_a}\n"
            f"- {text_b}\n\n"
        )
        if diff_abs > 0:
            raw += (
                f"{info_b['RegionName']} is about ${diff_abs:,.0f} {more} "
                f"expensive per month than {info_a['RegionName']} based on this data."
            )
        else:
            raw += "Both metros have very similar current rent levels in this dataset."

        try:
            #return polish_response(raw, message)
            print("DEBUG RAW REPLY:\n", raw)
            return raw
        except Exception:
            return raw

    # 2) Growth / trend intent (up-and-coming vs declining)
    growth = _parse_growth_intent(message)
    if growth:
        horizon, direction = growth
        state = _parse_state(message)

        df = best_rent_growth(
            limit=10,
            horizon=horizon,
            direction=direction,
            state=state,
        )

        if df.empty:
            raw = (
                "I couldn't find any metros that match that growth pattern "
                "in the dataset. Try removing the state filter or broadening the request."
            )
            try:
                # return polish_response(raw, message)
                print("DEBUG RAW REPLY:\n", raw)
                return raw
            except Exception:
                return raw

        if direction == "up":
            desc = "up-and-coming (rising rent) metros"
        else:
            desc = "declining (falling or cooling) rent metros"

        if horizon == "5y":
            horizon_desc = "over the last 5 years"
            col = "rent_5yr_pct_change"
        else:
            horizon_desc = "over the last 3 years"
            col = "rent_3yr_pct_change"

        lines = [f"Here are some {desc} {horizon_desc} based on the data:\n"]
        for _, row in df.iterrows():
            name = row["RegionName"]
            state_code = row.get("State", "") or ""
            pct = row[col]
            current = row.get("Current_Rent", None)

            if current is not None:
                lines.append(
                    f"- {name} ({state_code}) — ~${current:,.0f} now, {pct:+.1f}% over {horizon_desc}"
                )
            else:
                lines.append(
                    f"- {name} ({state_code}) — {pct:+.1f}% over {horizon_desc}"
                )

        if state:
            lines.append(
                f"\nThese are limited to metros in {state}. "
                "Ask again without mentioning a state if you want to see the whole country."
            )

        raw = "\n".join(lines)
        try:
            # return polish_response(raw, message)
            print("DEBUG RAW REPLY:\n", raw)
            return raw
        except Exception:
            return raw

    # 3) Cheapest / most expensive requests (no explicit budget)
    if _is_cheapest_request(message):
        state = _parse_state(message)
        df = cheapest_metros(limit=10, state=state)

        if df.empty:
            raw = "I couldn't find any metros in the dataset for that request."
            try:
                return polish_response(raw, message)
            except Exception:
                return raw

        lines = ["Here are some of the cheapest metros by current average rent:\n"]
        for _, row in df.iterrows():
            name = row["RegionName"]
            state_code = row.get("State", "") or ""
            current = row["Current_Rent"]
            lines.append(f"- {name} ({state_code}) — ~${current:,.0f} per month")

        if state:
            lines.append(f"\nThese are limited to metros in {state}.")

        raw = "\n".join(lines)
        try:
            return polish_response(raw, message)
        except Exception:
            return raw

    if _is_most_expensive_request(message):
        state = _parse_state(message)
        df = most_expensive_metros(limit=10, state=state)

        if df.empty:
            raw = "I couldn't find any metros in the dataset for that request."
            try:
                return polish_response(raw, message)
            except Exception:
                return raw

        lines = ["Here are some of the most expensive metros by current average rent:\n"]
        for _, row in df.iterrows():
            name = row["RegionName"]
            state_code = row.get("State", "") or ""
            current = row["Current_Rent"]
            lines.append(f"- {name} ({state_code}) — ~${current:,.0f} per month")

        if state:
            lines.append(f"\nThese are limited to metros in {state}.")

        raw = "\n".join(lines)
        try:
            #return polish_response(raw, message)
            print("DEBUG RAW REPLY:\n", raw)
            return raw
        except Exception:
            return raw

    # 4) Budget-based search (default path)
    budget = _parse_budget(message)
    state = _parse_state(message)

    if budget is None:
        # No budget specified: fall back to cheapest metros
        df = cheapest_metros(limit=10, state=state)
        if df.empty:
            raw = (
                "I couldn't find any metros in the dataset. "
                "Try asking about the cheapest metros or providing a rent budget."
            )
            try:
                #return polish_response(raw, message)
                print("DEBUG RAW REPLY:\n", raw)
                return raw
            except Exception:
                return raw

        lines = [
            "I didn't see a clear rent budget in your message, "
            "so here are some of the cheapest metros by current average rent:\n"
        ]
        for _, row in df.iterrows():
            name = row["RegionName"]
            state_code = row.get("State", "") or ""
            current = row["Current_Rent"]
            lines.append(f"- {name} ({state_code}) — ~${current:,.0f} per month")

        lines.append(
            "\nYou can also tell me your monthly rent budget (e.g. '$2500 in CA') "
            "and I'll filter down to metros under that amount."
        )

        raw = "\n".join(lines)
        try:
            #return polish_response(raw, message)
            print("DEBUG RAW REPLY:\n", raw)
            return raw
        except Exception:
            return raw

    # We have a budget → filter metros
    df = filter_by_budget(monthly_budget=budget, state=state)

    if df.empty:
        raw = (
            f"I couldn't find metros with average rent under about ${budget:,.0f} "
            "in this dataset. Try increasing your budget or omitting the state filter."
        )
        try:
            #return polish_response(raw, message)
            print("DEBUG RAW REPLY:\n", raw)
            return raw
        except Exception:
            return raw

    # Show top 10 matches
    df = df.head(10)

    if state:
        lines = [
            f"Here are some metros in {state} with average monthly rent roughly under your budget of ~${budget:,.0f}:\n"
        ]
    else:
        lines = [
            f"Here are some metros with average monthly rent roughly under your budget of ~${budget:,.0f}:\n"
        ]

    for _, row in df.iterrows():
        name = row["RegionName"]
        state_code = row.get("State", "") or ""
        current = row["Current_Rent"]
        trend = row.get("trend_label", "unknown")
        lines.append(
            f"- {name} ({state_code}) — ~${current:,.0f} per month, trend: {trend}"
        )

    lines.append(
        "\nYou can also ask about up-and-coming or declining markets, "
        "or ask me to compare two specific metros."
    )

    raw = "\n".join(lines)
    try:
        #return polish_response(raw, message)
        print("DEBUG RAW REPLY:\n", raw)
        return raw
    except Exception:
        return raw
