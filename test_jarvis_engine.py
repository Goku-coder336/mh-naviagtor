"""
Tests for jarvis_engine.py and matching_engine.py.
Run from the project folder with:   python -m unittest -v
No network access is needed: the postcode lookup is tested with a fake web call.
"""

import itertools
import os
import re
import unittest
from datetime import date

import jarvis_engine as je
import matching_engine as me

HERE = os.path.dirname(os.path.abspath(__file__))
ORGS = je.load_rows(je.find_data_file("organisations.csv"))
RTT = je.load_rows(je.find_data_file("rtt_by_icb_real.csv"))
RESOURCES = je.load_rows(je.find_data_file("resources.csv"))


class FakeResponse:
    def __init__(self, status=200, payload=None, bad_json=False):
        self.status_code, self._payload, self._bad = status, payload, bad_json

    def json(self):
        if self._bad:
            raise ValueError("not json")
        return self._payload


class CrisisDetection(unittest.TestCase):
    MUST_FIRE = [
        "I want to kill myself",
        "I keep thinking about self-harm",
        "thinking about self‑harm",                 # non-breaking hyphen, as pasted from some apps
        "I can’t go on like this",                   # curly apostrophe, the iPhone default
        "I want to take my own life",
        "I wish I was dead",
        "I don't want to be here anymore",
        "I don’t want to be here anymore",
        "there is no point in living",
        "no reason to live",
        "I've been cutting myself",
        "I'm thinking of an overdose",
        "SUICIDAL thoughts again",
        "my family would be better off without me",
        "I am going to hang myself",
    ]
    MUST_NOT_FIRE = [
        "I feel jumpy and on edge",
        "my diet is a mess",
        "I was dying of embarrassment",
        "I am waiting for treatment and feel low",
        "I don't know where to turn",
        "the pump slit open",
        "",
        None,
    ]

    def test_fires_on_real_phrasing(self):
        for text in self.MUST_FIRE:
            with self.subTest(text=text):
                self.assertTrue(je.detect_crisis(text).is_crisis)

    def test_stays_quiet_on_everyday_phrasing(self):
        for text in self.MUST_NOT_FIRE:
            with self.subTest(text=text):
                self.assertFalse(je.detect_crisis(text).is_crisis)

    def test_message_contains_every_crisis_contact(self):
        message = je.crisis_message_markdown()
        for needle in ("116 123", "85258", "111", "999"):
            self.assertIn(needle, message)


class ReadingFreeText(unittest.TestCase):
    def test_treatment_is_not_an_eating_difficulty(self):
        self.assertNotIn("eating", je.detect_tags("I am waiting for treatment and feel low"))

    def test_know_is_not_urgent(self):
        self.assertEqual(je.detect_urgency("I don't know where to turn"), "standard")

    def test_community_checked_great_do_not_trigger_topics(self):
        self.assertEqual(je.detect_tags("I feel part of my community and checked my great phone"), ["general"])

    def test_real_topics_are_found(self):
        self.assertIn("anxiety", je.detect_tags("I have panic attacks every morning"))
        self.assertIn("eating", je.detect_tags("I think I have an eating disorder"))
        self.assertIn("grief", je.detect_tags("I lost my dad in the spring"))
        self.assertIn("trauma", je.detect_tags("flashbacks and nightmares since the accident"))

    def test_urgency_levels(self):
        self.assertEqual(je.detect_urgency("I need help tonight"), "immediate")
        self.assertEqual(je.detect_urgency("it is getting worse"), "elevated")


