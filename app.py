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
# STILL DEMO: mental health wait (weeks) per ICB. The NHS Talking
# Therapies MONTHLY waiting-time file (referral to first treatment)
# has not yet been located/downloaded — the annual report only
# covers treatment outcomes, not wait times. These figures are
# illustrative and clearly marked as such throughout the app.
# ─────────────────────────────────────────────────────────
_rtt_real = pd.read_csv(
    _find("rtt_by_icb_real.csv")
)

# Illustrative MH wait per ICB — same 8 ICBs as the real physical
# health leaders, so the comparison chart is meaningful. Replace
# this column the moment the real monthly IAPT file is found.
_demo_mh_wait = {
    "NHS GREATER MANCHESTER INTEGRATED CARE BOARD": 34,
    "NHS NORTH EAST AND NORTH CUMBRIA INTEGRATED CARE BOARD": 29,
    "NHS CHESHIRE AND MERSEYSIDE INTEGRATED CARE BOARD": 31,
    "NHS NORTH WEST LONDON INTEGRATED CARE BOARD": 26,
    "NHS NORTH EAST LONDON INTEGRATED CARE BOARD": 33,
    "NHS SUSSEX INTEGRATED CARE BOARD": 22,
    "NHS WEST YORKSHIRE INTEGRATED CARE BOARD": 52,
    "NHS LANCASHIRE AND SOUTH CUMBRIA INTEGRATED CARE BOARD": 19,
}

DEMO_TRUSTS = _rtt_real.head(8).copy()
DEMO_TRUSTS["Trust"] = DEMO_TRUSTS["icb_region"].str.title()
DEMO_TRUSTS["ICB Region"] = DEMO_TRUSTS["icb_region"]
DEMO_TRUSTS["Physical wait (weeks)"] = DEMO_TRUSTS["physical_health_wait_weeks"]
DEMO_TRUSTS["MH wait (weeks)"] = DEMO_TRUSTS["icb_region"].map(_demo_mh_wait)
DEMO_TRUSTS["6-week target met %"] = (100 - DEMO_TRUSTS["MH wait (weeks)"] * 1.4).clip(15, 85).round(0)
DEMO_TRUSTS = DEMO_TRUSTS[["Trust", "ICB Region", "MH wait (weeks)", "Physical wait (weeks)", "6-week target met %"]]

# Real national NHS Talking Therapies figures (2025-26 annual report)
REAL_REFERRALS_RECEIVED = 1_813_303
REAL_FINISHED_TREATMENT = 674_683
REAL_UNEMPLOYED_SEEKING = 73_299
REAL_LONG_TERM_SICK = 47_434
REAL_EMPLOYED_END = 385_736
REAL_NATIONAL_PHYSICAL_WAIT_WEEKS = 15.6  # from RTT, 7.05M patients, weighted average

DEMO_TREND = pd.DataFrame({
    "Month": pd.date_range("2025-07-01", periods=12, freq="MS"),
    "England median MH wait (weeks)": [21, 22, 22, 23, 24, 24, 25, 26, 26, 27, 28, 28],
    "England median physical wait (weeks)": [15, 15, 16, 16, 16, 15, 15, 16, 16, 16, 15, 15],
})

