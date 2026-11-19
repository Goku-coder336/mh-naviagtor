"""
jarvis_engine.py
================
The logic behind the "Jarvis Navigator" tab.

Read this first:
* This is a RULE-BASED assistant. It matches words and applies fixed rules. It is not
  an AI model, it cannot diagnose, and it must never be described as clinical advice.
* There is no Streamlit code in this file, so every function can be unit tested
  (see test_jarvis_engine.py).
* Nothing a person types is stored, logged or printed here. The only network call is
  lookup_icb(), which sends one postcode to the open postcodes.io service.
* No figures are invented. Anything that comes from outside the app (the sick pay rate,
  waiting times) is either read from a data file or carries a source and a check date.
"""

from __future__ import annotations

import csv
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Dict, List, Optional, Sequence
from urllib.parse import quote

ASSISTANT_NAME = "Jarvis"

# ---------------------------------------------------------------------------
# Crisis contacts: one copy, used by the interface and by every letter.
# ---------------------------------------------------------------------------
CRISIS_CONTACTS = (
    ("Samaritans", "call 116 123 (free, 24/7)"),
    ("Shout", "text SHOUT to 85258 (free, 24/7)"),
    ("NHS 111", "call 111 and choose option 2 for urgent mental health help"),
    ("Emergency", "if you are in immediate danger call 999 or go to A&E"),
)


def crisis_message_markdown() -> str:
    """The text shown whenever someone may be in crisis."""
    lines = [
        "**It sounds like you may be going through something very hard right now. "
        "You do not have to cope with it alone.**",
        "",
    ]
    lines += [f"- **{name}:** {how}" for name, how in CRISIS_CONTACTS]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Text clean-up. Phones type curly apostrophes and special dashes, and a keyword
# list that does not allow for them quietly misses people (this was a real bug).
# ---------------------------------------------------------------------------
_DASHES = {ord(c): "-" for c in "‐‑‒–—―−"}
_QUOTES = {ord(c): "'" for c in "‘’‚‛′ʼ"}
_INVISIBLE = {ord(c): None for c in "​‌‍⁠﻿"}


def normalise(text: Optional[str]) -> str:
    """Lower-case, straighten quotes and dashes, remove invisible characters."""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.translate(_DASHES).translate(_QUOTES).translate(_INVISIBLE)
    return " ".join(text.lower().split())


# ---------------------------------------------------------------------------
# 1. Crisis detection
# ---------------------------------------------------------------------------
# Whole-word patterns only. The old list used plain substring matches, so "jump" fired
# on "jumpy" and "self harm" missed the normal spelling "self-harm".
# This is a safety NET, not a safety guarantee: it will miss some wording, and it
# will fire on some innocent sentences. That is deliberate (better to show help once
# too often). The interface also shows the crisis contacts permanently.
_CRISIS_PATTERNS = [
    r"\bsuicid(?:e|al)\b",
    r"\bkill(?:ing)?\s+my\s?self\b",
    r"\bend(?:ing)?\s+(?:my\s+(?:own\s+)?life|it\s+all)\b",
    r"\btak(?:e|ing)\s+my\s+(?:own\s+)?life\b",
    r"\bself[\s-]?(?:harm|injur)\w*",
    r"\b(?:hurt|harm|cut|injure)(?:ting|ing)?\s+my\s?self\b",
    r"\bwant(?:ed|ing)?\s+to\s+die\b",
    r"\bwanna\s+die\b",
    r"\bwish\s+(?:i|that\s+i)\s+(?:was|were)\s+(?:dead|never\s+born)\b",
    r"\bbetter\s+off\s+(?:dead|without\s+me)\b",
    r"\b(?:do\s*n'?t|do\s+not|no\s+longer|not)\s+want\s+to\s+(?:be\s+here|live|be\s+alive|exist|wake\s+up)\b",
    r"\bno\s+(?:point|reason)\s+(?:in\s+|to\s+)?(?:living|live|go(?:ing)?\s+on|being\s+alive)\b",
    r"\b(?:life\s+)?(?:is\s*n'?t|is\s+not|not)\s+worth\s+living\b",
    r"\bcan(?:'?t|not)\s+(?:go|carry)\s+on\b",
    r"\boverdos(?:e|ed|ing)\b",
    r"\bhang(?:ing)?\s+my\s?self\b",
    r"\bslit(?:ting)?\s+my\s+(?:wrists?|throat)\b",
    r"\bjump(?:ing)?\s+(?:off|in\s+front)\b",
]
_CRISIS_REGEXES = [re.compile(p) for p in _CRISIS_PATTERNS]


