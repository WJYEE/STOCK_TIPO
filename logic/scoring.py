import hashlib
from collections import defaultdict


def _chosen(question, answers):
    return next((o for o in question["options"] if o["id"] == answers.get(question["id"])), None)


def calculate_scores(questions, answers):
    scores = defaultdict(int)
    for question in questions:
        opt = _chosen(question, answers)
        for character, points in (opt["scores"] if opt else {}).items():
            scores[character] += points
    return dict(scores)


def answer_seed(answers):
    return ",".join(f"{k}{v}" for k, v in sorted(answers.items()))


def rank(scores, character_ids, seed=""):
    """점수 내림차순. 동점은 응답 조합(seed)으로 만든 해시 순서로 결정:
    같은 응답이면 항상 같은 결과(재현성), 응답이 다르면 특정 캐릭터로 쏠리지 않음."""
    h = lambda c: hashlib.md5(f"{seed}|{c}".encode()).hexdigest()
    return sorted(character_ids, key=lambda c: (-scores.get(c, 0), h(c)))


def classify(scores, character_ids, seed=""):
    return rank(scores, character_ids, seed)[0]
