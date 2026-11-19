"""
jarvis_ui.py
============
The Streamlit screens for the Jarvis Navigator tab. All the thinking happens in
jarvis_engine.py; this file only draws forms and results.

Rules this file follows:
* Radio questions start with NOTHING selected, so a skipped question is never scored as zero.
* Questionnaire scores are only used in a letter if the person ticks the box.
* The postcode is only sent to postcodes.io if the person ticks the box.
* Nothing the person types is saved anywhere except this browser session.
"""

from __future__ import annotations

import hashlib
import re
from typing import Dict, Sequence

import streamlit as st

import jarvis_engine as je

MODES = {
    "triage": "💬 Describe how you feel: suggests services",
    "screening": "🩺 Questionnaires: PHQ-9 and GAD-7",
    "programme": "🎧 Free things to try while you wait",
    "toolkit": "🛡️ While you wait: coping toolkit",
    "rights": "⚖️ Your choices: self-referral and Right to Choose",
    "gp_letter": "✉️ Letter to my GP",
    "sbar": "📋 2 minute briefing for my GP",
    "work": "💼 Work and money guide",
    "calculator": "🧮 What sick leave could cost me",
    "mp_letter": "🏛️ Letter to my MP",
}

TOPIC_OPTIONS = [t for t in je.TAG_LABELS if t != "general"]


# ---------------------------------------------------------------------------
# Small shared pieces
# ---------------------------------------------------------------------------
def _crisis_banner() -> None:
    st.error(
        "**Need to talk to someone right now?** "
        + " · ".join(f"**{name}:** {how}" for name, how in je.CRISIS_CONTACTS)
    )


def _filename(name: str, stem: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name or "").strip("_")
    return f"{stem}_{safe}.txt" if safe else f"{stem}.txt"


def org_card(org: Dict[str, str]) -> None:
    with st.container(border=True):
        st.markdown(f"### [{org['name']}]({org['url']})")
        st.markdown(org["description"])
        if org.get("why_suits"):
            st.markdown(f"**Why this may suit you:** {org['why_suits']}")
        cost = "Free" if org.get("cost_category") == "free" else f"Low cost, up to £{org.get('cost_max', '')} a session"
        how = str(org.get("format_tags") or "").replace(",", " · ")
        checked = f"Checked: {org['verified_date']}" if org.get("verified_date") else ""
        st.caption(" · ".join(part for part in (cost, how, org.get("_why", ""), checked) if part))


def resource_card(row: Dict[str, str]) -> None:
    with st.container(border=True):
        st.markdown(f"### [{row['name']}]({row['url']})")
        st.markdown(row["description"])
        st.caption(f"{row['cost']} · {row['format']} · For: {row['who_for']} · "
                   f"Source: {row['source']} · Checked: {row['last_checked']}")


def _save_letter(kind: str, title: str, text: str, filename: str) -> None:
    """Streamlit re-runs the whole page on every click, so keep the letter in the session."""
    st.session_state[f"jarvis_letter_{kind}"] = (title, text, filename)


def _show_saved_letter(kind: str) -> None:
    saved = st.session_state.get(f"jarvis_letter_{kind}")
    if not saved:
        return
    title, text, filename = saved
    st.markdown(f"### {title}")
    st.info("Read it through and change anything that is not true for you before you send it.")
    # The key includes a fingerprint of the text, so a new letter never inherits edits made to an old one.
    fingerprint = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    st.text_area("Your letter (you can edit it here)", value=text, height=420, key=f"box_{kind}_{fingerprint}")
    st.download_button("📥 Download as a text file", data=text, file_name=filename, mime="text/plain",
                       key=f"dl_{kind}_{fingerprint}")