@dataclass(frozen=True)
class CrisisResult:
    is_crisis: bool
    matched: tuple = ()


def detect_crisis(text: Optional[str]) -> CrisisResult:
    clean = normalise(text)
    hits = tuple(m.group(0) for rx in _CRISIS_REGEXES for m in [rx.search(clean)] if m)
    return CrisisResult(bool(hits), hits)


# ---------------------------------------------------------------------------
# 2. Reading free text: topics and urgency
# ---------------------------------------------------------------------------
# Whole-word stems. The old code used substrings: "eat" matched "treatment" (so everyone
# waiting for treatment was sent to the eating disorder charity), and "now" matched
# "know" (so "I don't know where to turn" was treated as an emergency).
_TAG_PATTERNS = {
    "anxiety": [r"\banxi(?:ous|ety)\b", r"\bpanic\w*", r"\bworr(?:y|ied|ies|ying)\b", r"\bfears?\b",
                r"\boverthink\w*", r"\bheart\s+(?:racing|pounding)\b", r"\bon\s+edge\b"],
    "depression": [r"\bdepress\w*", r"\blow\s+mood\b", r"\bhopeless\w*", r"\bnumb\b", r"\bempty\b",
                   r"\bexhaust\w*", r"\bsad\b", r"\bno\s+motivation\b"],
    "trauma": [r"\btrauma\w*", r"\bptsd\b", r"\bflashbacks?\b", r"\bnightmares?\b", r"\babus(?:e|ed|ive)\b",
               r"\bassault\w*"],
    "ocd": [r"\bocd\b", r"\bobsess\w*", r"\bcompuls\w*", r"\bintrusive\s+thoughts?\b", r"\brituals?\b"],
    "grief": [r"\bgrie(?:f|ving|ve)\b", r"\bbereave\w*", r"\bfuneral\b", r"\bpassed\s+away\b",
              r"\bdeath\s+of\b", r"\blost\s+my\s+(?:mum|mom|dad|mother|father|husband|wife|partner|son|daughter|"
              r"brother|sister|friend|child|baby)\b"],
    "eating": [r"\beating\s+(?:disorder|problem|difficult\w*)\b", r"\bdisordered\s+eating\b", r"\banorex\w*",
               r"\bbulimi\w*", r"\bbing(?:e|eing)\b", r"\bpurg(?:e|ing)\b", r"\bbody\s+image\b",
               r"\bstopped\s+eating\b"],
    "relationships": [r"\bpartner\b", r"\bmarriage\b", r"\brelationship\w*", r"\bdivorc\w*",
                      r"\bbreak\s?up\b", r"\bseparat(?:ed|ion)\b"],
}
_TAG_REGEXES = {tag: [re.compile(p) for p in pats] for tag, pats in _TAG_PATTERNS.items()}

TAG_LABELS = {
    "anxiety": "Anxiety or panic",
    "depression": "Low mood or depression",
    "trauma": "Trauma or PTSD",
    "ocd": "OCD or intrusive thoughts",
    "grief": "Grief or bereavement",
    "eating": "Eating difficulties",
    "relationships": "Relationship difficulties",
    "general": "General emotional wellbeing",
}

_URGENT_NOW = [re.compile(p) for p in (r"\btonight\b", r"\bright\s+now\b", r"\bemergency\b",
                                        r"\bcan'?t\s+take\s+(?:it|this)\b")]
_URGENT_SOON = [re.compile(p) for p in (r"\btoday\b", r"\bthis\s+week\b", r"\burgent(?:ly)?\b",
                                         r"\bgetting\s+worse\b", r"\bdeteriorat\w*",
                                         r"\bstruggling\s+at\s+work\b")]


def detect_tags(text: Optional[str]) -> List[str]:
    clean = normalise(text)
    tags = [t for t, rxs in _TAG_REGEXES.items() if any(rx.search(clean) for rx in rxs)]
    return tags or ["general"]