class Matching(unittest.TestCase):
    def test_crisis_text_returns_only_24_hour_services(self):
        result = je.triage("I want to end my life", ORGS)
        self.assertTrue(result.crisis.is_crisis)
        self.assertTrue(result.matches)
        self.assertTrue(all(o["urgency_level"] == "immediate" for o in result.matches))

    def test_everyday_text_does_not_return_crisis_lines(self):
        result = je.triage("I have been feeling anxious for months", ORGS)
        self.assertFalse(result.crisis.is_crisis)
        self.assertTrue(result.matches)
        self.assertTrue(all(o["urgency_level"] != "immediate" for o in result.matches))

    def test_at_most_three_and_topic_must_match(self):
        result = je.rank_organisations(ORGS, ["ocd"])
        self.assertLessEqual(len(result), 3)
        self.assertEqual(result[0]["name"], "OCD Action")
        for org in result:
            tags = je._cells(org["condition_tags"])
            self.assertTrue("ocd" in tags or "general" in tags)

    def test_age_filter_is_respected(self):
        names = {o["name"] for o in je.rank_organisations(ORGS, ["anxiety"], age_band="Under 18", limit=10)}
        self.assertNotIn("NHS Talking Therapies", names)  # 18 and over
        self.assertIn("Kooth", names)

    def test_no_topic_gives_general_services_not_nothing(self):
        self.assertTrue(je.rank_organisations(ORGS, ["general"]))

    def test_matching_is_deterministic(self):
        first = [o["name"] for o in je.rank_organisations(ORGS, ["depression"])]
        self.assertEqual(first, [o["name"] for o in je.rank_organisations(ORGS, ["depression"])])


class Screening(unittest.TestCase):
    def test_phq9_band_edges(self):
        edges = {0: "Minimal", 4: "Minimal", 5: "Mild", 9: "Mild", 10: "Moderate", 14: "Moderate",
                 15: "Moderately severe", 19: "Moderately severe", 20: "Severe", 27: "Severe"}
        for score, label in edges.items():
            answers = [0] * 9
            remaining = score
            for i in range(9):
                answers[i] = min(3, remaining)
                remaining -= answers[i]
            with self.subTest(score=score):
                result = je.score_phq9(answers)
                self.assertEqual((result.score, result.severity), (score, label))

    def test_gad7_band_edges(self):
        edges = {0: "Minimal", 4: "Minimal", 5: "Mild", 9: "Mild", 10: "Moderate", 14: "Moderate",
                 15: "Severe", 21: "Severe"}
        for score, label in edges.items():
            answers, remaining = [0] * 7, score
            for i in range(7):
                answers[i] = min(3, remaining)
                remaining -= answers[i]
            with self.subTest(score=score):
                self.assertEqual(je.score_gad7(answers).severity, label)

    def test_item_nine_any_answer_above_zero_raises_safety_flag(self):
        self.assertFalse(je.score_phq9([0] * 9).safety_flag)
        self.assertTrue(je.score_phq9([0] * 8 + [1]).safety_flag)
        self.assertTrue(je.score_phq9([0] * 8 + [3]).safety_flag)

    def test_bad_input_is_refused_not_scored(self):
        for bad in ([3, 3, 3], [99] * 9, [0] * 8 + [-1], [0] * 8 + [True], [0] * 8 + [1.5], None, [0] * 10):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    je.score_phq9(bad)
        with self.assertRaises(ValueError):
            je.score_gad7([0] * 9)

    def test_every_result_says_it_is_not_a_diagnosis(self):
        self.assertIn("not a diagnosis", je.score_phq9([1] * 9).guidance)
        self.assertIn("not a diagnosis", je.score_gad7([1] * 7).guidance)

    def test_question_counts(self):
        self.assertEqual(len(je.PHQ9_QUESTIONS), 9)
        self.assertEqual(len(je.GAD7_QUESTIONS), 7)


