# Review of the Jarvis build, 18 November 2026

## How it was checked

* The old engine was lifted out of `app.py` and run on real inputs, so every bug below was seen happening, not guessed.
* 62 automated tests (`python -m unittest -v`), including tests that click through the real app.
* The app was driven in a real browser on a desktop and at phone width.
* All 42 links in the app and data files were opened (`python check_links.py`).
* Facts were checked against GOV.UK, NHS England, NHS.uk, the providers' own pages and postcodes.io.

## Safety problems (fixed)

| Problem | Evidence | Fix |
|---|---|---|
| Crisis wording was missed | 6 of the 7 real crisis phrasings I tried failed: "self-harm" (the normal spelling), "can’t go on" with a curly apostrophe (the iPhone default), "take my own life", "wish I was dead", "don't want to be here", "no point in living" | Text is normalised first, then whole word patterns are used. Crisis contacts are also on screen all the time, because no word list catches everything |
| Everyday words raised a false alarm | "jumpy" triggered the crisis box (it matched "jump") | Whole word patterns |
| The GP briefing said "No acute suicide intent reported" | Printed even though the person was never asked | It now says "Not assessed", or reports the person's own PHQ-9 item 9 answer |
| Skipped questionnaire questions counted as zero | Radio buttons defaulted to "Not at all" | Nothing is pre-selected, incomplete answers are refused, and scores outside 0 to 3 raise an error (the old code scored 99s as 891) |
| The tool overclaimed | "Active clinical safety", "interception with zero delay", "autonomous", "AI" | Described honestly as a rule-based guide |

## Wrong or invented information (fixed)

| Problem | Evidence | Fix |
|---|---|---|
| Invented mental health waits by area, with a default of 28 weeks | They flowed into the GP and MP letters, introduced as "According to public NHS England waiting time data" | Removed everywhere. The app says the data is not connected |
| Postcode letters guessed the NHS area | Hounslow, Lambeth and Hackney landed in the wrong London area. Typos, blanks and Scottish, Welsh and Northern Irish postcodes silently became a Berkshire area with an invented 18 week wait | Real lookup via postcodes.io. Failures say so. Never a guess |
| Cost calculator was not arithmetic | "Regional drag" of £173.1M changed with the user's own salary (£98.9M at £20k). A 1.78 "ONS multiplier" and a 4.5 per cent "affected patients" figure had no source. Presenteeism was counted as the person's lost wages | Plain arithmetic on the person's own numbers, using the real Statutory Sick Pay rule (£123.25 or 80 per cent of earnings, whichever is lower, for up to 28 weeks, GOV.UK) |
| "Right to Choose" directory | The Right to Choose providers listed offer **autism and ADHD assessments**, not talking therapy. The quoted waits ("12 to 18 weeks") had no source, and the referral email address does not appear on ProblemShared's page | Only providers whose own pages describe Right to Choose, with their own words, and a clear warning about what it covers |
| Letters made legal claims | "Principle 4 of the NHS Constitution", "entitled to alternative providers with shorter waiting lists", "breaches the spirit of the Act" | Replaced with NHS England's published wording, phrased as questions to the GP |
| Developer's name in patients' letters, and markdown asterisks in plain text | "Generated via ... Gokul Rajan" | Removed. Letters are plain text |
| Out of date or unconfirmed figures | Sick pay £116.75 (GOV.UK now says £123.25). Access to Work "£66,000 a year" and "9 months of coaching" could not be found on GOV.UK | Replaced by links to the official pages |
| 25 podcast, video and peer entries | Of 31 links in the old engine, 3 were broken (two 404s and a certificate error) and 4 had moved. Several went to a site's front page, not the episode or video. Durations and "why listen" claims had no source | Replaced by services and resources that have a link and a date checked |
| Other tabs | "Shortest wait 9 weeks, Berkshire Healthcare" while the chart's shortest was 19. An invented 12 month trend. Scatter values typed in by position and credited to ONS. "2.8M" and "£28bn" with no source. "15.6 weeks" typed in (the file gives 15.5) | Real RTT chart only. Figures are worked out from the data files |
| About page | GitHub link was a 404 | Fixed |

## Engineering (fixed)

* The engine lived inside `app.py`: about 1,000 lines of static data re-read on every click, and impossible to test. Now `jarvis_engine.py` (no Streamlit) plus `jarvis_ui.py`.
* Substring matching: "treatment" matched "eat", so everyone waiting for treatment was sent to the eating disorder charity. "know" matched "now" (urgent). "community" matched "uni" (youth programme). Whole word matching now.
* A specialist charity now outranks a general directory on a tie (OCD Action over Hub of Hope for OCD).
* A second copy of the matcher inside `app.py` removed.
* `config.toml` was in the repo root, where Streamlit ignores it. It is now `.streamlit/config.toml`.
* The accessibility and phone fixes from earlier had been overwritten and are restored (wrapping tabs, 6px card border, focus ring, 16px text).
* `st.plotly_chart(width="stretch")` shows a visible deprecation warning to every visitor on Streamlit 1.50. Fixed and tested.
* Letters vanished when the box was edited, because Streamlit re-runs the page. They are now kept for the visit.

## Needs your decision (I did not change your data files)

1. `resources.csv`: "Berkshire West Your Way" links to `https://rva.org.uk/organisation/resource/`, which returns 404.
2. `organisations.csv` has claims shown to patients that have no source:
   * Kooth: "No waiting list in most areas"
   * Anxiety UK: "therapy access is usually much faster than NHS"
   * Hub of Hope: "rarely appear in national listings"
   * Samaritans: "no waiting and no referral"
   Each should have a source or be softened. Tell me and I will show you the diff first.
3. **Names.** J.A.R.V.I.S. and F.R.I.D.A.Y. are Marvel characters, and the "NHS" name and blue can look like an endorsement. The assistant name is one constant (`ASSISTANT_NAME`). Consider a neutral name.
4. **Not reviewed:** `index.html` (the static site, which calls postcodes.io from the browser) and `download_latest_data.py`.
5. **Not ported:** `cli_jarvis.py` (the terminal menu). It duplicated the website and was not working code on the new engine.
6. **Needs a person.** Have a clinician or a mental health charity read the questionnaire guidance, the toolkit and the letters before this is promoted to patients.

## Upkeep

* Each April: re-check the Statutory Sick Pay numbers in `jarvis_engine.py`.
* Every month or two: run `python check_links.py`.
* NHS areas are merging, so a few postcodes will not match the March 2026 data. The app says so instead of guessing.