def detect_urgency(text: Optional[str]) -> str:
    clean = normalise(text)
    if any(rx.search(clean) for rx in _URGENT_NOW):
        return "immediate"
    if any(rx.search(clean) for rx in _URGENT_SOON):
        return "elevated"
    return "standard"


# ---------------------------------------------------------------------------
# 3. Data files and organisation matching
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))


def find_data_file(name: str) -> str:
    """Data files may sit in data/ or next to the code."""
    for folder in (os.path.join(_HERE, "data"), _HERE):
        path = os.path.join(folder, name)
        if os.path.exists(path):
            return path
    return os.path.join(_HERE, name)


def load_rows(path: str) -> List[Dict[str, str]]:
    """Read a CSV into a list of dicts. Raises FileNotFoundError if it is missing."""
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


AGE_BANDS = ("Under 18", "18 to 25", "26 to 64", "65 and over")


def _cells(value: Optional[str]) -> List[str]:
    return [p.strip().lower() for p in re.split(r"[;,]", value or "") if p.strip()]


def _speed_rank(org: Dict[str, str]) -> int:
    try:
        return int(org.get("speed_rank", 3))
    except (TypeError, ValueError):
        return 3


def crisis_organisations(orgs: Sequence[Dict[str, str]], limit: int = 3) -> List[Dict[str, str]]:
    """The 24/7 services (Samaritans, Shout, NHS 111)."""
    found = [o for o in orgs if o.get("urgency_level") == "immediate"]
    return sorted(found, key=lambda o: (_speed_rank(o), o.get("name", "")))[:limit]


def rank_organisations(orgs: Sequence[Dict[str, str]], tags: Sequence[str], urgency: str = "standard",
                       age_band: Optional[str] = None, limit: int = 3) -> List[Dict[str, str]]:
    """
    Best matches first. An organisation must cover at least one of the topics (or be a
    'general' service); the rest only changes the order: topic match, speed of access,
    and whether the person said they need help now.
    """
    wanted = set(tags) or {"general"}
    scored = []
    for org in orgs:
        org_tags = _cells(org.get("condition_tags"))
        ages = _cells(org.get("age_group"))
        if age_band and "all ages" not in ages and age_band.lower() not in ages:
            continue
        overlap = [t for t in wanted if t in org_tags]
        topic_score = 5 * len(overlap) if overlap else (2 if "general" in org_tags else 0)
        if topic_score == 0:
            continue
        # A specialist for the topic (not a 'general' service) should beat a general directory on a tie.
        specialist_bonus = 3 if overlap and "general" not in org_tags else 0
        score = topic_score + specialist_bonus + (4 - _speed_rank(org)) * 2
        is_crisis_line = org.get("urgency_level") == "immediate"
        if is_crisis_line and urgency == "immediate":
            score += 20
        elif is_crisis_line:
            score -= 10  # crisis lines are not a long-term plan for someone who is not in crisis
        why = ("Covers: " + ", ".join(TAG_LABELS.get(t, t) for t in sorted(overlap))) if overlap \
            else "A general service that supports many kinds of difficulty"
        scored.append((-score, _speed_rank(org), org.get("name", ""), dict(org, _why=why)))
    scored.sort(key=lambda row: row[:3])
    return [row[3] for row in scored[:limit]]


@dataclass
class TriageResult:
    crisis: CrisisResult
    tags: List[str]
    urgency: str
    matches: List[Dict[str, str]] = field(default_factory=list)


def triage(text: str, orgs: Sequence[Dict[str, str]], age_band: Optional[str] = None) -> TriageResult:
    """Read someone's own words and suggest up to three services."""
    crisis = detect_crisis(text)
    if crisis.is_crisis:
        return TriageResult(crisis, ["crisis"], "immediate", crisis_organisations(orgs))
    tags, urgency = detect_tags(text), detect_urgency(text)
    return TriageResult(crisis, tags, urgency, rank_organisations(orgs, tags, urgency, age_band))


# ---------------------------------------------------------------------------
# 4. Screening questionnaires (PHQ-9 and GAD-7)
# ---------------------------------------------------------------------------
ANSWER_LABELS = ("Not at all", "Several days", "More than half the days", "Nearly every day")

