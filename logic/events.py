"""이벤트 로깅 인터페이스. MVP는 DB 없이 메모리 버퍼 + 교체 가능한 sink만 제공.

sink 교체 예: events.set_sink(lambda e: bigquery_client.insert_rows_json(table, [e]))
환경변수 CARD_DNA_EVENT_LOG=경로 를 주면 JSON Lines 파일로도 기록(로컬 분석용).
"""
import json
import os
import time
import uuid

# 이벤트명 -> 필수 속성. 공통 필드(event, session_id, ts)는 track()이 채움.
SCHEMA = {
    "test_start": [],
    "question_view": ["question_id", "index"],
    "answer_select": ["question_id", "option_id", "changed", "elapsed_ms", "timed_out"],
    "question_next": ["question_id", "elapsed_ms", "timed_out"],
    "result_view": ["character_id", "second_id", "total_elapsed_ms"],
    "recommendation_click": ["character_id", "benefit"],
    "feedback_submit": ["character_id", "rating"],
}

_sink = None
BUFFER = []


def set_sink(fn):
    global _sink
    _sink = fn


def new_session_id():
    return uuid.uuid4().hex[:12]


def track(session_id, event, **props):
    missing = [k for k in SCHEMA[event] if k not in props]  # 알 수 없는 이벤트는 KeyError
    if missing:
        raise ValueError(f"{event}: missing {missing}")
    rec = {"event": event, "session_id": session_id, "ts": round(time.time(), 3), **props}
    BUFFER.append(rec)
    del BUFFER[:-1000]  # ponytail: 프로세스 메모리 상한, 실제 수집은 sink로
    if _sink:
        _sink(rec)
    path = os.environ.get("CARD_DNA_EVENT_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec
