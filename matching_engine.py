"""
Matching engine for the NHS Mental Health Navigator.
Takes five answers about a person's situation and returns
the top 3 most suitable support organisations.
"""

import pandas as pd


def load_organisations(path="data/organisations.csv"):
    """Load the curated organisation database."""
    return pd.read_csv(path)


def match_organisations(df, condition, age, urgency, cost, format_pref):
    """
    Filter the organisation database down to the top 3 matches.

    Rules:
    1. Crisis fast-track: urgency 'Tonight or this week' returns
       immediate services (Samaritans, Shout, NHS 111) before anything else.
    2. Otherwise filter by condition, age, cost and format in order.
    3. Sort fastest-access first. Return a maximum of 3 results.
    """

    # ── CRISIS FAST-TRACK ────────────────────────────────
    if urgency == "Tonight or this week":
        crisis = df[df["urgency_level"] == "immediate"]
        return crisis.head(3)

    results = df[df["urgency_level"] != "immediate"].copy()

    # ── CONDITION ────────────────────────────────────────
    condition_map = {
        "Anxiety or panic": "anxiety",
        "Low mood or depression": "depression",
        "Trauma or PTSD": "trauma",
        "OCD or intrusive thoughts": "ocd",
        "Grief or bereavement": "grief",
        "Relationship difficulties": "relationships",
        "Eating difficulties": "eating",
        "I'm not sure": "general",
    }
    tag = condition_map.get(condition, "general")
    results = results[results["condition_tags"].str.contains(tag, na=False)]

    # ── AGE ──────────────────────────────────────────────
    age_map = {
        "Under 18": "under 18",
        "18 to 25": "18 to 25",
        "26 to 64": "26 to 64",
        "65 and over": "65 and over",
    }
    age_tag = age_map.get(age, "")
    if age_tag:
        results = results[
            results["age_group"].str.contains(age_tag, na=False)
            | (results["age_group"] == "all ages")
        ]

    # ── COST ─────────────────────────────────────────────
    if cost == "Free only":
        results = results[results["cost_category"] == "free"]
    elif cost == "Up to £20 per session":
        results = results[results["cost_max"] <= 20]

    # ── FORMAT ───────────────────────────────────────────
    format_map = {
        "Online or video": "online",
        "Phone call": "phone",
        "Face to face": "in-person",
        "Text or chat": "text",
        "Something I can try on my own first": "online",
    }
    fmt = format_map.get(format_pref, "online")
    results = results[results["format_tags"].str.contains(fmt, na=False)]

    # ── SORT AND RETURN TOP 3 ────────────────────────────
    results = results.sort_values("speed_rank")
    return results.head(3)