def _score_choice() -> tuple:
    """Call INSIDE a form. Returns (phq9, gad7) to include, or (None, None) unless the person opts in."""
    phq9, gad7 = st.session_state.get("jarvis_phq9"), st.session_state.get("jarvis_gad7")
    if phq9 is None and gad7 is None:
        return None, None
    include = st.checkbox("Include my questionnaire scores in this letter", value=False,
                          help="Your scores are only kept for this visit. Tick this to put them in the letter.")
    return (phq9, gad7) if include else (None, None)


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------
def _triage(orgs: Sequence[Dict[str, str]]) -> None:
    st.markdown("#### Tell me what is going on, in your own words")
    st.caption("This reads your words for common topics and suggests services. It is a simple word matcher, "
               "so please check the topics it picks and change them if it gets it wrong.")
    with st.form("triage_form"):
        text = st.text_area("What has been happening?", height=130, max_chars=1500,
                            placeholder="For example: I have had panic attacks at work and I am not sleeping.")
        age = st.selectbox("Your age (optional)", ["Prefer not to say", *je.AGE_BANDS])
        submitted = st.form_submit_button("Suggest services", type="primary")
    if submitted:
        st.session_state["jarvis_triage"] = (text, None if age == "Prefer not to say" else age)
    saved = st.session_state.get("jarvis_triage")
    if not saved:
        return
    text, age_band = saved
    if not text.strip():
        st.warning("Please write a few words first.")
        return

    result = je.triage(text, orgs, age_band)
    if result.crisis.is_crisis:
        st.error(je.crisis_message_markdown())
        st.markdown("##### Support that is open now")
        for org in result.matches:
            org_card(org)
        return

    key = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    topics = st.multiselect(
        "Topics I picked up (change these if I got it wrong)", TOPIC_OPTIONS,
        default=[t for t in result.tags if t in TOPIC_OPTIONS], format_func=je.TAG_LABELS.get,
        key=f"triage_topics_{key}")
    urgency = result.urgency
    if urgency == "immediate":
        st.warning("You said you need help soon. These services are open day and night:")
        for org in je.crisis_organisations(orgs):
            org_card(org)
        st.markdown("##### Other services that may help")
    elif urgency == "elevated":
        st.info("You said things are getting harder. If that changes, use the crisis contacts above, "
                "and ask your GP for an urgent review.")
    ranked = je.rank_organisations(orgs, topics or ["general"], "standard", age_band, limit=6)
    matches = [o for o in ranked if o.get("urgency_level") != "immediate"][:3]  # crisis lines are shown above
    if not matches:
        st.warning("I could not find a close match. Hub of Hope (hubofhope.co.uk) lists local services by postcode.")
    for org in matches:
        org_card(org)


def _screening() -> None:
    st.markdown("#### Two short questionnaires used by the NHS")
    st.caption("The PHQ-9 and GAD-7 are the questionnaires GPs and NHS Talking Therapies use to see how low mood "
               "and anxiety are affecting you. " + je.SCREENING_DISCLAIMER)
    which = st.radio("Which questionnaire?", ["PHQ-9: low mood", "GAD-7: anxiety"], horizontal=True)
    is_phq = which.startswith("PHQ")
    questions = je.PHQ9_QUESTIONS if is_phq else je.GAD7_QUESTIONS
    prefix = "phq" if is_phq else "gad"
    with st.form(f"form_{prefix}"):
        st.markdown("**Over the last 2 weeks, how often have you been bothered by the following?**")
        answers = [
            st.radio(f"{i}. {q}", options=[0, 1, 2, 3], index=None, horizontal=True,
                     format_func=lambda v: je.ANSWER_LABELS[v], key=f"{prefix}_{i}")
            for i, q in enumerate(questions, start=1)
        ]
        submitted = st.form_submit_button("Score my answers", type="primary")
    if not submitted:
        return
    if any(a is None for a in answers):
        missing = [str(i) for i, a in enumerate(answers, start=1) if a is None]
        st.error("Please answer every question so the score is accurate. Still to answer: " + ", ".join(missing) + ".")
        return
    result = je.score_phq9(answers) if is_phq else je.score_gad7(answers)
    st.session_state["jarvis_phq9" if is_phq else "jarvis_gad7"] = result.score
    if is_phq:
        st.session_state["jarvis_phq9_item9"] = answers[8]
    st.metric("Your score", f"{result.score} out of {result.max_score}")
    st.markdown(f"**Level: {result.severity}**")
    if result.safety_flag:
        st.error("You said you have had thoughts of being better off dead or of hurting yourself. "
                 "Please talk to someone today.\n\n" + je.crisis_message_markdown())
    st.info(result.guidance)
    st.caption("Your score is kept only for this visit, so you can choose to add it to a letter. "
               "Questionnaire source: PHQ-9 and GAD-7, developed by Drs Spitzer, Williams and Kroenke.")


def _programme(orgs, resources) -> None:
    st.markdown("#### Free things to try while you wait")
    st.caption("Services, NHS self-help and people to connect with. Every link goes to the organisation's own page.")
    topic = st.selectbox("What would you like support with?", ["Not sure", *TOPIC_OPTIONS],
                         format_func=lambda t: t if t == "Not sure" else je.TAG_LABELS[t])
    tags = ["general"] if topic == "Not sure" else [topic]
    st.markdown("##### Services that match")
    for org in je.rank_organisations(orgs, tags, "standard", limit=3):
        org_card(org)
    for heading, section in (("Free self help from the NHS", "listen"), ("People to connect with", "join")):
        rows = [r for r in resources if r.get("section") == section]
        if rows:
            st.markdown(f"##### {heading}")
            for row in rows:
                resource_card(row)


