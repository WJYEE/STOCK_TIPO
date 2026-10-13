import json
import unittest
from collections import Counter
from itertools import product
from pathlib import Path

from logic.scoring import answer_seed, calculate_scores, classify, rank

D = Path(__file__).parent.parent / "data"
QS = json.loads((D / "questions.json").read_text(encoding="utf-8"))
IDS = [c["id"] for c in json.loads((D / "characters.json").read_text(encoding="utf-8"))]
QIDS = [q["id"] for q in QS]


class ScoringTest(unittest.TestCase):
    def test_simple(self):
        q = [{"id": 1, "options": [{"id": "A", "scores": {"bear": 2}}]}]
        self.assertEqual(calculate_scores(q, {1: "A"}), {"bear": 2})
        self.assertEqual(classify({"bear": 2}, ["bear", "fox"]), "bear")

    def test_tie_is_deterministic_and_complete(self):
        tied = {"fox": 2, "bear": 2}
        self.assertEqual(rank(tied, IDS, "x"), rank(tied, IDS, "x"))
        self.assertEqual(sorted(rank(tied, IDS, "x")), sorted(IDS))
        self.assertEqual(set(rank(tied, IDS, "x")[:2]), {"fox", "bear"})  # 동점자가 상위
        self.assertEqual(rank({"cat": 4}, IDS)[0], "cat")
        self.assertEqual(len({classify(tied, IDS, str(i)) for i in range(50)}), 2)  # 쏠림 없음

    def test_data_valid(self):
        self.assertEqual(len(QS), 12)
        for q in QS:
            self.assertEqual(len(q["options"]), 4)
            for o in q["options"]:
                self.assertTrue(set(o["scores"]) <= set(IDS))

    def test_score_opportunity_balanced(self):
        slots = Counter(c for q in QS for o in q["options"] for c in o["scores"])
        self.assertEqual(set(slots.values()), {8})
        for q in QS:  # 한 문항에서 같은 캐릭터가 중복 노출되지 않음
            chars = [c for o in q["options"] for c in o["scores"]]
            self.assertEqual(len(chars), len(set(chars)))

    def test_characters_have_result_fields(self):
        for c in json.loads((D / "characters.json").read_text(encoding="utf-8")):
            for k in ("name", "quote", "desc", "memes", "benefits", "tip", "dna", "mate"):
                self.assertTrue(c[k], (c["id"], k))

    def test_every_character_reachable(self):
        for cid in IDS:
            ans = {}
            for q in QS:
                pick = next((o for o in q["options"] if cid in o["scores"]), q["options"][0])
                ans[q["id"]] = pick["id"]
            self.assertEqual(classify(calculate_scores(QS, ans), IDS, answer_seed(ans)), cid, cid)

    def test_random_answers_reach_all_and_fair(self):
        import random
        rnd, seen = random.Random(0), Counter()
        for _ in range(6000):
            ans = {q["id"]: rnd.choice(q["options"])["id"] for q in QS}
            seen[classify(calculate_scores(QS, ans), IDS, answer_seed(ans))] += 1
        self.assertEqual(set(seen), set(IDS))
        self.assertLess(max(seen.values()) / min(seen.values()), 1.5)  # 균형 설계 → 쏠림 제한

    def test_all_results_in_sampled_space(self):
        seen = {classify(calculate_scores(QS, dict(zip(QIDS, c))), IDS)
                for c in product("ABCD", repeat=4)}
        self.assertTrue(len(seen) >= 4)


if __name__ == "__main__":
    unittest.main()