PHQ9_QUESTIONS = (
    "Little interest or pleasure in doing things",
    "Feeling down, depressed or hopeless",
    "Trouble falling or staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself, or that you are a failure or have let yourself or your family down",
    "Trouble concentrating on things, such as reading the newspaper or watching television",
    "Moving or speaking so slowly that other people could have noticed, or the opposite: being so fidgety "
    "or restless that you have been moving around a lot more than usual",
    "Thoughts that you would be better off dead, or of hurting yourself in some way",
)
GAD7_QUESTIONS = (
    "Feeling nervous, anxious or on edge",
    "Not being able to stop or control worrying",
    "Worrying too much about different things",
    "Trouble relaxing",
    "Being so restless that it is hard to sit still",
    "Becoming easily annoyed or irritable",
    "Feeling afraid, as if something awful might happen",
)

# Published cut-offs: PHQ-9 0-4 / 5-9 / 10-14 / 15-19 / 20-27, GAD-7 0-4 / 5-9 / 10-14 / 15-21.
_PHQ9_BANDS = ((4, "Minimal"), (9, "Mild"), (14, "Moderate"), (19, "Moderately severe"), (27, "Severe"))
_GAD7_BANDS = ((4, "Minimal"), (9, "Mild"), (14, "Moderate"), (21, "Severe"))

SCREENING_DISCLAIMER = ("This is a screening questionnaire, not a diagnosis. Only a health professional can "
                        "assess how you are.")


@dataclass(frozen=True)
class ScreeningResult:
    score: int
    max_score: int
    severity: str
    guidance: str
    safety_flag: bool = False


def _check_answers(answers: Sequence[int], expected: int) -> List[int]:
    """Refuse missing, extra or out-of-range answers instead of quietly scoring them."""
    if answers is None or len(answers) != expected:
        raise ValueError(f"Expected {expected} answers, got {0 if answers is None else len(answers)}.")
    cleaned = []
    for a in answers:
        if isinstance(a, bool) or not isinstance(a, int) or not 0 <= a <= 3:
            raise ValueError(f"Each answer must be a whole number from 0 to 3, got {a!r}.")
        cleaned.append(a)
    return cleaned


def _band(score: int, bands) -> str:
    return next(label for limit, label in bands if score <= limit)


def _guidance(severity: str) -> str:
    if severity == "Minimal":
        base = "Your answers suggest few symptoms at the moment. If you are still worried about how you feel, speak to your GP."
    elif severity == "Mild":
        base = ("Your answers suggest mild symptoms. Self-help can be a good start, and you can speak to your GP "
                "or refer yourself to NHS Talking Therapies if things do not improve.")
    elif severity == "Moderate":
        base = ("Your answers suggest it is worth speaking to your GP, or referring yourself to NHS Talking "
                "Therapies. You can do this while you wait for other support.")
    else:
        base = ("Your answers suggest you are having a hard time. Please arrange to speak to your GP soon, and "
                "use the crisis contacts if you ever feel unsafe.")
    return f"{base} {SCREENING_DISCLAIMER}"


def score_phq9(answers: Sequence[int]) -> ScreeningResult:
    vals = _check_answers(answers, 9)
    total = sum(vals)
    severity = _band(total, _PHQ9_BANDS)
    # Any answer above 'Not at all' to item 9 should prompt a safety message.
    return ScreeningResult(total, 27, severity, _guidance(severity), safety_flag=vals[8] > 0)


def score_gad7(answers: Sequence[int]) -> ScreeningResult:
    vals = _check_answers(answers, 7)
    total = sum(vals)
    severity = _band(total, _GAD7_BANDS)
    return ScreeningResult(total, 21, severity, _guidance(severity))


# ---------------------------------------------------------------------------
# 5. Postcode -> NHS area (Integrated Care Board)
# ---------------------------------------------------------------------------
# The old code guessed the area from the first letters of the postcode. That is wrong in
# many places (for example Hounslow, Lambeth and Hackney all landed in the wrong London
# area) and it silently defaulted to a Berkshire area for any postcode it did not know,
# including typos and postcodes outside England. We now ask the official-data service
# postcodes.io (built on ONS open data) and say so plainly when we cannot find an answer.
_OUTWARD = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?$")
_INWARD = re.compile(r"^\d[A-Z]{2}$")