def _toolkit() -> None:
    st.markdown("#### While you wait: a coping toolkit")
    st.caption("Simple things many people find helpful. They are not a treatment and do not replace support from "
               "a professional.")
    for tool in je.COPING_TOOLKIT:
        with st.container(border=True):
            st.markdown(f"**{tool['title']}**")
            st.write(tool["text"])
            if "link" in tool:
                st.markdown(f"[{tool['link'][0]}]({tool['link'][1]})")
    st.markdown("##### Signs it is time to ask for help sooner")
    for flag in je.DETERIORATION_FLAGS:
        st.markdown(f"- {flag}")
    st.warning(je.DETERIORATION_ADVICE)


def _rights() -> None:
    st.markdown("#### Your choices while you wait")
    st.markdown(
        "- **NHS Talking Therapies (for anxiety and depression):** you can refer yourself, without seeing a GP.\n"
        "- **Choosing where to go:** when a GP refers you, you usually have a legal right to choose where you go for "
        "a first outpatient appointment, and you can ask to be moved to a different provider if you are likely to "
        "wait longer than the maximum waiting time. Some choices depend on what is available locally.\n"
        "- **Ask for an urgent review:** if you are getting worse while you wait, contact the service and your GP and "
        "tell them. Getting worse can change how quickly you are seen."
    )
    for label, url in je.CHOICE_LINKS:
        st.markdown(f"- [{label}]({url})")
    st.markdown("##### Right to Choose providers")
    st.warning("The providers below offer **autism and ADHD assessments**. Right to Choose is not a way around a "
               "long wait for talking therapy. For that, refer yourself to an NHS Talking Therapies service. "
               "Ask your GP whether Right to Choose applies to you.")
    for prov in je.RIGHT_TO_CHOOSE_PROVIDERS:
        with st.container(border=True):
            st.markdown(f"### [{prov['name']}]({prov['url']})")
            st.write(f"From their own page: {prov['says']}")
            st.caption(f"Checked: {je.RIGHT_TO_CHOOSE_CHECKED}. Check that they accept referrals for your area.")


def _gp_letter() -> None:
    st.markdown("#### A letter to ask your GP for support")
    st.caption("This writes a letter from your own answers. It asks questions rather than making demands, and it "
               "does not add any statistics.")
    with st.form("gp_form"):
        name = st.text_input("Your name")
        surgery = st.text_input("Your GP surgery")
        condition = st.selectbox("What are you struggling with?",
                                 [je.TAG_LABELS[t] for t in TOPIC_OPTIONS] + ["Something else"])
        weeks = st.number_input("About how many weeks have you been waiting?", 0, 300, 8)
        impact = st.text_input("How is it affecting your life? (optional)",
                               placeholder="For example: I have been off work for two weeks.")
        provider = st.selectbox("Would you like to ask about a Right to Choose provider? (autism or ADHD assessment)",
                                ["No", *[p["name"] for p in je.RIGHT_TO_CHOOSE_PROVIDERS]])
        phq9, gad7 = _score_choice()
        submitted = st.form_submit_button("Write my letter", type="primary")
    if submitted:
        text = je.gp_letter(name, surgery, condition, int(weeks), impact, "" if provider == "No" else provider,
                            phq9, gad7)
        _save_letter("gp", "Your letter to your GP", text, _filename(name, "GP_letter"))
    _show_saved_letter("gp")


def _sbar() -> None:
    st.markdown("#### A 2 minute briefing for your GP appointment")
    st.caption("GP appointments are short. This puts what you tell it into the SBAR layout (Situation, "
               "Background, Assessment, Request) that clinicians know. It only reports what you enter.")
    with st.form("sbar_form"):
        name = st.text_input("Your name")
        symptoms = st.text_input("What are you struggling with?", placeholder="For example: panic attacks and poor sleep")
        duration = st.selectbox("For how long?", ["Less than a month", "1 to 3 months", "3 to 6 months",
                                                  "6 to 12 months", "More than a year"])
        impact = st.text_input("Effect on work or daily life")
        request = st.selectbox("What would you like from the appointment?", [
            "a referral or a faster referral to NHS Talking Therapies or a specialist team",
            "advice on support while I wait",
            "a review of my medication",
            "a fit note",
            "to talk about my choices of provider",
        ])
        phq9, gad7 = _score_choice()
        submitted = st.form_submit_button("Write my briefing", type="primary")
    if submitted:
        item9 = st.session_state.get("jarvis_phq9_item9") if phq9 is not None else None
        text = je.sbar_briefing(name, symptoms, duration, impact, request, phq9, gad7, item9)
        _save_letter("sbar", "Your briefing", text, _filename(name, "GP_briefing"))
    _show_saved_letter("sbar")


