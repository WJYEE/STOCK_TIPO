"""Supabase(PostgREST) 익명 이벤트 전송. 설정이 없으면 아무것도 하지 않음(키를 만들어 쓰지 않음).

필요 설정(둘 중 하나): Streamlit secrets `[supabase] url, anon_key` 또는 환경변수 SUPABASE_URL, SUPABASE_ANON_KEY.
anon 키는 INSERT 전용 RLS 정책과 함께 쓸 것 (docs/supabase_schema.sql).
"""
import json
import os
import threading
import urllib.request

TABLE = "events"
APP_VERSION = "1.0"


def load_config(secrets=None):
    try:
        cfg = dict(secrets["supabase"]) if secrets is not None else {}
    except Exception:  # secrets 파일 없음/키 없음
        cfg = {}
    url = cfg.get("url") or os.environ.get("SUPABASE_URL")
    key = cfg.get("anon_key") or os.environ.get("SUPABASE_ANON_KEY")
    return (url.rstrip("/"), key) if url and key else None


def build_request(cfg, rec):
    url, key = cfg
    common = {"event", "session_id", "ts"}
    row = {
        "event": rec["event"],
        "session_id": rec["session_id"],
        "client_ts": rec["ts"],
        "app_version": APP_VERSION,
        "props": {k: v for k, v in rec.items() if k not in common},
    }
    return urllib.request.Request(
        f"{url}/rest/v1/{TABLE}", data=json.dumps(row).encode(), method="POST",
        headers={"apikey": key, "Authorization": f"Bearer {key}",
                 "Content-Type": "application/json", "Prefer": "return=minimal"})


def make_sink(cfg, opener=urllib.request.urlopen, background=True):
    def send(rec):
        try:
            opener(build_request(cfg, rec), timeout=3).close()
        except Exception:
            pass  # 로깅 실패가 앱을 막으면 안 됨 # ponytail: 재시도/큐 없음, 필요 시 배치 전송 추가

    def sink(rec):
        if background:
            threading.Thread(target=send, args=(rec,), daemon=True).start()
        else:
            send(rec)

    return sink
