"""
NHS Mental Health & Economic Inactivity Navigator
Free, open-source patient-facing platform.
Built by Gokul — github.com/Goku-coder336/mh-navigator
Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matching_engine import load_organisations, match_organisations

def _find(name):
    """Find a data file whether it sits in data/ or next to app.py."""
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(here, "data", name), os.path.join(here, name)):
        if os.path.exists(p):
            return p
    return os.path.join(here, "data", name)


st.set_page_config(
    page_title="NHS Mental Health Navigator",
    page_icon="🧭",
    layout="wide",
)

# ─────────────────────────────────────────────────────────
# DATA SOURCES — mixed status, honestly labelled:
#
# REAL: physical health wait (weeks) per ICB, computed from the
# actual NHS England RTT March 2026 full extract (184,184 rows,
# 7.05M patients on incomplete pathways nationally). Aggregated
# to a patient-weighted average wait per ICB from the raw weekly
# bands. Source: england.nhs.uk RTT waiting times statistics.
#
# REAL: national NHS Talking Therapies employment/referral figures
# (referrals received, finished treatment, employment status at
# end of treatment) from the NHS Talking Therapies 2025-26 annual
# report. Source: digital.nhs.uk.
#
# NOT YET CONNECTED: mental health waiting times by ICB. The app says
# so and shows no estimate. Only real data is displayed anywhere.
# ─────────────────────────────────────────────────────────
_rtt_real = pd.read_csv(
    _find("rtt_by_icb_real.csv")
)

# Real national NHS Talking Therapies figures (2025-26 annual report)
REAL_REFERRALS_RECEIVED = 1_813_303
REAL_FINISHED_TREATMENT = 674_683
REAL_UNEMPLOYED_SEEKING = 73_299
REAL_LONG_TERM_SICK = 47_434
REAL_EMPLOYED_END = 385_736
REAL_NATIONAL_PHYSICAL_WAIT_WEEKS = 15.6  # from RTT, 7.05M patients, weighted average

# ─────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────

st.markdown("""
<style>
html, body, [class*="css"], .stMarkdown, button, input { font-family: Arial, Helvetica, sans-serif !important; }
.block-container { max-width: 1100px; padding-top: 1.5rem; }
h1 { color: #FFFFFF !important; background: #005EB8; margin: 0 !important; padding: 28px 28px 8px 28px !important; border-radius: 8px 8px 0 0; font-weight: 700 !important; }
.nhs-sub { background: #005EB8; color: #FFFFFF; padding: 0 28px 24px 28px; border-radius: 0 0 8px 8px; font-size: 1.1rem; line-height: 1.5; margin-bottom: 16px; }

/* Tabs. This Streamlit version renders role="tablist" and role="tab" (no data-baseweb
   attributes), so the old .stTabs [data-baseweb] selectors matched nothing. Tabs wrap
   onto extra rows instead of scrolling sideways, and Streamlit's own selection bar is
   hidden (newer versions use .react-aria-SelectionIndicator, 1.50 uses data-baseweb
   tab-highlight and tab-border) so the NHS yellow underline is the only indicator. */
[role="tablist"] { flex-wrap: wrap !important; overflow: visible !important; height: auto !important; column-gap: 4px; border-bottom: 2px solid #D8DDE0; }
[role="tablist"]::after, .react-aria-SelectionIndicator, [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }
[role="tab"] { padding: 8px 12px !important; min-height: 44px; border-bottom: 4px solid transparent; color: #005EB8 !important; font-size: 1rem !important; font-weight: 700; }
[role="tab"][aria-selected="true"] { color: #003087 !important; border-bottom-color: #FFB81C !important; }

/* Cards. st.container(border=True) now renders as stLayoutWrapper > stVerticalBlock;
   the old stVerticalBlockBorderWrapper test id no longer exists. */
[data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] { border-left: 6px solid #005EB8 !important; border-radius: 4px; background: #FFFFFF; }

a { color: #005EB8; } a:hover { color: #7C2855; }
.stButton > button, .stLinkButton > a { background: #007F3B; color: #FFFFFF; border: 0; border-radius: 4px; font-weight: 700; }
.stButton > button:hover, .stLinkButton > a:hover { background: #00662F; color: #FFFFFF; }

/* Keyboard focus (WCAG 2.4.7 and 1.4.11). A yellow ring inside a dark ring is visible
   on both light and dark backgrounds; yellow alone is only 1.7:1 on white. */
a:focus-visible, button:focus-visible, [role="tab"]:focus-visible, input:focus-visible, textarea:focus-visible, [tabindex]:focus-visible {
  outline: 3px solid #FFB81C !important; outline-offset: 0 !important; box-shadow: 0 0 0 6px #212B32 !important;
}

/* Text: nothing below 16px, and captions at full opacity in an NHS secondary text colour (7.75:1 on white). */
[data-testid="stCaptionContainer"] { opacity: 1 !important; color: #425563 !important; }
[data-testid="stCaptionContainer"] *, [data-testid="stMarkdownContainer"] p, .tag { font-size: 1rem !important; }
.tag { display: inline-block; background: #E8EDEE; color: #212B32; border-radius: 4px; padding: 2px 8px; margin-right: 6px; }

/* Phones */
@media (max-width: 640px) {
  h1 { font-size: 2rem !important; padding: 20px 16px 8px 16px !important; }
  .nhs-sub { padding: 0 16px 20px 16px; }
}
</style>
""", unsafe_allow_html=True)
st.title("Mental Health Navigator")
st.markdown(
    '<div class="nhs-sub">A free, open-source plan for people waiting for NHS mental health support. '
    'Find help, people and tools you can use today.</div>',
    unsafe_allow_html=True,
)
st.error(
    "**In crisis right now?** Call **Samaritans 116 123** (free, 24/7) · "
    "text **SHOUT to 85258** · call **NHS 111, option 2** · in immediate danger, call **999**."
)

_resources = pd.read_csv(_find("resources.csv"))


def show_resources(section):
    """Render curated resources for a section, each with its source and check date."""
    for _, r in _resources[_resources["section"] == section].iterrows():
        with st.container(border=True):
            st.markdown(f"### [{r['name']}]({r['url']})")
            st.markdown(r["description"])
            st.caption(
                f"{r['cost']} · {r['format']} · For: {r['who_for']}  \n"
                f"Source: {r['source']} · Last checked: {r['last_checked']}"
            )


tab_home, tab_match, tab_join, tab_listen, tab_prog, tab_media, tab_wait, tab_cost, tab_about = st.tabs([
    "🏠 Start here",
    "🤝 Find support",
    "👥 Join in",
    "🎧 Listen and learn",
    "📚 Programmes",
    "🎙️ Podcasts and video",
    "⏳ Waiting times",
    "📊 The cost",
    "ℹ️ About",
])

# ─────────────────────────────────────────────────────────
# START HERE
# ─────────────────────────────────────────────────────────
with tab_home:
    st.subheader("Where are you right now?")
    st.caption(
        "You do not have to wait for one service to act. Here are several routes "
        "you can use at the same time. This tool signposts; it does not give "
        "medical advice or treatment."
    )
    h1, h2, h3 = st.columns(3)
    with h1:
        with st.container(border=True):
            st.markdown("#### I need help now")
            st.markdown(
                "**Samaritans** 116 123  \n**Shout** text SHOUT to 85258  \n"
                "**NHS 111**, option 2  \n**999** if in immediate danger"
            )
    with h2:
        with st.container(border=True):
            st.markdown("#### I am waiting for NHS support")
            st.markdown(
                "Open **Find support** and answer five questions. You get a "
                "short waiting plan you can save. Then check **Waiting times** "
                "for your rights while you wait."
            )
    with h3:
        with st.container(border=True):
            st.markdown("#### I want to feel better before things get worse")
            st.markdown(
                "Try **Join in** for peer support and local organisations, and "
                "**Listen and learn** for free audio guides and self-help from "
                "trusted sources."
            )
    st.info(
        "Every listing shows who runs it, where the information came from and "
        "when it was last checked. No accounts. No personal data is collected."
    )

# ─────────────────────────────────────────────────────────
# JOIN IN
# ─────────────────────────────────────────────────────────
with tab_join:
    st.subheader("You do not have to do this alone")
    st.caption(
        "Groups, peer support and local organisations run by established "
        "charities. Each links to the organisation's own page."
    )
    show_resources("join")
    st.markdown("#### Local: Berkshire West (Reading, West Berkshire, Wokingham)")
    st.caption("Pilot area. Each entry is taken from the organisation's or council's own page.")
    show_resources("local")
    st.warning(
        "Early version. Local listings so far cover Berkshire West only, and "
        "more local sessions and activities will be added area by area, only "
        "after being checked against the organisation's own page."
    )

# ─────────────────────────────────────────────────────────
# LISTEN AND LEARN
# ─────────────────────────────────────────────────────────
with tab_listen:
    st.subheader("Things you can do today, on your own")
    st.caption(
        "Free self-help from trusted sources. This is support while you wait, "
        "not treatment. If things get worse, contact your GP or a crisis line."
    )
    show_resources("listen")
    st.info("Looking for structured programmes, podcasts or video? See the **Programmes** and **Podcasts and video** tabs.")

# ─────────────────────────────────────────────────────────
# PROGRAMMES, PODCASTS AND VIDEO (every link is to the organisation's own page)
# ─────────────────────────────────────────────────────────
PROGRAMMES = [
    ("NHS Talking Therapies", "https://www.nhs.uk/tests-and-treatments/talking-therapies/",
     "Free, confidential talking treatments for anxiety and depression. You can refer yourself without seeing a GP.",
     "NHS", "Treatment"),
    ("Every Mind Matters", "https://www.nhs.uk/every-mind-matters/",
     "Expert advice, practical tips and a personalised action plan for stress, anxiety, low mood and sleep.",
     "NHS", "Self help plan"),
    ("Mental wellbeing audio guides", "https://www.nhs.uk/mental-health/self-help/guides-tools-and-activities/mental-wellbeing-audio-guides/",
     "Short audio guides on topics such as sleep problems and unhelpful thinking.",
     "NHS", "Audio"),
    ("Berkshire Talking Therapies", "https://www.berkshirehealthcare.nhs.uk/talking-therapies",
     "The local NHS Talking Therapies service for Berkshire, run by Berkshire Healthcare NHS Foundation Trust.",
     "Berkshire Healthcare", "Local"),
]
PODCASTS = [
    ("Mind podcasts: your stories", "https://www.mind.org.uk/information-support/podcasts/",
     "A series in which people talk about what it is like to live with mental health problems.", "Mind"),
    ("The Rethink Mental Illness podcast", "https://www.rethink.org/news-and-stories/podcasts/",
     "Conversations with people living with mental illness and people working in mental health.", "Rethink Mental Illness"),
    ("Mental Health Foundation podcasts", "https://www.mentalhealth.org.uk/explore-mental-health/podcasts",
     "Podcasts from the home of Mental Health Awareness Week.", "Mental Health Foundation"),
]
CHECKED = "6 Nov 2026"


def link_card(name, url, desc, org, tag=None):
    with st.container(border=True):
        st.markdown(f"### [{name}]({url})")
        st.markdown(desc)
        chips = f'<span class="tag">{org}</span>' + (f'<span class="tag">{tag}</span>' if tag else "")
        st.markdown(chips, unsafe_allow_html=True)
        st.caption(f"Opens the organisation's own page · Last checked: {CHECKED}")


with tab_prog:
    st.subheader("Programmes you can start now")
    st.caption("Run by the NHS. You can use these while you wait. They support you; they do not replace a clinician.")
    c1, c2 = st.columns(2)
    for k, (n, u, d, o, t) in enumerate(PROGRAMMES):
        with (c1 if k % 2 == 0 else c2):
            link_card(n, u, d, o, t)

with tab_media:
    st.subheader("Mental health awareness: watch and listen")
    st.caption("Explainers and podcasts from trusted organisations. This project links to them and makes no treatment content of its own.")
    st.markdown("#### Video: how NHS Talking Therapies work")
    vcol, tcol = st.columns([3, 2])
    with vcol:
        st.video("https://www.youtube.com/watch?v=jLgv0E1k6hs")
        st.caption("NHS, via YouTube. Treatment for depression and anxiety | NHS Talking Therapies.")
    with tcol:
        with st.container(border=True):
            st.markdown("**More video**")
            st.markdown("- [Every Mind Matters on YouTube](https://www.youtube.com/channel/UCNG4k3ZA2rjaupAeDBO-t1Q/videos)")
            st.markdown("- [Mind, the mental health charity, on YouTube](https://www.youtube.com/channel/UCarWBJYMNqJxgn6n8_htCTQ)")
        with st.container(border=True):
            st.markdown("**Animated explainer for this project**")
            st.caption("Not made yet. A short animated explainer about mental health awareness can be added here once it is made and reviewed.")
    st.markdown("#### Podcasts")
    for n, u, d, o in PODCASTS:
        link_card(n, u, d, o, "Podcast")

# ─────────────────────────────────────────────────────────
# TAB 1 — POSTCODE SEARCH / NAVIGATE
# ─────────────────────────────────────────────────────────
with tab_wait:
    st.subheader("Find out how long the wait is in your area")
    st.caption(
        "🔵 Physical health waits are real, computed from the NHS England RTT "
        "March 2026 extract for all 42 integrated care boards (ICBs). "
        "🟡 Mental health waits by area are not yet connected, so none are shown "
        "as fact. Enter a postcode, or pick your area from the list."
    )
    _icbs = _rtt_real.copy()
    _icbs["Area"] = (
        _icbs["icb_region"].str.replace("NHS ", "", n=1, regex=False)
        .str.replace(" INTEGRATED CARE BOARD", "", regex=False).str.title()
    )
    _names = sorted(_icbs["Area"])
    _bob = next((i for i, n in enumerate(_names) if "Berkshire" in n), 0)
    _default = 0

    # Postcode lookup (postcodes.io, free public service). It gives the local
    # authority. Automatic matching to an NHS area is built for the pilot area
    # only (Berkshire West, Oxfordshire, Buckinghamshire); elsewhere the
    # person confirms their area in the box below.
    _PILOT_LAS = {
        "Reading", "West Berkshire", "Wokingham", "Oxford", "Cherwell",
        "South Oxfordshire", "Vale of White Horse", "West Oxfordshire",
        "Buckinghamshire",
    }

    @st.cache_data(ttl=3600, show_spinner=False)
    def _lookup(pc):
        import requests
        try:
            r = requests.get(
                "https://api.postcodes.io/postcodes/" + pc.replace(" ", ""), timeout=6
            )
            if r.status_code == 200:
                d = r.json()["result"]
                return {"ok": True, "la": d.get("admin_district"), "country": d.get("country")}
            if r.status_code == 404:
                return {"ok": False, "reason": "notfound"}
        except Exception:
            pass
        return {"ok": False, "reason": "unavailable"}

    postcode = st.text_input("Your postcode (optional)", placeholder="e.g. RG1 7TN")
    if postcode.strip():
        res = _lookup(postcode.strip())
        if res["ok"] and res["country"] != "England":
            st.warning("Waiting-time data here covers NHS England only. Scotland, Wales and Northern Ireland run their own health services and are planned for later. The national organisations in Join in and Listen and learn, and the crisis lines above, work across the UK.")
        elif res["ok"] and res["la"] in _PILOT_LAS:
            _default = _bob
            st.success(f"{postcode.upper()} is in {res['la']}. Showing your NHS area below.")
        elif res["ok"]:
            st.info(
                f"{postcode.upper()} is in {res['la']}. Automatic matching to an NHS "
                "area is only built for Berkshire West, Oxfordshire and "
                "Buckinghamshire so far. Please choose your area below."
            )
        elif res["reason"] == "notfound":
            st.warning("That postcode was not recognised. Check it, or choose your area below.")
        else:
            st.info("Postcode lookup is unavailable right now. Please choose your area below.")

    area = st.selectbox("Your NHS area (ICB)", _names, index=_default)
    row = _icbs[_icbs["Area"] == area].iloc[0]
    _rank = int(_icbs["physical_health_wait_weeks"].rank(ascending=False, method="min")[row.name])
    m1, m2, m3 = st.columns(3)
    m1.metric("Physical health wait (real)", f"{row['physical_health_wait_weeks']:.1f} weeks",
              f"{row['physical_health_wait_weeks'] - REAL_NATIONAL_PHYSICAL_WAIT_WEEKS:+.1f} vs England",
              delta_color="inverse")
    m2.metric("People waiting (real)", f"{int(row['patients_waiting']):,}")
    m3.metric("Mental health wait", "Not yet available")
    st.caption(
        f"{area} ranks {_rank} of {len(_icbs)} areas for longest physical health "
        f"waits (1 = longest). Source: NHS England RTT, March 2026."
    )
    st.info(
        "⏳ **Waiting for mental health support?** Open **Find support** and answer "
        "five questions to get a waiting plan."
    )

    with st.expander("All 42 areas, real physical health waits"):
        st.dataframe(
            _icbs[["Area", "physical_health_wait_weeks", "patients_waiting"]]
            .rename(columns={"physical_health_wait_weeks": "Physical wait (weeks)",
                             "patients_waiting": "People waiting"})
            .sort_values("Physical wait (weeks)", ascending=False),
            width="stretch", hide_index=True,
        )

    with st.expander("📋 Your rights while you wait — plain English"):
        st.markdown("""
- **Self-refer to NHS Talking Therapies** — you do not need a GP referral for
  anxiety and depression. You can refer yourself today via the NHS website or NHS App.
- **Right to Choose** — for many services you have a legal right to choose a
  different provider with a shorter wait, including in a neighbouring area.
  Ask your GP to refer you to the provider you choose.
- **Ask for an urgent review** — if your condition deteriorates while waiting,
  contact the service and your GP. Deterioration can change your priority.
- **In crisis right now** — call **Samaritans 116 123** (free, 24/7) or text
  **SHOUT to 85258**. Call **NHS 111 and select option 2** for the urgent
  mental health team.
""")

# ─────────────────────────────────────────────────────────
# TAB 2 — INEQUALITY / TREND
# ─────────────────────────────────────────────────────────
with tab_wait:
    st.divider()
    st.subheader("Where you live affects how long you wait")
    st.caption(
        "Real physical health waits by NHS area (NHS England RTT, March 2026). "
        "Mental health waits by area are not connected yet."
    )
    _w = _icbs.sort_values("physical_health_wait_weeks", ascending=False)
    _top = pd.concat([_w.head(8), _w.tail(8)])
    fig2 = px.bar(
        _top.sort_values("physical_health_wait_weeks"),
        x="physical_health_wait_weeks", y="Area", orientation="h",
        color="physical_health_wait_weeks",
        color_continuous_scale=["#2ecc71", "#f5a623", "#e74c3c"],
        labels={"physical_health_wait_weeks": "Weeks (patient-weighted average)"},
    )
    fig2.update_layout(height=520, coloraxis_showscale=False)
    st.plotly_chart(fig2, width="stretch")

    c1, c2, c3 = st.columns(3)
    c1.metric("England average", f"{REAL_NATIONAL_PHYSICAL_WAIT_WEEKS} weeks")
    c2.metric("Longest area", f"{_w.iloc[0]['physical_health_wait_weeks']:.1f} weeks", _w.iloc[0]["Area"])
    c3.metric("Shortest area", f"{_w.iloc[-1]['physical_health_wait_weeks']:.1f} weeks", _w.iloc[-1]["Area"])
    st.caption(
        "Shown: the 8 longest and 8 shortest of 42 areas. The full list is above. "
        "These are physical health waits, used to show how much waits vary by area. "
        "Mental health waits by area will be added when the monthly NHS Talking "
        "Therapies data is connected."
    )

# ─────────────────────────────────────────────────────────
# TAB 3 — MATCHING ENGINE
# ─────────────────────────────────────────────────────────
with tab_match:
    st.subheader("You don't have to wait in silence")
    st.caption(
        "Tell us a little about your situation and we'll show you the two or "
        "three organisations best matched to you — not a list of twenty."
    )

    q1 = st.selectbox("1 · What are you experiencing right now?", [
        "Anxiety or panic", "Low mood or depression", "Trauma or PTSD",
        "OCD or intrusive thoughts", "Grief or bereavement",
        "Relationship difficulties", "Eating difficulties", "I'm not sure",
    ])
    q2 = st.selectbox("2 · How old are you?", [
        "Under 18", "18 to 25", "26 to 64", "65 and over",
    ])
    q3 = st.selectbox("3 · How quickly do you need support?", [
        "Tonight or this week", "Within the next month", "A few weeks is fine",
    ])
    q4 = st.selectbox("4 · What can you afford?", [
        "Free only", "Up to £20 per session", "Cost is not the main concern",
    ])
    q5 = st.selectbox("5 · How would you prefer to receive support?", [
        "Online or video", "Phone call", "Face to face", "Text or chat",
        "Something I can try on my own first",
    ])

    if st.button("Show my matches", type="primary"):
        df_orgs = load_organisations(
            _find("organisations.csv")
        )
        matches = match_organisations(df_orgs, q1, q2, q3, q4, q5)

        if q3 == "Tonight or this week":
            st.error(
                "**You said you need support now — these services answer "
                "immediately, day or night.**"
            )

        if matches.empty:
            st.warning(
                "No exact match found — try widening cost or format. "
                "Hub of Hope (hubofhope.co.uk) lists every local service by postcode."
            )
        for _, org in matches.iterrows():
            with st.container(border=True):
                st.markdown(f"### [{org['name']}]({org['url']})")
                st.markdown(org["description"])
                st.markdown(f"**Why this suits you:** {org['why_suits']}")
                cost_label = "Free" if org["cost_category"] == "free" else f"Up to £{org['cost_max']}/session"
                st.caption(
                    f"{cost_label} · {org['format_tags'].replace(',', ' · ')} · "
                    f"Approach: {org['approach']}  \n"
                    f"Last checked: {org['verified_date']}"
                )

        # ── My waiting plan ──
        st.markdown("---")
        st.subheader("My waiting plan")
        first = matches.iloc[0] if not matches.empty else None
        plan = ["MY WAITING PLAN", ""]
        if first is not None:
            plan.append(f"1. Contact: {first['name']} - {first['url']}")
        plan += [
            "2. Join in: find your local Mind - https://www.mind.org.uk/information-support/local-minds/",
            "   or a Rethink support group - https://www.rethink.org/help-in-your-area/support-groups/",
            "3. Listen: NHS mental wellbeing audio guides - https://www.nhs.uk/mental-health/self-help/guides-tools-and-activities/mental-wellbeing-audio-guides/",
            "4. If things get worse: Samaritans 116 123, text SHOUT to 85258, NHS 111 option 2, 999 in an emergency.",
            "",
            "This plan signposts services. It is not medical advice.",
        ]
        plan_text = "\n".join(plan)
        with st.container(border=True):
            st.text(plan_text)
        st.download_button(
            "Save my plan (text file)", plan_text, file_name="my-waiting-plan.txt",
            on_click="ignore",
        )

# ─────────────────────────────────────────────────────────
# TAB 4 — ECONOMIC LAYER
# ─────────────────────────────────────────────────────────
with tab_cost:
    st.subheader("What the waiting list costs the country")

    st.success(
        "✅ **The figures below are real** — pulled directly from the NHS Talking "
        "Therapies 2025-26 annual report and the NHS England RTT March 2026 extract."
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Referrals received (national)", f"{REAL_REFERRALS_RECEIVED:,}")
    c2.metric("Unemployed & seeking work at end of treatment", f"{REAL_UNEMPLOYED_SEEKING:,}")
    c3.metric("Long-term sick at end of treatment", f"{REAL_LONG_TERM_SICK:,}")

    st.caption(
        f"Of {REAL_REFERRALS_RECEIVED:,} people referred, {REAL_FINISHED_TREATMENT:,} "
        f"finished a course of treatment. At the end of treatment, {REAL_EMPLOYED_END:,} "
        f"were employed — but {REAL_UNEMPLOYED_SEEKING:,} were still unemployed and "
        f"seeking work, and {REAL_LONG_TERM_SICK:,} were recorded as long-term sick. "
        f"Source: NHS Talking Therapies 2025-26 annual report, employment status at end "
        f"of treatment."
    )

    st.markdown("#### National context")
    st.metric("Physical health wait, England (RTT, weighted average)", f"{REAL_NATIONAL_PHYSICAL_WAIT_WEEKS} weeks")
    st.caption(
        "Computed from 7.05 million patients on incomplete RTT pathways nationally "
        "as of March 2026. Links between waits and economic inactivity by area are "
        "not shown, because that analysis needs mental health wait data by area and "
        "ONS economic inactivity data, neither of which is connected yet."
    )

# ─────────────────────────────────────────────────────────
# TAB 5 — ABOUT
# ─────────────────────────────────────────────────────────
with tab_about:
    st.subheader("About this tool")
    st.markdown("""
**What it is** — a free navigation layer for people waiting for NHS mental
health support. It connects people to help that already exists and is easy to
miss: NHS routes, charity support, peer groups and trusted self-help. It does
not give medical advice or treatment.

**Who built it** — Gokul Rajan, Reading UK. MSc Financial Technology
(Distinction, University of Kent). Product design and data. Prototyped with AI
coding tools. Not yet reviewed for clinical safety or accessibility.

**How this fits alongside the NHS App** — the NHS App is the national route
into NHS services, and government plans say it could offer self-referral to
talking therapies and mental health advice. This tool does not replace any of
that. It is for the time between asking for help and getting it: a short plan
that puts crisis help first, then the NHS route, then trusted charity, peer and
self-help options near you. Where the NHS App offers something, this tool
points to it. It does not copy or compete with it.

**Coverage** — waiting-time data covers NHS England (all 42 integrated care boards). Scotland, Wales and Northern Ireland have separate health services and are planned for later. Crisis lines and national charities listed work UK-wide.

**Listings** — each shows its source and last-checked date. Support, groups and
self-help entries link to the organisation's own page.

**Data status, honestly:**
- ✅ **Physical health waits** — real, computed from the NHS England RTT March
  2026 full extract (184,184 rows, 7.05 million patients on incomplete
  pathways nationally, aggregated to a patient-weighted average per ICB).
- ✅ **National referral and employment figures** — real, from the NHS
  Talking Therapies 2025-26 annual report (1.81 million referrals received,
  employment status at end of treatment).
- 🟡 **Mental health wait times by ICB** — not yet connected, so the app
  shows "Not yet available" and no estimates. The NHS Talking Therapies
  annual report covers treatment outcomes, not waiting times. The monthly
  waiting-time publication is the next data source to connect.

**Data sources** — NHS Talking Therapies (digital.nhs.uk) · NHS RTT waiting
times (england.nhs.uk) · ONS economic inactivity by local authority
(ons.gov.uk, not yet connected) · ONS postcode directory (not yet connected).

**Open source** — github.com/Goku-coder336/mh-navigator ·
Suggest an organisation for the matching database: gokulrajan.336@gmail.com

**If you are in crisis right now** — Samaritans **116 123** (free, 24/7) ·
text **SHOUT to 85258** · NHS 111, option 2.
""")