class Postcodes(unittest.TestCase):
    def test_normalise(self):
        self.assertEqual(je.normalise_postcode("rg1  2ab"), "RG1 2AB")
        self.assertEqual(je.normalise_postcode("M11AE"), "M1 1AE")
        self.assertEqual(je.normalise_postcode("SW1A 2AA"), "SW1A 2AA")
        for bad in ("", None, "hello", "12345", "ZZ", "RG1", "RG1 2AB 9"):
            with self.subTest(bad=bad):
                self.assertIsNone(je.normalise_postcode(bad))

    def ok(self, **extra):
        body = {"result": {"country": "England", "icb": "NHS South East London Integrated Care Board",
                           "admin_district": "Lambeth", **extra}}
        return lambda url, timeout: FakeResponse(200, body)

    def test_success(self):
        result = je.lookup_icb("SW9 9TG", http_get=self.ok())
        self.assertTrue(result.ok)
        self.assertEqual(result.icb_name, "NHS South East London Integrated Care Board")

    def test_every_failure_is_reported_never_guessed(self):
        def boom(url, timeout):
            raise TimeoutError("slow")
        cases = {
            "invalid": je.lookup_icb("hello", http_get=self.ok()),
            "not_found": je.lookup_icb("ZZ1 1ZZ", http_get=lambda u, timeout: FakeResponse(404, {})),
            "unavailable": je.lookup_icb("SW9 9TG", http_get=boom),
            "unavailable ": je.lookup_icb("SW9 9TG", http_get=lambda u, timeout: FakeResponse(500, {})),
            "unavailable  ": je.lookup_icb("SW9 9TG", http_get=lambda u, timeout: FakeResponse(200, bad_json=True)),
            "not_england": je.lookup_icb("EH1 1YZ", http_get=lambda u, timeout: FakeResponse(
                200, {"result": {"country": "Scotland"}})),
            "no_icb": je.lookup_icb("SW9 9TG", http_get=lambda u, timeout: FakeResponse(
                200, {"result": {"country": "England"}})),
        }
        for expected, result in cases.items():
            with self.subTest(expected=expected):
                self.assertFalse(result.ok)
                self.assertEqual(result.reason, expected.strip())
                self.assertIsNone(result.icb_name)

    def test_icb_rows_match_by_name_or_return_none(self):
        row = je.find_icb_row("NHS South East London Integrated Care Board", RTT)
        self.assertIsNotNone(row)
        self.assertGreater(float(row["physical_health_wait_weeks"]), 0)
        self.assertIsNotNone(je.find_icb_row("NHS Staffordshire and Stoke-on-Trent Integrated Care Board", RTT))
        self.assertIsNone(je.find_icb_row("NHS Made Up Integrated Care Board", RTT))
        self.assertIsNone(je.find_icb_row(None, RTT))
        self.assertIsNone(je.find_icb_row("", RTT))


class Letters(unittest.TestCase):
    TODAY = date(2026, 11, 18)

    def gp(self, **kw):
        base = dict(patient_name="A Patient", gp_surgery="The Surgery", condition="anxiety", weeks_waiting=20,
                    impact="I cannot sleep", today=self.TODAY)
        base.update(kw)
        return je.gp_letter(**base)

    def test_no_markdown_no_developer_name_no_invented_statistics(self):
        for text in (self.gp(), je.mp_letter("A Patient", "sw9 9tg", "Ms Smith", 20, "anxiety", today=self.TODAY),
                     je.sbar_briefing("A Patient", "low mood", "3 months", "off work", "a referral")):
            with self.subTest(text=text[:30]):
                self.assertNotIn("**", text)
                self.assertNotIn("###", text)
                for banned in ("Gokul", "Rajan", "median", "billion", "2.8", "Principle 4", "breach", "AQP"):
                    self.assertNotIn(banned, text)

    def test_gp_letter_uses_only_what_the_user_gave(self):
        text = self.gp()
        self.assertIn("18 November 2026", text)
        self.assertIn("about 20 weeks", text)
        self.assertIn("I cannot sleep", text)
        self.assertNotIn("PHQ-9", text)          # no scores supplied, none invented

    def test_scores_and_provider_appear_only_when_supplied(self):
        text = self.gp(phq9=12, gad7=9, preferred_provider="Psychiatry-UK")
        self.assertIn("PHQ-9 (low mood) 12 out of 27", text)
        self.assertIn("GAD-7 (anxiety) 9 out of 21", text)
        self.assertIn("not a diagnosis", text)
        self.assertIn("Psychiatry-UK", text)

    def test_blank_fields_fall_back_safely(self):
        text = je.gp_letter("", "", "", 0, "", today=self.TODAY)
        self.assertIn("[your name]", text)
        self.assertIn("My GP practice", text)

    def test_control_characters_and_length_are_cleaned(self):
        self.assertEqual(je.clean_text("a\x00b\r\n c"), "ab c")
        self.assertEqual(len(je.clean_text("x" * 1000, 50)), 50)

    def test_mp_letter_only_names_the_area_when_known(self):
        without = je.mp_letter("A", "RG1 2AB", "", 10, "anxiety", today=self.TODAY)
        with_area = je.mp_letter("A", "RG1 2AB", "", 10, "anxiety", icb_name="NHS Thames Valley", today=self.TODAY)
        self.assertNotIn("NHS Thames Valley", without)
        self.assertIn("NHS Thames Valley", with_area)
        self.assertIn("House of Commons", without)

    def test_sbar_never_claims_absence_of_risk_it_did_not_ask_about(self):
        unasked = je.sbar_briefing("A", "low mood", "1 month", "x", "y")
        self.assertIn("Not assessed", unasked)
        self.assertNotIn("No acute", unasked)
        asked_yes = je.sbar_briefing("A", "low mood", "1 month", "x", "y", phq9=10, phq9_item9=1)
        self.assertIn("Several days", asked_yes)
        self.assertIn("Please ask me about this", asked_yes)
        asked_no = je.sbar_briefing("A", "low mood", "1 month", "x", "y", phq9=3, phq9_item9=0)
        self.assertIn("'Not at all'", asked_no)