def _work() -> None:
    st.markdown("#### Work and money guide")
    st.caption("A plain guide with links to the official pages. Amounts change, so this page does not repeat them.")
    for item in je.WORKPLACE_GUIDE:
        with st.container(border=True):
            st.markdown(f"**{item['title']}**")
            st.write(item["text"])
            for label, url in item["links"]:
                st.markdown(f"- [{label}]({url})")


def _calculator() -> None:
    st.markdown("#### What could sick leave cost me?")
    st.caption("Simple arithmetic on the numbers you enter. It does not use or invent any other data.")
    salary = st.number_input("Your gross yearly pay (£, before tax)", 0, 200_000, 30_000, step=1000)
    scenario = st.radio("What is your situation?", list(je.INCOME_SCENARIOS), format_func=je.INCOME_SCENARIOS.get)
    weeks = st.slider("For how many weeks?", 1, 104, 12)
    pct = 0
    if scenario == "reduced_hours":
        pct = st.slider("By how much have your hours (and pay) dropped?", 0, 100, 20, format="%d%%")
    try:
        result = je.estimate_income_impact(salary, scenario, weeks, pct)
    except ValueError as err:
        st.error(str(err))
        return
    c1, c2 = st.columns(2)
    c1.metric("Your usual weekly pay", f"£{result.weekly_gross:,.2f}")
    c2.metric("Estimated pay lost", f"£{result.total_lost:,.2f}")
    for note in result.notes:
        st.caption(note)
    st.markdown(f"[GOV.UK: Statutory Sick Pay]({je.SSP_SOURCE_URL})")


def _mp_letter() -> None:
    st.markdown("#### A letter to your MP")
    st.caption("MPs can ask your local NHS body for waiting time information. Find your MP at "
               "[writetothem.com](https://www.writetothem.com/).")
    with st.form("mp_form"):
        name = st.text_input("Your name")
        postcode = st.text_input("Your postcode", help="Your MP needs this to know you are a constituent.")
        mp = st.text_input("Your MP's name (optional)")
        condition = st.selectbox("What are you waiting for support with?",
                                 [je.TAG_LABELS[t] for t in TOPIC_OPTIONS] + ["Something else"])
        weeks = st.number_input("About how many weeks have you been waiting?", 0, 300, 8)
        lookup = st.checkbox("Also name my NHS area in the letter. This sends my postcode to postcodes.io "
                             "(a free postcode service) to find it.")
        submitted = st.form_submit_button("Write my letter", type="primary")
    if submitted:
        icb = None
        if lookup:
            found = je.lookup_icb(postcode)
            if found.ok:
                icb = found.icb_name
            else:
                st.warning(lookup_message(found.reason) + " The letter was written without it.")
        _save_letter("mp", "Your letter to your MP", je.mp_letter(name, postcode, mp, int(weeks), condition, icb),
                     _filename(name, "MP_letter"))
    _show_saved_letter("mp")


def lookup_message(reason: str) -> str:
    return {
        "invalid": "That does not look like a UK postcode.",
        "not_found": "That postcode was not found.",
        "not_england": "That postcode is not in England, and this tool only covers England.",
        "no_icb": "No NHS area was listed for that postcode.",
        "unavailable": "The postcode service could not be reached just now.",
    }.get(reason, "Your NHS area could not be found.")


# ---------------------------------------------------------------------------
# Entry point called from app.py
# ---------------------------------------------------------------------------
def render(orgs: Sequence[Dict[str, str]], resources: Sequence[Dict[str, str]]) -> None:
    st.subheader(f"{je.ASSISTANT_NAME}: your guide while you wait")
    _crisis_banner()
    with st.expander("About this guide (please read)"):
        st.markdown(
            "- This is a **rule-based guide**, not an AI chatbot and not a clinician. It matches words and follows "
            "fixed rules, so it can get things wrong.\n"
            "- It gives information, not medical advice, and it cannot diagnose anything.\n"
            "- We do not save what you type. Your questionnaire scores last only for this visit.\n"
            "- The only thing that leaves the app is a postcode, and only if you tick the box that says so."
        )
    mode = st.selectbox("What would you like help with?", list(MODES), format_func=MODES.get)
    st.divider()
    if mode == "triage":
        _triage(orgs)
    elif mode == "screening":
        _screening()
    elif mode == "programme":
        _programme(orgs, resources)
    elif mode == "toolkit":
        _toolkit()
    elif mode == "rights":
        _rights()
    elif mode == "gp_letter":
        _gp_letter()
    elif mode == "sbar":
        _sbar()
    elif mode == "work":
        _work()
    elif mode == "calculator":
        _calculator()
    elif mode == "mp_letter":
        _mp_letter()
