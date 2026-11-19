# Mental Health Navigator

A free, open-source tool for people waiting for NHS mental health support in England.
It helps you see how long NHS waits are in your area, find support while you wait, and
write letters that ask your GP and MP the right questions.

**It is not an NHS service and it does not give medical advice.**
If you are in crisis: Samaritans 116 123 (free, 24/7) · text SHOUT to 85258 · NHS 111, option 2 · 999 in an emergency.

## What is in the app

| Tab | What it does |
|---|---|
| Find my wait time | Postcode to NHS area (via postcodes.io), real physical health waiting time for that area, your rights in plain English |
| Jarvis Navigator | A rule-based guide (not an AI chatbot): describe how you feel and get suggested services, PHQ-9 and GAD-7 questionnaires, free things to try, coping toolkit, GP letter, GP briefing, work and money guide, sick leave cost calculator, MP letter |
| The postcode lottery | Physical health waits across the 42 NHS areas |
| Get support now | Five questions, up to three matched organisations |
| The economic cost | Real national NHS Talking Therapies figures |

## Run it

```
pip install -r requirements.txt
streamlit run app.py
```

## Test it

```
python -m unittest -v
python check_links.py
```

* `test_jarvis_engine.py` tests the rules (crisis wording, scoring, letters, money, data files).
* `test_app.py` runs the real app headlessly and clicks through it.
* `check_links.py` opens every link in the app. Run it every month or two: links go out of date.

## Project structure

```
app.py                  page layout and the simple tabs
jarvis_ui.py            the screens inside the Jarvis tab
jarvis_engine.py        the rules behind Jarvis (no Streamlit, fully tested)
matching_engine.py      the five question matcher
organisations.csv       support organisations (each with a link and a date checked)
resources.csv           free NHS self help and peer support (each with a source and a date checked)
rtt_by_icb_real.csv     real RTT waits for 42 NHS areas, March 2026
.streamlit/config.toml  light NHS theme (this exact folder name is required by Streamlit)
REVIEW.md               what was checked, fixed, and what still needs a decision
```

## Data rule

The app only shows numbers it can source. Where a number is not available it says so.

* Real: physical health waits by area (NHS England RTT, March 2026); national NHS Talking Therapies figures (2025-26 annual report).
* Not connected yet: mental health waiting times by area. Nothing is shown rather than an estimate.
* Updated each April: the Statutory Sick Pay figures in `jarvis_engine.py` (they carry their GOV.UK source and the date they were checked).

## Privacy

The app does not save what you type. The only thing that leaves it is a postcode sent to
postcodes.io, and only when you ask for an area lookup.

## Sources

NHS Talking Therapies statistics (digital.nhs.uk) · NHS England RTT waiting times (england.nhs.uk) ·
ONS postcode data via postcodes.io · GOV.UK · NHS.uk
