# CARD DNA 이벤트 스키마

공통 필드: `event`, `session_id`(테스트 시작마다 새로 발급), `ts`(epoch초). 정의: `logic/events.py`의 `SCHEMA`.

| event | 발생 시점 | 속성 |
|---|---|---|
| test_start | 첫 문항 진입(1회) | - |
| question_view | 문항 최초 노출(문항당 1회) | question_id, index |
| answer_select | 선택지 클릭 시(선택 즉시 다음 문항으로 이동. 이전 답과 같으면 미기록) | question_id, option_id, changed(수정 여부), elapsed_ms, timed_out |
| question_next | 선택지 클릭으로 다음 문항/결과로 이동할 때 | question_id, elapsed_ms, timed_out |
| result_view | 결과 최초 노출(1회) | character_id, second_id, total_elapsed_ms |
| recommendation_click | 선호 혜택 버튼 클릭 | character_id, benefit |
| feedback_submit | 결과 공감도 제출(세션당 첫 응답 1회) | character_id, rating (`very_similar` 😍 / `somewhat` 🙂 / `different` 🤔) |

## 수집 방법
- 기본: 메모리 버퍼(`events.BUFFER`)만 사용. 설정이 없으면 외부 전송 없음.
- 로컬 분석: `CARD_DNA_EVENT_LOG=events.jsonl streamlit run app.py` → JSON Lines 기록.
- Supabase: `logic/supabase_sink.py`가 설정이 있을 때만 활성화(아래 설정 방법). 전송 실패는 앱에 영향 없음(3초 타임아웃, 백그라운드 스레드).

## Supabase 설정
1. [supabase.com](https://supabase.com)에서 프로젝트 생성 → SQL Editor에서 `docs/supabase_schema.sql` 실행(테이블·RLS·분석 뷰 생성).
2. Project Settings → API에서 **Project URL**과 **anon public key** 확인. (`service_role` 키는 앱에 절대 넣지 말 것)
3. 로컬: `.streamlit/secrets.toml` (gitignore됨)
   ```toml
   [supabase]
   url = "https://<project-ref>.supabase.co"
   anon_key = "<anon public key>"
   ```
   Streamlit Community Cloud: 앱 Settings → Secrets에 같은 내용을 붙여넣기.
4. 확인: 테스트 1회 진행 후 Table Editor → `events`에 행이 쌓이는지 확인.

익명성: 저장되는 값은 랜덤 session_id, 이벤트명, 문항/선택/캐릭터 ID, 경과 시간뿐. 이름·IP·이메일·기기 정보 없음.
anon 키는 INSERT만 허용(RLS)하므로 키가 노출되어도 데이터를 읽거나 지울 수 없음(스팸 삽입은 가능 → 필요 시 Supabase 속도 제한/주기적 정리).

## 지표 → 분석 뷰 (`docs/supabase_schema.sql`)
| 지표 | 뷰 / 계산 |
|---|---|
| 테스트 시작률 | 시작 수 = `v_funnel.started`. 분모(홈 방문)는 앱에 방문 이벤트가 없어 Streamlit Cloud 방문 통계 등 외부 값 사용 |
| 완료율 | `v_funnel.completion_pct` |
| 문항별 이탈률 | `v_question_dropoff.dropoff_pct`, 소요시간·타임아웃은 `v_question_timing` |
| 캐릭터 분포 | `v_character_dist` |
| 추천 혜택 반응률 | `v_reco_ctr` (캐릭터별), 혜택별 클릭은 `props->>'benefit'` 집계 |
| 결과 공감도 | `feedback_submit`의 `props->>'rating'` |