class Money(unittest.TestCase):
    def test_ssp_uses_the_lower_of_flat_rate_and_80_percent(self):
        weekly = 35000 / 52
        result = je.estimate_income_impact(35000, "ssp", 24)
        self.assertAlmostEqual(result.total_lost, round(24 * (weekly - je.SSP_WEEKLY_RATE), 2), places=2)
        low = je.estimate_income_impact(5200, "ssp", 10)          # 100 a week: 80% (80) is below the flat rate
        self.assertAlmostEqual(low.total_lost, 10 * 20, places=2)

    def test_ssp_stops_after_28_weeks(self):
        weekly = 35000 / 52
        result = je.estimate_income_impact(35000, "ssp", 30)
        expected = 28 * (weekly - je.SSP_WEEKLY_RATE) + 2 * weekly
        self.assertAlmostEqual(result.total_lost, round(expected, 2), places=2)

    def test_other_scenarios(self):
        self.assertAlmostEqual(je.estimate_income_impact(52000, "left_job", 10).total_lost, 10000.0)
        self.assertAlmostEqual(je.estimate_income_impact(52000, "reduced_hours", 10, 50).total_lost, 5000.0)
        self.assertEqual(je.estimate_income_impact(52000, "reduced_hours", 10, 0).total_lost, 0.0)

    def test_nothing_is_invented_and_output_does_not_depend_on_unrelated_inputs(self):
        a = je.estimate_income_impact(40000, "left_job", 8)
        b = je.estimate_income_impact(40000, "left_job", 8)
        self.assertEqual(a, b)
        self.assertFalse(hasattr(a, "regional"))
        self.assertFalse(hasattr(a, "societal"))

    def test_bad_input_is_refused(self):
        for args in ((-1, "ssp", 5), (2_000_000, "ssp", 5), (30000, "ssp", -1), (30000, "ssp", 300),
                     (30000, "nonsense", 5), (30000, "reduced_hours", 5, 150)):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    je.estimate_income_impact(*args)

    def test_notes_carry_the_source_date(self):
        self.assertIn(je.SSP_CHECKED, " ".join(je.estimate_income_impact(30000, "ssp", 5).notes))


