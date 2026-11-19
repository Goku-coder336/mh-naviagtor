"""
Mental Health Navigator
Free, open-source tool for people waiting for NHS mental health support in England.
Run with:  streamlit run app.py

Layout of the project
  app.py              this file: page layout and the simple tabs
  jarvis_ui.py        the screens inside the Jarvis tab
  jarvis_engine.py    the rules behind Jarvis (no Streamlit, fully tested)
  matching_engine.py  the five question matcher used by "Get support now"
  test_jarvis_engine.py   run with:  python -m unittest -v

Data rule: this app only shows numbers it can source. Where a number is not available
(mental health waiting times by area) it says so instead of estimating.
"""

import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jarvis_engine as je  # noqa: E402
import jarvis_ui  # noqa: E402
from matching_engine import load_organisations, match_organisations  # noqa: E402

st.set_page_config(page_title="Mental Health Navigator", page_icon="🧭", layout="wide")

GITHUB_URL = "https://github.com/Goku-coder336/mh-naviagtor"

# ---------------------------------------------------------------------------
# Styling: NHS colours, wrapping tabs on phones, card borders, readable text and a
# keyboard focus ring that is visible on any background. The selectors match the
# markup of current Streamlit (role="tab", stLayoutWrapper); the older data-baseweb and
# stVerticalBlockBorderWrapper selectors no longer exist, which is why they did nothing.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
html, body, [class*="css"], .stMarkdown, button, input { font-family: Arial, Helvetica, sans-serif !important; }
.block-container { max-width: 1100px; padding-top: 1.5rem; }
[role="tablist"] { flex-wrap: wrap !important; overflow: visible !important; height: auto !important; column-gap: 4px; border-bottom: 2px solid #D8DDE0; }
[role="tablist"]::after, .react-aria-SelectionIndicator, [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }
[role="tab"] { padding: 8px 12px !important; min-height: 44px; border-bottom: 4px solid transparent; color: #005EB8 !important; font-size: 1rem !important; font-weight: 700; }
[role="tab"][aria-selected="true"] { color: #003087 !important; border-bottom-color: #FFB81C !important; }
[data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] { border-left: 6px solid #005EB8 !important; border-radius: 4px; background: #FFFFFF; }
a { color: #005EB8; } a:hover { color: #7C2855; }
.stButton > button, .stLinkButton > a, [data-testid="stFormSubmitButton"] > button { background: #007F3B; color: #FFFFFF; border: 0; border-radius: 4px; font-weight: 700; }
.stButton > button:hover, .stLinkButton > a:hover, [data-testid="stFormSubmitButton"] > button:hover { background: #00662F; color: #FFFFFF; }
a:focus-visible, button:focus-visible, [role="tab"]:focus-visible, input:focus-visible, textarea:focus-visible, [tabindex]:focus-visible {
  outline: 3px solid #FFB81C !important; outline-offset: 0 !important; box-shadow: 0 0 0 6px #212B32 !important;
}
[data-testid="stCaptionContainer"] { opacity: 1 !important; color: #425563 !important; }
[data-testid="stCaptionContainer"] *, [data-testid="stMarkdownContainer"] p, [data-testid="stWidgetLabel"] * { font-size: 1rem !important; }
@media (max-width: 640px) { h1 { font-size: 1.8rem !important; } }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data (read once, then cached)
# ---------------------------------------------------------------------------
@st.cache_data
def get_orgs():
    return je.load_rows(je.find_data_file("organisations.csv"))


@st.cache_data
def get_resources():
    return je.load_rows(je.find_data_file("resources.csv"))


@st.cache_data
def get_rtt():
    """Real RTT (physical health) waits for the 42 ICBs, NHS England March 2026 extract."""
    frame = pd.DataFrame(je.load_rows(je.find_data_file("rtt_by_icb_real.csv")))
    frame["patients_waiting"] = frame["patients_waiting"].astype(int)
    frame["physical_health_wait_weeks"] = frame["physical_health_wait_weeks"].astype(float)
    frame["Area"] = frame["icb_region"].map(pretty_area)
    return frame


@st.cache_data
def get_matching_frame():
    return load_organisations(je.find_data_file("organisations.csv"))


def pretty_area(name: str) -> str:
    """'NHS SOUTH EAST LONDON INTEGRATED CARE BOARD' -> 'NHS South East London ICB'."""
    text = name.title().replace("Nhs", "NHS").replace("Integrated Care Board", "ICB")
    for small in (" And ", " Of ", " The "):
        text = text.replace(small, small.lower())
    return text


orgs, resources, rtt = get_orgs(), get_resources(), get_rtt()
rtt_rows = rtt.to_dict("records")
# Patient-weighted average, worked out from the file so it can never drift from the data.
national_wait = (rtt["physical_health_wait_weeks"] * rtt["patients_waiting"]).sum() / rtt["patients_waiting"].sum()
total_waiting = int(rtt["patients_waiting"].sum())

# Real national NHS Talking Therapies figures, 2025-26 annual report (digital.nhs.uk).
REAL_REFERRALS_RECEIVED = 1_813_303
REAL_FINISHED_TREATMENT = 674_683
REAL_UNEMPLOYED_SEEKING = 73_299
REAL_LONG_TERM_SICK = 47_434
REAL_EMPLOYED_END = 385_736

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("Mental Health Navigator")
st.caption("Free · Open source · Find out how long NHS waits are in your area, and get support while you wait.")
st.markdown(
    '<div style="background-color:#fff3cd;border-left:5px solid #ffc107;padding:10px 15px;border-radius:4px;'
    'margin-bottom:15px;color:#212B32;"><strong>In immediate distress or crisis?</strong> '
    "Call <strong>Samaritans 116 123</strong> (free, 24/7) · Text <strong>SHOUT to 85258</strong> · "
    "Call <strong>NHS 111, option 2</strong> for urgent NHS mental health help · "
    "In immediate danger call <strong>999</strong>.</div>",
    unsafe_allow_html=True,
)

tab_find, tab_jarvis, tab_lottery, tab_match, tab_cost, tab_about = st.tabs([
    "🔍 Find my wait time",
    "🤖 Jarvis Navigator",
    "🗺️ The postcode lottery",
    "🤝 Get support now",
    "📊 The economic cost",
    "ℹ️ About",
])

# ===========================================================================
# TAB 1: find my area and its waiting time
# ===========================================================================
with tab_find:
    st.subheader("Find your NHS area and how long people wait there")
    st.caption("Your postcode is sent to postcodes.io (a free service built on official ONS data) to find your NHS "
               "area. Nothing else is sent, and we do not save it.")
    with st.form("area_form"):
        postcode = st.text_input("Your postcode", placeholder="For example: SW1A 2AA")
        submitted = st.form_submit_button("Look up my area", type="primary")
    if submitted:
        st.session_state["area_lookup"] = je.lookup_icb(postcode)
    lookup = st.session_state.get("area_lookup")
    if lookup is not None and not lookup.ok:
        st.warning(jarvis_ui.lookup_message(lookup.reason) + " You can choose your area from the list instead.")
    chosen = st.selectbox("Or choose your area from the list", rtt["Area"].tolist(), index=None,
                          placeholder="Choose your area")
    area_name = chosen if chosen else (lookup.icb_name if lookup is not None and lookup.ok else None)

    if area_name:
        st.success(f"Your NHS area: **{area_name}**")
        row = je.find_icb_row(area_name, rtt_rows)
        if row:
            c1, c2 = st.columns(2)
            c1.metric("Average wait for physical health treatment", f"{float(row['physical_health_wait_weeks']):.1f} weeks")
            c2.metric("People waiting for that treatment", f"{int(row['patients_waiting']):,}")
            st.caption("Source: NHS England Referral to Treatment (RTT) data, March 2026, patient-weighted "
                       "average for the area. England average across these areas: "
                       f"{national_wait:.1f} weeks.")
        else:
            st.info("We hold waiting time data for the 42 areas as they were in March 2026. Your area does not "
                    "match one of them, possibly because areas have merged or been renamed since.")
        st.warning("**Mental health waiting times for your area are not shown here yet.** This tool is not yet "
                   "connected to the NHS Talking Therapies waiting time data, and we would rather show nothing than "
                   "guess. Ask your local service how long the wait is. You can refer yourself to NHS Talking "
                   "Therapies without seeing a GP.")
        st.markdown("[Find an NHS Talking Therapies service](" + je.CHOICE_LINKS[2][1] + ")")

    with st.expander("📋 Your rights while you wait, in plain English"):
        st.markdown(
            "- **Refer yourself.** For anxiety and depression you can refer yourself to NHS Talking Therapies. You do not "
            "need a GP referral.\n"
            "- **Choose where you go.** When a GP refers you, you usually have a legal right to choose where you go for a "
            "first outpatient appointment. You can ask to be moved to a different provider if you are likely to wait longer "
            "than the maximum waiting time. Some choices depend on what is available locally.\n"
            "- **Ask for an urgent review.** If you are getting worse while you wait, tell the service and your GP. It can "
            "change how quickly you are seen.\n"
            "- **In crisis right now.** Call **Samaritans 116 123** (free, 24/7), text **SHOUT to 85258**, or call "
            "**NHS 111 and choose option 2**.\n\n"
            "The **Jarvis Navigator** tab can write a letter to your GP that asks about these choices."
        )
        for label, url in je.CHOICE_LINKS[:2]:
            st.markdown(f"- [{label}]({url})")

# ===========================================================================
# TAB 2: Jarvis
# ===========================================================================
with tab_jarvis:
    jarvis_ui.render(orgs, resources)

# ===========================================================================
# TAB 3: how waits differ by area (real physical health data)
# ===========================================================================
with tab_lottery:
    st.subheader("Where you live changes how long you wait")
    st.caption("Physical health (RTT) waits by NHS area, March 2026. Mental health waits by area are not yet "
               "connected to this tool, so they are not shown.")
    ordered = rtt.sort_values("physical_health_wait_weeks")
    longest, shortest = ordered.iloc[-1], ordered.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("England average", f"{national_wait:.1f} weeks")
    c2.metric("Longest area", f"{longest['physical_health_wait_weeks']:.1f} weeks")
    c2.caption(longest["Area"])
    c3.metric("Shortest area", f"{shortest['physical_health_wait_weeks']:.1f} weeks")
    c3.caption(shortest["Area"])
    fig = px.bar(ordered, x="physical_health_wait_weeks", y="Area", orientation="h",
                 color="physical_health_wait_weeks", color_continuous_scale=["#2ecc71", "#f5a623", "#e74c3c"],
                 labels={"physical_health_wait_weeks": "Average wait (weeks)", "Area": ""})
    fig.update_layout(height=max(420, 24 * len(ordered)), coloraxis_showscale=False, font_size=14)
    # No width argument on purpose: the name of that argument differs between Streamlit versions, and the
    # wrong one makes Streamlit print a deprecation warning on the page for every visitor.
    st.plotly_chart(fig)

# ===========================================================================
# TAB 4: five question matcher
# ===========================================================================
with tab_match:
    st.subheader("You do not have to wait in silence")
    st.caption("Answer five quick questions and we will show up to three organisations that may suit you.")
    with st.form("match_form"):
        q1 = st.selectbox("1. What are you experiencing right now?", [
            "Anxiety or panic", "Low mood or depression", "Trauma or PTSD", "OCD or intrusive thoughts",
            "Grief or bereavement", "Relationship difficulties", "Eating difficulties", "I'm not sure"])
        q2 = st.selectbox("2. How old are you?", list(je.AGE_BANDS))
        q3 = st.selectbox("3. How quickly do you need support?",
                          ["Tonight or this week", "Within the next month", "A few weeks is fine"])
        q4 = st.selectbox("4. What can you afford?",
                          ["Free only", "Up to £20 per session", "Cost is not the main concern"])
        q5 = st.selectbox("5. How would you prefer to receive support?", [
            "Online or video", "Phone call", "Face to face", "Text or chat", "Something I can try on my own first"])
        go = st.form_submit_button("Show my matches", type="primary")
    if go:
        matches = match_organisations(get_matching_frame(), q1, q2, q3, q4, q5)
        if q3 == "Tonight or this week":
            st.error(je.crisis_message_markdown())
        if matches.empty:
            st.warning("No exact match found. Try widening the cost or format. "
                       "Hub of Hope (hubofhope.co.uk) lists local services by postcode.")
        for _, org in matches.iterrows():
            jarvis_ui.org_card(org.to_dict())
        free_help = [r for r in resources if r.get("section") == "listen"]
        if free_help and q3 != "Tonight or this week":
            st.markdown("##### Free self help from the NHS")
            for item in free_help:
                st.markdown(f"- [{item['name']}]({item['url']}): {item['description']}")

# ===========================================================================
# TAB 5: the economic cost (real figures only)
# ===========================================================================
with tab_cost:
    st.subheader("What the waiting list costs people and the country")
    st.success("The figures below come from the NHS Talking Therapies 2025-26 annual report and the NHS England "
               "RTT March 2026 extract.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Referrals received (England)", f"{REAL_REFERRALS_RECEIVED:,}")
    c2.metric("Unemployed and seeking work at end of treatment", f"{REAL_UNEMPLOYED_SEEKING:,}")
    c3.metric("Long term sick at end of treatment", f"{REAL_LONG_TERM_SICK:,}")
    st.caption(
        f"Of {REAL_REFERRALS_RECEIVED:,} people referred, {REAL_FINISHED_TREATMENT:,} finished a course of treatment. "
        f"At the end of treatment {REAL_EMPLOYED_END:,} were employed, {REAL_UNEMPLOYED_SEEKING:,} were unemployed and "
        f"seeking work, and {REAL_LONG_TERM_SICK:,} were recorded as long term sick. "
        "Source: NHS Talking Therapies 2025-26 annual report (digital.nhs.uk).")
    c4, c5 = st.columns(2)
    c4.metric("Average wait for physical health treatment", f"{national_wait:.1f} weeks")
    c5.metric("People waiting for that treatment", f"{total_waiting:,}")
    st.caption("Source: NHS England RTT March 2026 extract, across the 42 areas in our data file.")
    st.info("**What you will not find here:** a chart linking waiting times to people being out of work, or a figure "
            "for the total cost to the economy. We do not yet have sourced mental health waiting times by area, or a "
            "sourced cost figure, and we would rather leave them out than estimate. They will be added when we do.\n\n"
            "To see what time off could cost **you**, open the Jarvis Navigator tab and choose *What sick leave "
            "could cost me*.")

# ===========================================================================
# TAB 6: about
# ===========================================================================
with tab_about:
    st.subheader("About this tool")
    st.markdown(f"""
**Who built it.** Gokul, Data Analyst, Reading UK. MSc Financial Technology (Distinction, University of Kent).
Built because NHS mental health waiting data is published every month but is invisible to the people it affects most.

**This is not an NHS service.** It is an independent, free tool. It gives information, not medical advice.

### What the Jarvis Navigator does
It is a **rule-based guide**, not an AI chatbot. It reads your words for common topics and suggests services, scores the
PHQ-9 and GAD-7 questionnaires, writes letters from your own answers, and links to official pages about your choices,
work and money. It can get things wrong, so please check what it tells you. It does not save what you type.

### Data status, honestly
- ✅ **Physical health waits by NHS area:** real. NHS England RTT March 2026 extract, patient-weighted average per
  area ({total_waiting:,} people across the 42 areas in our file).
- ✅ **National referral and employment figures:** real. NHS Talking Therapies 2025-26 annual report.
- ✅ **Support organisations and resources:** each has a link to the organisation's own page and a date it was last
  checked.
- ⛔ **Mental health waiting times by area:** not connected yet. Nothing is shown rather than an estimate.
- ⛔ **Economic cost and out of work figures:** removed until a sourced figure is added.
- ⚠️ **Postcode lookup:** uses postcodes.io. Area names change as NHS areas merge, so a few postcodes may not match
  the March 2026 data.

**Data sources.** NHS Talking Therapies (digital.nhs.uk) · NHS RTT waiting times (england.nhs.uk) · ONS postcode data
via postcodes.io.

**Open source.** [{GITHUB_URL}]({GITHUB_URL}) · To suggest an organisation for the matching database:
gokulrajan.336@gmail.com

### If you are in crisis right now
**Samaritans 116 123** (free, 24/7) · text **SHOUT to 85258** · **NHS 111, option 2** · **999** if you are in immediate danger.
""")
