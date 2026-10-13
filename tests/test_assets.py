import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent


class AssetsTest(unittest.TestCase):
    def test_referenced_images_exist(self):
        qs = json.loads((ROOT / "data/questions.json").read_text(encoding="utf-8"))
        cs = json.loads((ROOT / "data/characters.json").read_text(encoding="utf-8"))
        paths = ["assets/cover.png"] + [q["scene"] for q in qs] + [c["image"] for c in cs]
        for p in paths:
            f = ROOT / p
            self.assertTrue(f.is_file() and f.stat().st_size > 1000, p)
        self.assertEqual(len(set(paths)), 19)


if __name__ == "__main__":
    unittest.main()
