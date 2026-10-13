"""Supabase 연결 진단: python scripts/check_supabase.py
.streamlit/secrets.toml 의 [supabase] 또는 환경변수 SUPABASE_URL / SUPABASE_ANON_KEY 를 읽어
테스트 행 1개(session_id='diagnostic_check')를 넣어 보고 HTTP 결과를 설명합니다."""
import json
import os
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from logic import supabase_sink  # noqa: E402

secrets = {}
f = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
if f.is_file():
    secrets = tomllib.loads(f.read_text(encoding="utf-8"))
else:
    print(f"- {f} 파일이 없어 환경변수를 사용합니다.")
cfg = supabase_sink.load_config(secrets)
if not cfg:
    sys.exit("설정 없음: secrets.toml 의 [supabase] url / anon_key (또는 SUPABASE_URL / SUPABASE_ANON_KEY) 를 확인하세요.")
url, key = cfg
print("URL:", url, "| 키 형식:", "JWT(eyJ…)" if key.startswith("eyJ") else key[:15] + "…")
if not url.startswith("https://") or ".supabase.co" not in url:
    print("! URL 형식이 이상해요. 'https://<project-ref>.supabase.co' 여야 합니다 (대시보드 주소 아님, /rest/v1 붙이지 않음).")
rec = {"event": "test_start", "session_id": "diagnostic_check", "ts": 0}
try:
    r = urllib.request.urlopen(supabase_sink.build_request(cfg, rec), timeout=10)
    print("HTTP", r.status, "→ 성공! Table Editor 의 events 에서 session_id=diagnostic_check 행을 확인하세요(확인 후 삭제 가능).")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", "replace")
    print("HTTP", e.code, body)
    hint = {
        404: "events 테이블이 없어요 → docs/supabase_schema.sql 을 SQL Editor에서 실행하세요 (또는 URL 오타).",
        401: "키가 잘못됐어요 → Project Settings > API 에서 anon/publishable 키를 다시 복사하세요 (service_role 아님).",
        403: "권한 없음 → RLS 정책 'anon insert only' 가 만들어졌는지 확인하세요 (schema.sql 실행).",
        400: "컬럼/체크 제약 불일치 → schema.sql 의 테이블 정의와 같은지 확인하세요.",
    }.get(e.code)
    if '42501' in body:
        hint = "RLS 정책 위반 → schema.sql 의 'create policy \"anon insert only\" ...' 를 실행하세요."
    print("→", hint or "응답 본문을 확인하세요.")
except Exception as e:
    print("연결 실패:", repr(e), "→ URL 철자/네트워크를 확인하세요.")
