import json
import os
import tempfile
import unittest

from logic import events, supabase_sink


class EventsTest(unittest.TestCase):
    def test_all_events_trackable(self):
        got = []
        events.set_sink(got.append)
        for name, req in events.SCHEMA.items():
            events.track("s1", name, **{k: 1 for k in req})
        events.set_sink(None)
        self.assertEqual([e["event"] for e in got], list(events.SCHEMA))
        self.assertTrue(all(e["session_id"] == "s1" and "ts" in e for e in got))

    def test_missing_and_unknown(self):
        with self.assertRaises(ValueError):
            events.track("s", "question_view", question_id=1)
        with self.assertRaises(KeyError):
            events.track("s", "nope")

    def test_jsonl_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "e.jsonl")
            os.environ["CARD_DNA_EVENT_LOG"] = p
            try:
                events.track("s", "test_start")
            finally:
                del os.environ["CARD_DNA_EVENT_LOG"]
            with open(p, encoding="utf-8") as f:
                self.assertEqual(json.loads(f.read())["event"], "test_start")


class SupabaseSinkTest(unittest.TestCase):
    CFG = ("https://x.supabase.co", "KEY")

    def test_no_config_means_disabled(self):
        for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY"):
            os.environ.pop(k, None)
        self.assertIsNone(supabase_sink.load_config({}))
        self.assertIsNone(supabase_sink.load_config(None))

    def test_config_from_secrets_and_env(self):
        self.assertEqual(supabase_sink.load_config({"supabase": {"url": "https://a.co/", "anon_key": "k"}}),
                         ("https://a.co", "k"))
        os.environ.update(SUPABASE_URL="https://e.co", SUPABASE_ANON_KEY="ek")
        try:
            self.assertEqual(supabase_sink.load_config({}), ("https://e.co", "ek"))
        finally:
            del os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"]

    def test_request_shape_is_anonymous_row(self):
        rec = events.track("sid1", "question_view", question_id=3, index=2)
        req = supabase_sink.build_request(self.CFG, rec)
        self.assertEqual(req.full_url, "https://x.supabase.co/rest/v1/events")
        self.assertEqual(req.headers["Apikey"], "KEY")
        row = json.loads(req.data)
        self.assertEqual(row["event"], "question_view")
        self.assertEqual(row["session_id"], "sid1")
        self.assertEqual(row["props"], {"question_id": 3, "index": 2})
        self.assertEqual(set(row), {"event", "session_id", "client_ts", "app_version", "props"})

    def test_sink_sends_and_swallows_errors(self):
        sent = []

        class R:
            def close(self):
                pass

        events.set_sink(supabase_sink.make_sink(self.CFG, lambda req, timeout: sent.append(req) or R(), background=False))
        try:
            events.track("s", "test_start")
            self.assertEqual(len(sent), 1)

            def boom(req, timeout):
                raise OSError("down")
            events.set_sink(supabase_sink.make_sink(self.CFG, boom, background=False))
            events.track("s", "test_start")  # 예외 전파 없음
        finally:
            events.set_sink(None)


if __name__ == "__main__":
    unittest.main()
