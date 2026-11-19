"""
End to end tests: these run the real Streamlit app headlessly and click through it.
Run with:   python -m unittest test_app -v
No network is used (the postcode box is only tested with an invalid postcode).
"""

import os
import unittest

from streamlit.testing.v1 import AppTest

import jarvis_engine as je

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")


def fresh() -> AppTest:
    return AppTest.from_file(APP, default_timeout=60).run()


def choose_mode(at: AppTest, mode: str) -> AppTest:
    box = next(s for s in at.selectbox if s.label == "What would you like help with?")
    box.select(mode)
    return at.run()


def all_text(at: AppTest) -> str:
    parts = []
    for group in (at.markdown, at.error, at.warning, at.info, at.success, at.caption, at.metric):
        parts += [str(getattr(el, "value", "")) for el in group]
    return "\n".join(parts)


class AppStarts(unittest.TestCase):
    def test_loads_without_errors_and_has_six_tabs(self):
        at = fresh()
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])
        self.assertEqual(len(at.tabs), 6)

    def test_every_jarvis_mode_renders_without_errors(self):
        at = fresh()
        for mode in ("triage", "screening", "programme", "toolkit", "rights", "gp_letter", "sbar", "work",
                     "calculator", "mp_letter"):
            with self.subTest(mode=mode):
                at = choose_mode(at, mode)
                self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])

    def test_no_streamlit_warnings_are_shown_to_visitors(self):
        """A deprecated argument makes Streamlit print a warning box on the page for every visitor."""
        at = fresh()
        text = all_text(at).lower()
        for banned in ("deprecated", "will be removed in a future release"):
            self.assertFalse(banned in text, f"the page shows {banned!r}")

    def test_crisis_contacts_are_always_on_screen(self):
        text = all_text(fresh())
        for needle in ("116 123", "85258", "111", "999"):
            self.assertTrue(needle in text, f"crisis contact {needle!r} missing")


class NoInventedNumbers(unittest.TestCase):
    """The page text must not bring back figures that were removed because they could not be sourced."""

    def test_removed_figures_are_gone(self):
        at = fresh()
        text = all_text(at)
        for banned in ("2.8M", "£28bn", "£66,000", "28 weeks +7", "52 weeks", "6-week target", "1.7 million",
                       "Estimated Mental Health Wait", "7.05 million", "AI Navigator"):
            self.assertFalse(banned in text, f"the page still shows {banned!r}")


class TriageFlow(unittest.TestCase):
    def submit(self, text):
        at = choose_mode(fresh(), "triage")
        at.text_area[0].set_value(text)
        at.button[[b.label for b in at.button].index("Suggest services")].click()
        return at.run()

    def test_crisis_words_show_the_crisis_contacts_and_only_24_hour_services(self):
        at = self.submit("I can’t go on and I want to end my life")
        self.assertEqual(len(at.exception), 0)
        errors = " ".join(e.value for e in at.error)
        self.assertIn("116 123", errors)
        self.assertIn("85258", errors)
        cards = " ".join(m.value for m in at.tabs[1].markdown)     # the Jarvis tab only
        self.assertIn("Samaritans", cards)
        self.assertNotIn("Beat Eating", cards)

    def test_everyday_text_gets_topic_matches_not_crisis(self):
        at = self.submit("I have had panic attacks at work and I am waiting for treatment")
        self.assertEqual(len(at.exception), 0)
        cards = " ".join(m.value for m in at.tabs[1].markdown)     # the Jarvis tab only
        self.assertIn("Anxiety UK", cards)
        self.assertNotIn("Beat Eating Disorders", cards)       # 'treatment' used to trigger the eating tag
        self.assertNotIn("Samaritans", cards)

    def test_empty_text_asks_for_words(self):
        at = self.submit("   ")
        self.assertTrue(any("few words" in w.value for w in at.warning))