def normalise_postcode(raw: Optional[str]) -> Optional[str]:
    """'rg1  2ab' -> 'RG1 2AB'. Returns None if it is not shaped like a UK postcode."""
    cleaned = re.sub(r"\s+", "", (raw or "").upper())
    if len(cleaned) < 5 or len(cleaned) > 7:
        return None
    outward, inward = cleaned[:-3], cleaned[-3:]
    if _OUTWARD.match(outward) and _INWARD.match(inward):
        return f"{outward} {inward}"
    return None


@dataclass(frozen=True)
class PostcodeLookup:
    ok: bool
    postcode: Optional[str] = None
    reason: str = ""          # invalid, not_found, not_england, no_icb, unavailable
    icb_name: Optional[str] = None
    district: Optional[str] = None


def lookup_icb(raw_postcode: str, http_get: Optional[Callable] = None, timeout: float = 5.0) -> PostcodeLookup:
    """Find the NHS area for a postcode. Never raises: failures come back as ok=False."""
    postcode = normalise_postcode(raw_postcode)
    if postcode is None:
        return PostcodeLookup(False, None, "invalid")
    if http_get is None:
        import requests  # imported here so the rest of the engine works without it
        http_get = requests.get
    try:
        response = http_get(f"https://api.postcodes.io/postcodes/{quote(postcode)}", timeout=timeout)
        if response.status_code == 404:
            return PostcodeLookup(False, postcode, "not_found")
        if response.status_code != 200:
            return PostcodeLookup(False, postcode, "unavailable")
        result = (response.json() or {}).get("result") or {}
    except Exception:  # network down, timeout, bad JSON: all mean "could not look it up"
        return PostcodeLookup(False, postcode, "unavailable")
    if result.get("country") and result["country"] != "England":
        return PostcodeLookup(False, postcode, "not_england")
    if not result.get("icb"):
        return PostcodeLookup(False, postcode, "no_icb")
    return PostcodeLookup(True, postcode, "", result["icb"], result.get("admin_district"))


def _icb_key(name: str) -> str:
    name = (name or "").upper().replace("&", " AND ")
    name = re.sub(r"\bINTEGRATED CARE BOARD\b|\bICB\b|\bNHS\b", " ", name)
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", name).split())