class DataFiles(unittest.TestCase):
    REQUIRED = {"name", "url", "description", "condition_tags", "age_group", "cost_category", "cost_max",
                "format_tags", "speed_rank", "urgency_level", "approach", "why_suits"}

    def test_organisations_are_complete(self):
        self.assertGreaterEqual(len(ORGS), 10)
        for org in ORGS:
            with self.subTest(org=org["name"]):
                self.assertTrue(self.REQUIRED <= set(org))
                self.assertTrue(org["url"].startswith("https://"))
                self.assertTrue(org["name"].strip() and org["description"].strip())
                self.assertIn(org["urgency_level"], {"immediate", "standard"})
                int(org["speed_rank"])
                float(org["cost_max"])

    def test_crisis_services_exist(self):
        names = {o["name"] for o in je.crisis_organisations(ORGS)}
        self.assertTrue({"Samaritans", "Shout"} <= names)

    def test_rtt_file_is_numeric_and_has_42_icbs(self):
        self.assertEqual(len(RTT), 42)
        for row in RTT:
            self.assertGreater(float(row["physical_health_wait_weeks"]), 0)
            self.assertGreater(int(row["patients_waiting"]), 0)

    def test_resources_have_sources_and_dates(self):
        for row in RESOURCES:
            with self.subTest(row=row["name"]):
                self.assertTrue(row["url"].startswith("https://"))
                self.assertTrue(row["source"].strip() and row["last_checked"].strip())

    def test_all_hard_coded_links_are_https(self):
        urls = [u for _, u in je.CHOICE_LINKS] + [p["url"] for p in je.RIGHT_TO_CHOOSE_PROVIDERS]
        urls += [u for g in je.WORKPLACE_GUIDE for _, u in g["links"]]
        urls += [t["link"][1] for t in je.COPING_TOOLKIT if "link" in t]
        self.assertTrue(urls)
        self.assertTrue(all(u.startswith("https://") for u in urls))


class FiveQuestionMatcher(unittest.TestCase):
    """matching_engine.py is the engine behind the 'Get support now' tab."""
    CONDITIONS = ["Anxiety or panic", "Low mood or depression", "Trauma or PTSD", "OCD or intrusive thoughts",
                  "Grief or bereavement", "Relationship difficulties", "Eating difficulties", "I'm not sure"]
    AGES = ["Under 18", "18 to 25", "26 to 64", "65 and over"]
    URGENCY = ["Tonight or this week", "Within the next month", "A few weeks is fine"]
    COST = ["Free only", "Up to £20 per session", "Cost is not the main concern"]
    FORMAT = ["Online or video", "Phone call", "Face to face", "Text or chat", "Something I can try on my own first"]

    def setUp(self):
        self.df = me.load_organisations(je.find_data_file("organisations.csv"))

    def test_all_1440_answer_combinations_run_and_respect_the_rules(self):
        crisis_names = {"Samaritans", "Shout", "NHS 111 option 2"}
        for c, a, u, k, f in itertools.product(self.CONDITIONS, self.AGES, self.URGENCY, self.COST, self.FORMAT):
            result = me.match_organisations(self.df, c, a, u, k, f)
            self.assertLessEqual(len(result), 3)
            names = set(result["name"])
            if u == "Tonight or this week":
                self.assertTrue(result.shape[0] > 0 and names <= crisis_names, (c, a, u, k, f))
            else:
                self.assertFalse(names & crisis_names, (c, a, u, k, f))
                if k == "Free only":
                    self.assertTrue((result["cost_category"] == "free").all())


class Architecture(unittest.TestCase):
    def test_engine_has_no_streamlit_and_never_prints_user_text(self):
        source = open(os.path.join(HERE, "jarvis_engine.py"), encoding="utf-8").read()
        self.assertNotRegex(source, r"^\s*(import|from)\s+streamlit", )
        self.assertIsNone(re.search(r"\bprint\(", source))
        self.assertIsNone(re.search(r"\blogging\b", source))

    def test_no_placeholder_links_left(self):
        source = open(os.path.join(HERE, "jarvis_engine.py"), encoding="utf-8").read()
        self.assertNotIn("example.com", source)


if __name__ == "__main__":
    unittest.main()
