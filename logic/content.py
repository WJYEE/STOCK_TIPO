"""캐릭터 데이터 정규화: 필드가 빠졌거나 예전 형식(benefits가 문자열 목록, dna/tip 없음)이어도 결과 화면이 깨지지 않게 함."""

DEFAULT_TIP = "소비 습관은 정답이 없어요. 한 달에 한 번, 내가 어디에 쓰는지만 돌아봐도 충분해요."


def normalize_character(c):
    c = dict(c)
    c.setdefault("emoji", "🐾")
    c.setdefault("color", "#F4EEE5")
    c.setdefault("trait", "")
    c.setdefault("quote", "")
    c.setdefault("desc", "")
    c.setdefault("name", c.get("id", ""))
    # 예전 형식의 혜택(문자열)도 카드 형식으로 변환
    c["benefits"] = [b if isinstance(b, dict) else {"icon": "🎁", "name": str(b), "desc": ""}
                     for b in c.get("benefits", [])]
    for b in c["benefits"]:
        b.setdefault("icon", "🎁")
        b.setdefault("desc", "")
    # 소비 DNA: 없으면 기존 밈 문구(memes)로 대체
    if not c.get("dna"):
        c["dna"] = [{"emoji": "💬", "text": m} for m in c.get("memes", [])[:4]]
    if not c.get("tip"):
        habits = c.get("cautions") or []
        c["tip"] = ("이런 점을 가볍게 살펴보면 좋아요: " + ", ".join(habits) + ".") if habits else DEFAULT_TIP
    c.setdefault("mate", "")
    return c
