import unittest

from streamlit.testing.v1 import AppTest

from logic import events

ROOT = __file__.rsplit("tests", 1)[0]


def start():
    at = AppTest.from_file(ROOT + "app.py", default_timeout=20).run()
    at.button[0].click().run()
    return at


def opts(at):
    return [b for b in at.button if b.key and b.key[:4] in ("opt_", "sel_")]


def evs(at, name):
    return [e for e in events.BUFFER if e["session_id"] == at.session_state.sid and e["event"] == name]


def finish(at):
    for _ in range(12):
        opts(at)[0].click().run()
    return at


class UiTest(unittest.TestCase):
    def test_home_has_image_and_start_button(self):
        at = AppTest.from_file(ROOT + "app.py", default_timeout=20).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.button[0].label, "테스트 시작 🚀")
        html = " ".join(m.value for m in at.markdown)
        self.assertIn('class="sz-img"', html)
        self.assertNotIn('<div class="sz-big">', html)

    def test_quiz_2x2_options_and_no_next_button(self):
        at = start()
        self.assertEqual(len(opts(at)), 4)
        self.assertEqual(len(at.columns), 4)  # 2행 x 2열
        self.assertFalse([b for b in at.button if "다음" in b.label or "결과 보기" in b.label])
        css = at.markdown[0].value
        self.assertIn("flex-wrap:nowrap", css)

    def test_click_advances_immediately_and_logs_once(self):
        at = start()
        opts(at)[0].click().run()
        self.assertEqual(at.session_state.index, 1)
        self.assertEqual(len(at.session_state.answers), 1)
        self.assertEqual(len(evs(at, "answer_select")), 1)
        self.assertEqual(len(evs(at, "question_next")), 1)
        at.run()
        at.run()  # rerun으로 중복 기록되지 않음
        self.assertEqual(len(evs(at, "answer_select")), 1)
        self.assertEqual(len(evs(at, "question_view")), 2)

    def test_back_keeps_selection_and_timer(self):
        at = start()
        t0 = at.session_state.started[0]
        opts(at)[1].click().run()
        picked = at.session_state.answers[1]
        [b for b in at.button if b.key == "prev"][0].click().run()
        self.assertEqual(at.session_state.index, 0)
        self.assertEqual(at.session_state.started[0], t0)  # 타이머 리셋 없음
        self.assertEqual([b.key for b in opts(at) if b.key.startswith("sel_")], [f"sel_{picked}"])

    def test_last_click_goes_to_result_with_all_sections(self):
        at = finish(start())
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, "result")
        html = " ".join(m.value for m in at.markdown)
        for key in ("MY CARD DNA", "나의 소비 DNA", "추천 카드 혜택", "숨겨진 카드 성향", "소비 TIP", "가상의 혜택"):
            self.assertIn(key, html)
        self.assertEqual(html.count('class="rs-dna"'), 4)
        self.assertEqual(html.count('class="rs-fill"'), 3)
        self.assertEqual(len(evs(at, "result_view")), 1)

    def test_reco_click_logged_once_and_highlighted(self):
        at = finish(start())
        b = [b for b in at.button if b.key == "reco_0"][0]
        b.click().run()
        [x for x in at.button if x.key == "recsel_0"][0].click().run()  # 같은 혜택 재클릭
        self.assertEqual(len(evs(at, "recommendation_click")), 1)

    def test_feedback_recorded_once_per_session(self):
        at = finish(start())
        [b for b in at.button if b.key == "fb_somewhat"][0].click().run()
        self.assertEqual(at.session_state.fb, "somewhat")
        [b for b in at.button if b.key == "fbsel_somewhat"][0].click().run()
        fb = evs(at, "feedback_submit")
        self.assertEqual([e["rating"] for e in fb], ["somewhat"])
        self.assertTrue(all(b.disabled for b in at.button if b.key in ("fb_very_similar", "fb_different")))

    def test_restart_resets_state(self):
        at = finish(start())
        [b for b in at.button if b.key == "again"][0].click().run()
        self.assertEqual(at.session_state.page, "home")
        self.assertEqual(at.session_state.answers, {})
        self.assertIsNone(at.session_state.fb)

    def test_result_renders_for_all_six_characters(self):
        import json
        qs = json.load(open(ROOT + "data/questions.json", encoding="utf-8"))
        cs = json.load(open(ROOT + "data/characters.json", encoding="utf-8"))
        self.assertEqual(len(cs), 6)
        for c in cs:
            ans = {q["id"]: next((o["id"] for o in q["options"] if c["id"] in o["scores"]), "A") for q in qs}
            at = AppTest.from_file(ROOT + "app.py", default_timeout=20)
            at.session_state.page, at.session_state.answers = "result", ans
            at.run()
            self.assertFalse(at.exception, (c["id"], at.exception))
            html = " ".join(m.value for m in at.markdown)
            self.assertIn(c["name"], html, c["id"])
            self.assertEqual(html.count('class="rs-dna"'), len(c["dna"]), c["id"])
            self.assertEqual(len([b for b in at.button if b.key and b.key.startswith("reco")]), len(c["benefits"]))


class NormalizeTest(unittest.TestCase):
    def test_legacy_character_without_dna_tip_and_string_benefits(self):
        from logic.content import normalize_character
        old = {"id": "x", "name": "옛 캐릭터", "memes": ["a", "b", "c", "d"], "benefits": ["캐시백"],
               "cautions": ["충동구매"]}
        n = normalize_character(old)
        self.assertEqual([d["text"] for d in n["dna"]], ["a", "b", "c", "d"])
        self.assertEqual(n["benefits"][0], {"icon": "🎁", "name": "캐시백", "desc": ""})
        self.assertIn("충동구매", n["tip"])
        for k in ("emoji", "color", "trait", "quote", "desc", "mate"):
            self.assertIn(k, n)

    def test_empty_character_does_not_raise(self):
        from logic.content import normalize_character
        n = normalize_character({"id": "y"})
        self.assertEqual(n["dna"], [])
        self.assertTrue(n["tip"])


if __name__ == "__main__":
    unittest.main()