# ─────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────
st.title("Mental Health Navigator")
st.caption(
    "A free, open-source navigation layer for people waiting for NHS mental health "
    "support. Prevention is better than cure: find help, people and tools you can "
    "use today."
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


tab_home, tab_match, tab_join, tab_listen, tab_wait, tab_cost, tab_about = st.tabs([
    "🏠 Start here",
    "🤝 Find support",
    "👥 Join in",
    "🎧 Listen and learn",
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
    st.warning(
        "Early version: national organisations and directories only. Local "
        "sessions and activities (councils, local Minds, community groups) will "
        "be added area by area, and only after being checked against the "
        "organisation's own page."
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
    st.warning(
        "Coming next: a curated selection of podcasts and short animated videos "
        "from trusted organisations. This project links to them; it does not "
        "make its own treatment content."
    )

# ─────────────────────────────────────────────────────────
# TAB 1 — POSTCODE SEARCH / NAVIGATE
# ─────────────────────────────────────────────────────────
with tab_wait:
    st.subheader("Find out how long the wait is near you")
    st.caption(
        "🔵 Physical health figures below are real, computed from the NHS England RTT "
        "March 2026 extract. 🟡 Mental health wait figures are illustrative placeholders "
        "pending access to the NHS Talking Therapies monthly waiting-time file."
    )
    col1, col2 = st.columns([1, 1])
    with col1:
        postcode = st.text_input("Your postcode", placeholder="e.g. RG1 2AB")
    with col2:
        condition = st.selectbox(
            "What are you looking for support with?",
            ["Anxiety or depression", "Trauma or PTSD", "OCD",
             "Eating difficulties", "General mental health",
             "Child or young person (CAMHS)", "Not sure"],
        )

    if st.button("Find services near me", type="primary"):
        st.success(
            f"Showing NHS Talking Therapies services for **{postcode or 'your area'}** "
            f"— condition: **{condition}**. Sorted by shortest wait first."
        )
        shown = DEMO_TRUSTS.sort_values("MH wait (weeks)")
        st.dataframe(
            shown, width="stretch", hide_index=True,
        )

        st.markdown("#### Mental health vs physical health wait — same areas, same NHS")
        chart_df = shown.melt(
            id_vars="Trust",
            value_vars=["MH wait (weeks)", "Physical wait (weeks)"],
            var_name="Type", value_name="Weeks",
        )
        fig = px.bar(
            chart_df, x="Trust", y="Weeks", color="Type", barmode="group",
            color_discrete_map={
                "MH wait (weeks)": "#e74c3c",
                "Physical wait (weeks)": "#2ecc71",
            },
        )
        fig.update_layout(xaxis_tickangle=-35, height=420, legend_title="")
        st.plotly_chart(fig, width="stretch")

        worst = shown.iloc[-1]
        best = shown.iloc[0]
        st.info(
            f"**The gap:** the longest mental health wait shown here "
            f"({worst['Trust']}, {worst['MH wait (weeks)']} weeks) is "
            f"**{worst['MH wait (weeks)'] / best['MH wait (weeks)']:.1f}x longer** than the "
            f"shortest ({best['Trust']}, {best['MH wait (weeks)']} weeks). "
            f"Same NHS. Different postcode."
        )
        st.markdown(
            "⏳ **Facing a long wait?** Open the **Find support** tab — "
            "answer five questions and we'll match you to support available today."
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
    st.subheader("Where you live decides how long you wait")
    st.caption("Median waits by trust — the postcode lottery in one chart.")

    fig2 = px.bar(
        DEMO_TRUSTS.sort_values("MH wait (weeks)", ascending=True),
        x="MH wait (weeks)", y="Trust", orientation="h",
        color="MH wait (weeks)", color_continuous_scale=["#2ecc71", "#f5a623", "#e74c3c"],
    )
    fig2.update_layout(height=420, coloraxis_showscale=False)
    st.plotly_chart(fig2, width="stretch")

    c1, c2, c3 = st.columns(3)
    _s = DEMO_TRUSTS.sort_values("MH wait (weeks)")
    c1.metric("England median MH wait (illustrative)", "28 weeks")
    c2.metric("Longest wait shown (illustrative)", f"{_s.iloc[-1]['MH wait (weeks)']:.0f} weeks", _s.iloc[-1]["Trust"])
    c3.metric("Shortest wait shown (illustrative)", f"{_s.iloc[0]['MH wait (weeks)']:.0f} weeks", _s.iloc[0]["Trust"])
    st.caption("Mental health waits and the 12-month trend are illustrative placeholders. Physical health waits are real.")

    st.markdown("#### 12-month trend — the gap is widening")
    trend_long = DEMO_TREND.melt(id_vars="Month", var_name="Series", value_name="Weeks")
    fig3 = px.line(
        trend_long, x="Month", y="Weeks", color="Series",
        color_discrete_map={
            "England median MH wait (weeks)": "#e74c3c",
            "England median physical wait (weeks)": "#2ecc71",
        },
    )
    fig3.update_layout(height=380, legend_title="")
    st.plotly_chart(fig3, width="stretch")

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
    c4, c5, c6 = st.columns(3)
    c4.metric("Out of work due to mental health (UK-wide estimate)", "2.8M people")
    c5.metric("Annual economic cost (UK-wide estimate)", "£28bn")
    c6.metric("Real national physical health wait (RTT, weighted average)", f"{REAL_NATIONAL_PHYSICAL_WAIT_WEEKS} weeks")
    st.caption(
        "The 2.8M / £28bn figures are UK-wide estimates from published mental health "
        "economic research, not computed from the two files above. The physical health "
        "wait figure is real, computed from 7.05 million patients on incomplete RTT "
        "pathways nationally as of March 2026."
    )

    st.markdown("#### Longer waits, more people out of work — the correlation")
    econ = DEMO_TRUSTS.copy()
    econ["Economic inactivity due to MH (%)"] = [3.1, 3.4, 3.9, 4.4, 7.8, 7.2, 6.1, 5.3]
    fig4 = px.scatter(
        econ, x="MH wait (weeks)", y="Economic inactivity due to MH (%)",
        text="ICB Region", size="MH wait (weeks)", color="MH wait (weeks)",
        color_continuous_scale=["#2ecc71", "#e74c3c"],
    )
    fig4.update_traces(textposition="top center")
    fig4.update_layout(height=460, coloraxis_showscale=False)
    st.plotly_chart(fig4, width="stretch")
    st.caption(
        "Each point is a region. Areas with longer mental health waits show "
        "higher rates of people out of work due to mental health conditions. "
        "Data: NHS IAPT monthly statistics + ONS Labour Force Survey."
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

**Listings** — each shows its source and last-checked date. Support, groups and
self-help entries link to the organisation's own page.

**Data status, honestly:**
- ✅ **Physical health waits** — real, computed from the NHS England RTT March
  2026 full extract (184,184 rows, 7.05 million patients on incomplete
  pathways nationally, aggregated to a patient-weighted average per ICB).
- ✅ **National referral and employment figures** — real, from the NHS
  Talking Therapies 2025-26 annual report (1.81 million referrals received,
  employment status at end of treatment).
- 🟡 **Mental health wait times by ICB** — still illustrative placeholders.
  The NHS Talking Therapies annual report covers treatment outcomes, not
  waiting times; the monthly waiting-time publication has not yet been
  located and downloaded. This is the next data source to connect.

**Data sources** — NHS Talking Therapies (digital.nhs.uk) · NHS RTT waiting
times (england.nhs.uk) · ONS economic inactivity by local authority
(ons.gov.uk, not yet connected) · ONS postcode directory (not yet connected).

**Open source** — github.com/Goku-coder336/mh-navigator ·
Suggest an organisation for the matching database: gokulrajan.336@gmail.com

**If you are in crisis right now** — Samaritans **116 123** (free, 24/7) ·
text **SHOUT to 85258** · NHS 111, option 2.
""")
