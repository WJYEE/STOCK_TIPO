import base64
import io
import json
import random
import time
from pathlib import Path

import streamlit as st

from logic import events, supabase_sink
from logic.content import normalize_character
from logic.scoring import answer_seed, calculate_scores, rank

ROOT = Path(__file__).parent
TIME_LIMIT = 10
DISCLAIMER = "재미로 보는 오락용 성향 테스트예요. 정답은 없으며, 특정 금융상품의 추천·권유가 아닙니다."

st.set_page_config(page_title="CARD DNA", page_icon="🐾", layout="centered")

CSS = """
<style>
#MainMenu, footer, header {visibility:hidden;}
.block-container {max-width:420px; padding:1rem 1rem 3rem;}
:root {--ink:#5A4636; --card:#FFFFFF;}
.sz-logo {text-align:center; font-weight:900; font-size:2.2rem; line-height:1.1; color:var(--ink); letter-spacing:1px;}
.sz-hero {display:flex; flex-direction:column; align-items:center; gap:14px; margin-bottom:.4rem;}
.sz-hero > * {margin:0;}
.sz-hero .sz-card {width:100%; box-sizing:border-box; text-align:center;}
.sz-card h2 {margin:0 0 .4rem; padding:0; font-size:clamp(1.25rem, 5.6vw, 1.5rem); line-height:1.3;
  word-break:keep-all; text-wrap:balance;}
.sz-card p {margin:0; font-size:.95rem; line-height:1.55; word-break:keep-all; text-wrap:balance;}
.sz-tags {display:flex; flex-wrap:wrap; justify-content:center; gap:6px;}
.sz-img {display:block; margin:0 auto; max-width:100%; height:auto; border-radius:18px;}
.sz-card {background:var(--card); border:3px solid var(--ink); border-radius:22px;
  box-shadow:0 5px 0 var(--ink); padding:1rem 1.1rem; margin:.6rem 0; color:var(--ink);}
.sz-scene {text-align:center; border:3px solid var(--ink); border-radius:22px; padding:1rem 0;
  box-shadow:0 5px 0 var(--ink); margin:.4rem 0 .8rem;}
.sz-big {font-size:4.5rem; line-height:1.1;}
.sz-q {font-size:1.25rem; font-weight:800; color:var(--ink); margin:.4rem 0 .6rem; word-break:keep-all;}
.sz-timer {margin-top:.5rem; text-align:center; font-weight:800; border:3px solid var(--ink); border-radius:999px;
  padding:.25rem .8rem; background:#E6F5EC; color:var(--ink);}
.sz-timer.up {background:#FFD9D9;}
.sz-meme {background:#FFF3C4; border:3px dashed var(--ink); border-radius:16px; padding:.6rem .9rem;
  margin:.4rem 0; font-weight:700; color:var(--ink);}
.sz-tag {display:inline-block; background:#fff; border:2px solid var(--ink); border-radius:999px;
  padding:.1rem .6rem; font-size:.78rem; font-weight:700; color:var(--ink); white-space:nowrap;}
/* 카드형 버튼(선택지/혜택/피드백): 실제 st.button 위젯. 키 접두사(st-key-*)로 선택 상태를 구분 */
[class*="st-key-opt_"] button, [class*="st-key-sel_"] button, [class*="st-key-reco"] button,
[class*="st-key-fb"] button {width:100%; background:#fff; color:#5A4636; border:3px solid #5A4636;
  border-radius:16px; box-shadow:0 3px 0 #5A4636; padding:.6rem .6rem;}
[class*="st-key-opt_"] button, [class*="st-key-sel_"] button {min-height:118px !important; height:100%;}
[class*="st-key-reco"] button {min-height:76px; justify-content:flex-start; text-align:left;}
[class*="st-key-fb"] button {min-height:84px;}
[class*="st-key-opt_"] button p, [class*="st-key-sel_"] button p, [class*="st-key-reco"] button p,
[class*="st-key-fb"] button p {margin:0; font-size:.92rem; line-height:1.4; font-weight:700; white-space:normal;
  word-break:keep-all; overflow-wrap:anywhere;}
[class*="st-key-sel_"] button, [class*="st-key-recsel"] button, [class*="st-key-fbsel"] button {
  background:#D9F0E5; border-color:#2F8F6B; box-shadow:0 3px 0 #2F8F6B;}
.rs-title {text-align:center; font-weight:900; font-size:1.2rem; color:var(--ink); margin:.8rem 0 .1rem;}
.rs-sub {text-align:center; font-size:.85rem; color:#8a7766; margin:0 0 .2rem;}
.rs-main {border:3px solid var(--ink); border-radius:26px; box-shadow:0 5px 0 var(--ink); padding:1.1rem 1rem 1.3rem;
  text-align:center; color:var(--ink); box-sizing:border-box;}
.rs-kicker {font-weight:900; letter-spacing:2px; font-size:.85rem; margin-bottom:.6rem;}
.rs-main .sz-img {margin-bottom:.8rem;}
.rs-name {font-size:1.7rem; font-weight:900; line-height:1.2; margin:.2rem 0 .4rem; word-break:keep-all;}
.rs-quote {font-size:1.3rem; font-weight:800; line-height:1.4; margin:.7rem 0; word-break:keep-all; text-wrap:balance;}
.rs-main p {font-size:.95rem; line-height:1.6; margin:0; word-break:keep-all; text-wrap:balance;}
.rs-grid {display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:10px;}
.rs-dna {min-height:100px; box-sizing:border-box; display:flex; flex-direction:column; align-items:center;
  justify-content:center; gap:6px; text-align:center; padding:.7rem .6rem; background:#fff; color:var(--ink);
  border:3px solid var(--ink); border-radius:16px; box-shadow:0 3px 0 var(--ink); font-size:.9rem; font-weight:700;
  line-height:1.4; word-break:keep-all; overflow-wrap:anywhere;}
.rs-dna b {font-size:1.6rem; line-height:1;}
.rs-box {background:#fff; border:3px solid var(--ink); border-radius:18px; box-shadow:0 3px 0 var(--ink);
  padding:.8rem .9rem; color:var(--ink); box-sizing:border-box;}
.rs-row {display:flex; justify-content:space-between; gap:8px; font-weight:800; font-size:.92rem; margin-bottom:4px;}
.rs-track {height:14px; background:#EFE6D8; border-radius:999px; overflow:hidden; margin-bottom:.7rem;}
.rs-fill {height:100%; border-radius:999px; border-right:2px solid var(--ink);}
.rs-tip {background:#FFF3C4; border:3px dashed var(--ink); border-radius:18px; padding:.9rem 1rem; color:var(--ink);
  font-size:.95rem; line-height:1.65; word-break:keep-all; box-sizing:border-box;}
.rs-note {text-align:center; font-size:.8rem; color:#8a7766; margin:.1rem 0 .4rem;}
/* 좁은 화면에서도 이전/다음 버튼을 같은 너비의 한 줄로 유지 */
div[data-testid="stHorizontalBlock"] {flex-wrap:nowrap !important; gap:.6rem;}
div[data-testid="stColumn"] {min-width:0 !important; flex:1 1 0 !important;}
div.stButton > button {border:3px solid #5A4636; border-radius:16px; font-weight:800; min-height:3rem;
  box-shadow:0 4px 0 #5A4636;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data
def load(mtime):
    """mtime을 캐시 키에 포함 → JSON을 수정하면 실행 중인 서버에서도 새 데이터를 읽음."""
    qs = json.loads((ROOT / "data/questions.json").read_text(encoding="utf-8"))
    cs = json.loads((ROOT / "data/characters.json").read_text(encoding="utf-8"))
    return qs, [normalize_character(c) for c in cs]


@st.cache_resource
def setup_logging():
    cfg = supabase_sink.load_config(st.secrets)
    if cfg:
        events.set_sink(supabase_sink.make_sink(cfg))
    return bool(cfg)


setup_logging()
questions, characters = load(tuple((ROOT / f"data/{n}.json").stat().st_mtime for n in ("questions", "characters")))
char_map = {c["id"]: c for c in characters}
ids = [c["id"] for c in characters]

ss = st.session_state
ss.setdefault("page", "home")
ss.setdefault("index", 0)
ss.setdefault("answers", {})
ss.setdefault("started", {})  # 문항 index -> 최초 진입 시각 (선택/rerun에도 유지)
ss.setdefault("sid", events.new_session_id())
ss.setdefault("reco", set())  # 클릭한 혜택(강조 표시용)
ss.setdefault("fb", None)  # 피드백 응답(세션당 첫 응답만 기록)
ss.setdefault("seen", set())  # 중복 로깅 방지: rerun마다 이벤트가 쌓이지 않게


def log(event, **props):
    events.track(ss.sid, event, **props)


def log_once(key, event, **props):
    if key not in ss.seen:
        ss.seen.add(key)
        log(event, **props)


def go(page, index=None, reset=False):
    ss.page = page
    if index is not None:
        ss.index = index
    if reset:
        ss.answers, ss.started, ss.seen, ss.reco, ss.fb = {}, {}, set(), set(), None
        ss.sid = events.new_session_id()
    st.rerun()


@st.cache_data
def img_uri(path, max_w):
    """이미지를 data URI로 변환(표시 폭의 2배보다 크면 축소). 원본 파일은 변경하지 않음."""
    from PIL import Image
    im = Image.open(ROOT / path)
    if im.width > max_w * 2:
        im = im.resize((max_w * 2, round(im.height * max_w * 2 / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def art_html(path, emoji, color, max_w=None):
    """이미지 HTML. 파일이 없거나 열 수 없을 때만 이모지 플레이스홀더."""
    try:
        w = max_w or 420
        style = f' style="max-width:{w}px"' if max_w else ""
        return f'<img class="sz-img" src="{img_uri(path, w)}" alt=""{style}>'
    except Exception:
        return f'<div class="sz-scene" style="background:{color}"><div class="sz-big">{emoji}</div></div>'


def art(path, emoji, color, max_w=None):
    st.markdown(art_html(path, emoji, color, max_w), unsafe_allow_html=True)


@st.fragment(run_every=1)
def timer(start):
    left = TIME_LIMIT - (time.time() - start)
    if left > 0:
        st.markdown(f'<div class="sz-timer">⏱️ {int(left) + 1}초</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="sz-timer up">⏰ TIME UP! 괜찮아, 천천히 골라도 돼요 🐾</div>',
                    unsafe_allow_html=True)


def home():
    tags = "".join(f'<span class="sz-tag">{c["emoji"]} {c["name"]}</span>' for c in characters)
    st.markdown(
        f'<div class="sz-hero">{art_html("assets/cover.png", "💳🐱", "#FFFFFF", 260)}'
        '<div class="sz-logo">CARD DNA</div>'
        '<div class="sz-card"><h2>당신의 지갑에는 어떤 동물이 살고 있나요?</h2>'
        '<p>12개 결제 상황, 문항당 10초!<br>정답은 없어요. 나의 소비·결제 DNA를 찾아보세요.</p></div>'
        f'<div class="sz-tags">{tags}</div></div>', unsafe_allow_html=True)
    if st.button("테스트 시작 🚀", use_container_width=True, type="primary"):
        go("quiz", 0, reset=True)
    st.caption(DISCLAIMER)


def quiz():
    idx = ss.index
    q = questions[idx]
    actor = char_map.get(q["actor"], characters[0])
    start = ss.started.setdefault(idx, time.time())
    if not ss.started.get("t0"):
        ss.started["t0"] = start
        log("test_start")
    log_once(("view", idx), "question_view", question_id=q["id"], index=idx)
    elapsed = lambda: int((time.time() - start) * 1000)
    st.progress((idx + 1) / len(questions), text=f"Q{idx + 1} / {len(questions)}")
    art(q["scene"], actor["emoji"], actor["color"])
    timer(start)
    st.markdown(f'<div class="sz-q">{q["title"]}</div>', unsafe_allow_html=True)
    # 선택지 순서는 문항별 고정 시드로 섞어 위치 편향을 줄임 (재현 가능)
    opts = random.Random(q["id"]).sample(q["options"], len(q["options"]))
    prior = ss.answers.get(q["id"])
    last = idx == len(questions) - 1
    clicked = None
    for row in (opts[:2], opts[2:]):
        for col, o in zip(st.columns(2), row):
            mark = "✓ " if o["id"] == prior else ""
            label = f'{mark}{"ABCD"[opts.index(o)]}. {o["text"]}'
            if col.button(label, key=f'{"sel" if o["id"] == prior else "opt"}_{o["id"]}', use_container_width=True):
                clicked = o["id"]
    if clicked:  # 선택 즉시 다음 문항(마지막이면 결과)으로 이동. 타이머 종료 후에도 동일
        if clicked != prior:
            log("answer_select", question_id=q["id"], option_id=clicked, changed=prior is not None,
                elapsed_ms=elapsed(), timed_out=elapsed() > TIME_LIMIT * 1000)
        ss.answers[q["id"]] = clicked
        log("question_next", question_id=q["id"], elapsed_ms=elapsed(), timed_out=elapsed() > TIME_LIMIT * 1000)
        go("result") if last else go("quiz", idx + 1)
    if idx > 0 and st.button("← 이전", key="prev", use_container_width=True):
        go("quiz", idx - 1)


FB = {"very_similar": "😍 완전 나야!", "somewhat": "🙂 어느 정도 맞아", "different": "🤔 조금 달라"}


def result():
    scores = calculate_scores(questions, ss.answers)
    order = rank(scores, ids, answer_seed(ss.answers))
    c, second = char_map[order[0]], char_map[order[1]]
    log_once("result", "result_view", character_id=c["id"], second_id=second["id"],
             total_elapsed_ms=int((time.time() - ss.started.get("t0", time.time())) * 1000))
    st.markdown(
        f'<div class="rs-main" style="background:{c["color"]}"><div class="rs-kicker">MY CARD DNA</div>'
        f'{art_html(c["image"], c["emoji"], c["color"], 260)}'
        f'<div class="rs-name">{c["name"]}</div><span class="sz-tag">{c["trait"]}</span>'
        f'<div class="rs-quote">“{c["quote"]}”</div><p>{c["desc"]}</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="rs-title">나의 소비 DNA</div>', unsafe_allow_html=True)
    st.markdown('<div class="rs-grid">' + "".join(
        f'<div class="rs-dna"><b>{d["emoji"]}</b>{d["text"]}</div>' for d in c["dna"]) + "</div>", unsafe_allow_html=True)

    st.markdown('<div class="rs-title">추천 카드 혜택</div><div class="rs-sub">눌러서 관심 표시를 해보세요</div>',
                unsafe_allow_html=True)
    for i, b in enumerate(c["benefits"]):
        on = b["name"] in ss.reco
        if st.button(f'{"✓ " if on else ""}{b["icon"]} **{b["name"]}**  \n{b["desc"]}',
                     key=f'{"recsel" if on else "reco"}_{i}', use_container_width=True):
            ss.reco.add(b["name"])
            log_once(("reco", b["name"]), "recommendation_click", character_id=c["id"], benefit=b["name"])
            st.rerun()
    st.markdown('<div class="rs-note">※ 실제 금융상품이 아닌 가상의 혜택 예시예요.</div>', unsafe_allow_html=True)

    st.markdown('<div class="rs-title">숨겨진 카드 성향</div>'
                '<div class="rs-sub">내 답변에서 각 유형이 얻은 점수예요 (백분율 아님)</div>', unsafe_allow_html=True)
    rows = ""
    for cid in order[:3]:
        mx = sum(max(o["scores"].get(cid, 0) for o in qq["options"]) for qq in questions)
        ch, sc = char_map[cid], scores.get(cid, 0)
        rows += (f'<div class="rs-row"><span>{ch["emoji"]} {ch["name"]}</span><span>{sc} / {mx}점</span></div>'
                 f'<div class="rs-track"><div class="rs-fill" style="width:{100 * sc / mx:.0f}%;'
                 f'background:{ch["color"]}{";border:0" if not sc else ""}"></div></div>')
    st.markdown(f'<div class="rs-box">{rows}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="rs-title">💡 소비 TIP</div><div class="rs-tip">{c["tip"]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="rs-title">이 결과가 나와 얼마나 비슷한가요?</div>', unsafe_allow_html=True)
    for col, (code, label) in zip(st.columns(3), FB.items()):
        done = ss.fb is not None
        if col.button(label.replace(" ", "\n\n", 1), key=f'{"fbsel" if ss.fb == code else "fb"}_{code}',
                      disabled=done and ss.fb != code, use_container_width=True) and not done:
            ss.fb = code  # 세션당 첫 응답만 기록 → 반복 클릭해도 중복 이벤트 없음
            log("feedback_submit", character_id=c["id"], rating=code)
            st.rerun()
    if ss.fb:
        st.markdown('<div class="rs-note">의견 고마워요! 🐾</div>', unsafe_allow_html=True)

    st.markdown('<div class="rs-title">결과 공유하기</div><div class="rs-sub">아래 문구 오른쪽 위 아이콘으로 복사해요</div>',
                unsafe_allow_html=True)
    st.code(f"나는 {c['emoji']} {c['name']}! “{c['quote']}” - CARD DNA", language=None, wrap_lines=True)
    if st.button("다시 테스트하기 🔄", key="again", use_container_width=True, type="primary"):
        go("home", 0, reset=True)
    st.caption(DISCLAIMER)


{"home": home, "quiz": quiz, "result": result}.get(ss.page, home)()