class ScreeningFlow(unittest.TestCase):
    def open_phq(self):
        at = choose_mode(fresh(), "screening")
        return at

    def submit(self, at):
        label = [b.label for b in at.button]
        at.button[label.index("Score my answers")].click()
        return at.run()

    def test_skipped_questions_are_refused_not_scored_as_zero(self):
        at = self.submit(self.open_phq())
        self.assertTrue(any("answer every question" in e.value for e in at.error))
        self.assertFalse(any(m.label == "Your score" for m in at.metric))
        self.assertNotIn("jarvis_phq9", at.session_state)

    def test_complete_answers_are_scored_and_remembered(self):
        at = self.open_phq()
        for radio in at.radio:
            if radio.label[:2] in {f"{i}." for i in range(1, 10)}:
                radio.set_value(1)
        at = self.submit(at)
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.session_state["jarvis_phq9"], 9)
        self.assertTrue(any("9 out of 27" in m.value for m in at.metric))
        self.assertTrue(any("Mild" in m.value for m in at.markdown))

    def test_item_nine_answer_triggers_a_safety_message(self):
        at = self.open_phq()
        for radio in at.radio:
            if radio.label[:2] in {f"{i}." for i in range(1, 10)}:
                radio.set_value(0)
        next(r for r in at.radio if r.label.startswith("9.")).set_value(1)
        at = self.submit(at)
        self.assertTrue(any("better off dead" in e.value and "116 123" in e.value for e in at.error))


class LetterFlow(unittest.TestCase):
    def test_gp_letter_is_written_from_the_form(self):
        at = choose_mode(fresh(), "gp_letter")
        next(t for t in at.text_input if t.label == "Your name").set_value("Sam Example")
        next(t for t in at.text_input if t.label == "Your GP surgery").set_value("The Test Surgery")
        at.button[[b.label for b in at.button].index("Write my letter")].click()
        at = at.run()
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])
        box = next(t for t in at.text_area if t.label.startswith("Your letter"))
        self.assertIn("Sam Example", box.value)
        self.assertIn("The Test Surgery", box.value)
        self.assertNotIn("**", box.value)
        self.assertNotIn("Gokul", box.value)

    def test_letter_survives_a_rerun(self):
        at = choose_mode(fresh(), "gp_letter")
        at.button[[b.label for b in at.button].index("Write my letter")].click()
        at = at.run().run()      # any other click makes Streamlit run the script again
        self.assertTrue(any(t.label.startswith("Your letter") for t in at.text_area))

    def test_scores_are_left_out_unless_ticked(self):
        at = choose_mode(fresh(), "screening")
        for radio in at.radio:
            if radio.label[:2] in {f"{i}." for i in range(1, 10)}:
                radio.set_value(2)
        at.button[[b.label for b in at.button].index("Score my answers")].click()
        at = choose_mode(at.run(), "gp_letter")
        at.button[[b.label for b in at.button].index("Write my letter")].click()
        at = at.run()
        self.assertNotIn("PHQ-9", next(t for t in at.text_area if t.label.startswith("Your letter")).value)
        next(c for c in at.checkbox if c.label.startswith("Include my questionnaire scores")).check()
        at.button[[b.label for b in at.button].index("Write my letter")].click()
        at = at.run()
        self.assertIn("PHQ-9 (low mood) 18 out of 27",
                      next(t for t in at.text_area if t.label.startswith("Your letter")).value)


class CalculatorFlow(unittest.TestCase):
    def test_default_numbers_match_the_engine(self):
        at = choose_mode(fresh(), "calculator")
        self.assertEqual(len(at.exception), 0)
        expected = je.estimate_income_impact(30_000, "ssp", 12)
        values = {m.label: m.value for m in at.metric}
        self.assertEqual(values["Estimated pay lost"], f"£{expected.total_lost:,.2f}")


class FindAreaFlow(unittest.TestCase):
    def test_bad_postcode_gets_a_clear_message_and_no_guess(self):
        at = fresh()
        at.text_input[0].set_value("hello")
        at.button[0].click()
        at = at.run()
        self.assertTrue(any("does not look like a UK postcode" in w.value for w in at.warning))
        self.assertFalse(any("Your NHS area" in s.value for s in at.success))

    def test_choosing_an_area_from_the_list_shows_real_wait_and_the_mental_health_notice(self):
        at = fresh()
        at.selectbox[0].select_index(3)
        at = at.run()
        self.assertTrue(any("Average wait for physical health treatment" == m.label for m in at.metric))
        self.assertTrue(any("not shown here yet" in w.value for w in at.warning))


if __name__ == "__main__":
    unittest.main()