def find_icb_row(icb_name: Optional[str], rtt_rows: Sequence[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Match an ICB name to a row of rtt_by_icb_real.csv, or None (never a guess)."""
    key = _icb_key(icb_name or "")
    if not key:
        return None
    return next((r for r in rtt_rows if _icb_key(r.get("icb_region", "")) == key), None)


# ---------------------------------------------------------------------------
# 6. Letters. Plain text (they are pasted into emails and surgery forms), written only
#    from what the person tells us. No statistics, no legal claims beyond the NHS's own
#    published wording, and no developer name in the patient's letter.
# ---------------------------------------------------------------------------
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def clean_text(value: Optional[str], max_len: int = 300) -> str:
    value = _CONTROL.sub("", value or "")
    return " ".join(value.split())[:max_len]


def _today(today: Optional[date]) -> str:
    return (today or date.today()).strftime("%d %B %Y")


def _scores_sentence(phq9: Optional[int], gad7: Optional[int]) -> str:
    parts = []
    if phq9 is not None:
        parts.append(f"PHQ-9 (low mood) {phq9} out of 27")
    if gad7 is not None:
        parts.append(f"GAD-7 (anxiety) {gad7} out of 21")
    if not parts:
        return ""
    return ("I completed two online screening questionnaires. My scores were " + " and ".join(parts) +
            ". I understand these are not a diagnosis.")


def gp_letter(patient_name: str, gp_surgery: str, condition: str, weeks_waiting: int, impact: str,
              preferred_provider: str = "", phq9: Optional[int] = None, gad7: Optional[int] = None,
              today: Optional[date] = None) -> str:
    name = clean_text(patient_name, 80) or "[your name]"
    surgery = clean_text(gp_surgery, 120) or "My GP practice"
    condition = clean_text(condition, 120) or "my mental health"
    impact = clean_text(impact, 300)
    provider = clean_text(preferred_provider, 120)
    weeks = max(int(weeks_waiting or 0), 0)
    lines = [
        f"Date: {_today(today)}",
        f"To: {surgery}",
        f"From: {name}",
        "Subject: Support while I wait for NHS mental health care, and my choices",
        "",
        "Dear Doctor,",
        "",
        f"I am writing about my mental health. I am struggling with {condition} and I have been waiting "
        f"about {weeks} weeks for NHS support.",
    ]
    if impact:
        lines += [f"This is affecting my daily life: {impact}"]
    scores = _scores_sentence(phq9, gad7)
    if scores:
        lines += ["", scores]
    lines += [
        "",
        "I would be grateful if you could:",
        "1. Review whether my referral should be prioritised, because the wait is affecting my life.",
        "2. Tell me what support is available while I wait, and who to contact if things get worse.",
        "3. Explain my choices. I understand the NHS Choice Framework gives patients legal rights to choose "
        "where to go for a first outpatient appointment when a GP refers them, and to ask to be moved to a "
        "different provider if they are likely to wait longer than the maximum waiting time. Please tell me "
        "whether either right applies to my situation.",
    ]
    if provider:
        lines += [f"4. I would like to be considered for referral to {provider}, if that is appropriate."]
    lines += ["", "Thank you for your help.", "", "Yours sincerely,", name]
    return "\n".join(lines)


def mp_letter(constituent_name: str, postcode: str, mp_name: str, weeks_waiting: int, condition: str,
              icb_name: Optional[str] = None, today: Optional[date] = None) -> str:
    name = clean_text(constituent_name, 80) or "[your name]"
    mp = clean_text(mp_name, 80)
    condition = clean_text(condition, 120) or "my mental health"
    weeks = max(int(weeks_waiting or 0), 0)
    pc = normalise_postcode(postcode) or clean_text(postcode, 10).upper() or "[your postcode]"
    area = f" ({clean_text(icb_name, 120)})" if icb_name else ""
    return "\n".join([
        f"Date: {_today(today)}",
        f"To: {mp or 'My Member of Parliament'}, House of Commons, London SW1A 0AA",
        f"From: {name}, {pc}",
        "Subject: Long waits for NHS mental health support in my area",
        "",
        f"Dear {mp or 'Member of Parliament'},",
        "",
        f"I am one of your constituents. I have been waiting about {weeks} weeks for NHS support for {condition}.",
        "",
        "I would be grateful if you would:",
        f"1. Ask our Integrated Care Board{area} for the current waiting times for NHS Talking Therapies and "
        "other mental health services in our area, and what is being done to shorten them.",
        "2. Ask the Department of Health and Social Care how mental health is being given equal priority with "
        "physical health ('parity of esteem').",
        "3. Tell me what help your office can offer to people who are waiting.",
        "",
        "Thank you for your time.",
        "",
        "Yours sincerely,",
        name,
    ])


def sbar_briefing(patient_name: str, symptoms: str, duration: str, impact: str, request: str,
                  phq9: Optional[int] = None, gad7: Optional[int] = None,
                  phq9_item9: Optional[int] = None) -> str:
    """A short structured summary for a GP. It reports only what the patient entered."""
    name = clean_text(patient_name, 80) or "The patient"
    symptoms = clean_text(symptoms, 200) or "not stated"
    request = clean_text(request, 200) or "not stated"
    scores = _scores_sentence(phq9, gad7) or "No questionnaire scores recorded."
    if phq9_item9 is None:
        risk = "Not assessed by this tool. Please ask me about risk."
    elif phq9_item9 > 0:
        risk = (f"On the PHQ-9 I answered '{ANSWER_LABELS[phq9_item9]}' to the question about thoughts of being "
                "better off dead or of hurting myself. Please ask me about this.")
    else:
        risk = ("On the PHQ-9 I answered 'Not at all' to the question about thoughts of being better off dead "
                "or of hurting myself.")
    return "\n".join([
        "2-MINUTE GP BRIEFING (SBAR). Written by the patient from their own answers.",
        "",
        f"S (Situation): {name} is struggling with {symptoms}.",
        f"B (Background): symptoms have lasted {clean_text(duration, 60) or 'not stated'}. "
        f"Effect on work or daily life: {clean_text(impact, 300) or 'not stated'}.",
        f"A (Assessment, my own view): {scores} Risk: {risk}",
        f"R (Request): {request}.",
    ])


# ---------------------------------------------------------------------------
# 7. Money: what sick leave can cost. Plain arithmetic on the person's own numbers.
# ---------------------------------------------------------------------------
# Source: GOV.UK, https://www.gov.uk/statutory-sick-pay/what-youll-get, checked 18 November 2026:
# "£123.25 a week Statutory Sick Pay or 80% of your normal weekly earnings, whichever is lower.
# It's paid for up to 28 weeks." These change each April: re-check them every year.
SSP_WEEKLY_RATE = 123.25
SSP_EARNINGS_SHARE = 0.80
SSP_MAX_WEEKS = 28
SSP_SOURCE_URL = "https://www.gov.uk/statutory-sick-pay/what-youll-get"
SSP_CHECKED = "18 November 2026"

INCOME_SCENARIOS = {
    "ssp": "Off sick, on Statutory Sick Pay only",
    "reduced_hours": "Working fewer hours",
    "left_job": "Had to leave my job",
}


@dataclass(frozen=True)
class IncomeImpact:
    weekly_gross: float
    total_lost: float
    notes: tuple


def estimate_income_impact(annual_salary: float, scenario: str, weeks: int,
                           reduced_hours_pct: float = 0.0) -> IncomeImpact:
    if scenario not in INCOME_SCENARIOS:
        raise ValueError(f"Unknown scenario {scenario!r}.")
    if not 0 <= annual_salary <= 1_000_000:
        raise ValueError("Salary must be between 0 and 1,000,000.")
    if not 0 <= weeks <= 260:
        raise ValueError("Weeks must be between 0 and 260.")
    if not 0 <= reduced_hours_pct <= 100:
        raise ValueError("Hours reduction must be between 0 and 100 per cent.")
    weekly = annual_salary / 52
    if scenario == "ssp":
        ssp_weeks = min(weeks, SSP_MAX_WEEKS)
        paid_per_week = min(SSP_WEEKLY_RATE, SSP_EARNINGS_SHARE * weekly)
        lost = ssp_weeks * (weekly - paid_per_week) + max(weeks - SSP_MAX_WEEKS, 0) * weekly
        notes = (
            f"Uses the statutory minimum only: £{SSP_WEEKLY_RATE:.2f} a week or 80% of weekly earnings, "
            f"whichever is lower, for up to {SSP_MAX_WEEKS} weeks (GOV.UK, checked {SSP_CHECKED}).",
            "Your employer may pay more than this. Check your contract.",
            "After 28 weeks Statutory Sick Pay stops. Other support, such as Universal Credit, may be available.",
        )
    elif scenario == "reduced_hours":
        lost = weeks * weekly * reduced_hours_pct / 100
        notes = ("Assumes your pay falls in proportion to your hours.",)
    else:
        lost = weeks * weekly
        notes = ("Shows pay you would normally receive, before any benefits you may be able to claim.",)
    return IncomeImpact(round(weekly, 2), round(lost, 2),
                        notes + ("All figures are gross (before tax) and are estimates, not advice.",))


# ---------------------------------------------------------------------------
# 8. Static guidance. Wording is deliberately cautious and every item links to the
#    official page. No pound amounts or legal absolutes are repeated here, because they
#    go out of date (the old text quoted an Access to Work cap and sick pay rate that
#    had both changed).
# ---------------------------------------------------------------------------
CHOICE_LINKS = (
    ("NHS England: your legal rights to choice", "https://www.england.nhs.uk/personalisedcare/choice/"),
    ("NHS: your choices in the NHS", "https://www.nhs.uk/using-the-nhs/about-the-nhs/your-choices-in-the-nhs/"),
    ("NHS: find an NHS Talking Therapies service (you can refer yourself)",
     "https://www.nhs.uk/service-search/mental-health/find-an-nhs-talking-therapies-service/"),
)

# Providers whose own pages describe NHS Right to Choose referrals. Checked 18 November 2026.
# Note what they offer: autism and ADHD assessments. Right to Choose is NOT a way around a long
# wait for talking therapy, which you can self-refer to directly.
RIGHT_TO_CHOOSE_PROVIDERS = (
    {"name": "Psychiatry-UK", "url": "https://psychiatry-uk.com/right-to-choose/",
     "says": "NHS-funded ADHD assessments online, with a GP referral in England."},
    {"name": "ProblemShared", "url": "https://www.problemshared.net/right-to-choose",
     "says": "NHS-funded online autism and ADHD assessments and post-diagnostic support, through Right to Choose."},
    {"name": "Clinical Partners",
     "url": "https://www.clinical-partners.co.uk/nhs-right-to-choose-assessments-and-medication/",
     "says": "NHS Right to Choose assessments for autism and ADHD, and an ADHD medication service."},
)
RIGHT_TO_CHOOSE_CHECKED = "18 November 2026"

WORKPLACE_GUIDE = (
    {"title": "Access to Work",
     "text": "A government scheme that can help pay for support at work if you have a health condition or "
             "disability, including a mental health condition. Check who can apply and what help is available.",
     "links": (("GOV.UK: Access to Work", "https://www.gov.uk/access-to-work"),)},
    {"title": "Reasonable adjustments at work",
     "text": "A mental health condition can count as a disability under the Equality Act 2010 if it has a "
             "substantial and long-term effect on your day-to-day life. If it does, your employer has a duty to "
             "consider reasonable adjustments. Whether yours counts depends on your circumstances.",
     "links": (("GOV.UK: definition of disability", "https://www.gov.uk/definition-of-disability-under-equality-act-2010"),
               ("Acas: reasonable adjustments", "https://www.acas.org.uk/reasonable-adjustments"),
               ("GOV.UK: your rights as a disabled person", "https://www.gov.uk/rights-disabled-person"))},
    {"title": "Sick pay",
     "text": "Statutory Sick Pay may be paid by your employer if you are eligible. The rate changes each April, "
             "so check the current figure. Some employers pay more than the minimum.",
     "links": (("GOV.UK: Statutory Sick Pay", "https://www.gov.uk/statutory-sick-pay"),
               ("GOV.UK: sick pay for employers and employees", "https://www.gov.uk/employers-sick-pay"))},
    {"title": "Benefits that may help",
     "text": "Depending on your situation you may be able to claim Universal Credit or Personal Independence "
             "Payment. Use the official pages to check, and consider talking to an adviser.",
     "links": (("GOV.UK: Universal Credit", "https://www.gov.uk/universal-credit"),
               ("GOV.UK: Personal Independence Payment", "https://www.gov.uk/pip"))},
)

COPING_TOOLKIT = (
    {"title": "Breathing exercise",
     "text": "Slow, steady breathing can help when you feel tense or panicky. The NHS has a step-by-step guide.",
     "link": ("NHS: breathing exercises for stress",
              "https://www.nhs.uk/mental-health/self-help/guides-tools-and-activities/breathing-exercises-for-stress/")},
    {"title": "Grounding: 5-4-3-2-1",
     "text": "Look around and name 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell and 1 "
             "you can taste. It gives your mind something steady to focus on."},
    {"title": "A set time for worry",
     "text": "Pick a short slot each day for worries. If one appears earlier, jot it down and come back to it then."},
    {"title": "Small daily habits",
     "text": "The NHS five steps to mental wellbeing are a simple place to start.",
     "link": ("NHS: 5 steps to mental wellbeing",
              "https://www.nhs.uk/mental-health/self-help/guides-tools-and-activities/five-steps-to-mental-wellbeing/")},
)

DETERIORATION_FLAGS = (
    "Not sleeping for several nights in a row.",
    "Not being able to eat or look after yourself.",
    "Thoughts of harming yourself, ending your life, or that others would be better off without you.",
    "Panic attacks that are getting more frequent or more severe.",
    "Pulling away from work, family and friends.",
)
DETERIORATION_ADVICE = ("If any of these apply, do not wait for your appointment. Contact your GP surgery and "
                        "ask for an urgent review, call NHS 111 and choose option 2, or use the crisis contacts above.")
