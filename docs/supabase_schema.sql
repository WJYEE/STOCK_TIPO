-- CARD DNA 익명 이벤트 저장 (Supabase SQL Editor에서 실행)
create table if not exists public.events (
  id          bigint generated always as identity primary key,
  created_at  timestamptz not null default now(),
  event       text not null check (event in
    ('test_start','question_view','answer_select','question_next',
     'result_view','recommendation_click','feedback_submit')),
  session_id  text not null,          -- 테스트마다 새로 만드는 랜덤 ID. 사용자·기기 식별 정보 없음
  client_ts   double precision,
  app_version text,
  props       jsonb not null default '{}'::jsonb
);
create index on public.events (event, created_at);
create index on public.events (session_id);

-- 보안: 익명(anon) 키는 INSERT만 가능, 조회/수정/삭제 불가
alter table public.events enable row level security;
create policy "anon insert only" on public.events for insert to anon with check (true);
-- 분석은 대시보드 SQL Editor 또는 service_role(서버 전용, 앱에 넣지 말 것)로 수행

-- ===== 분석 뷰 =====
-- 세션별 요약
create or replace view public.v_sessions as
select session_id,
  min(created_at) as started_at,
  bool_or(event='test_start') as started,
  bool_or(event='result_view') as completed,
  max((props->>'index')::int) filter (where event='question_view') as last_question_index,
  max(props->>'character_id') filter (where event='result_view') as character_id,
  bool_or(event='recommendation_click') as clicked_reco,
  bool_or(event='feedback_submit') as gave_feedback
from public.events group by session_id;

-- 시작 대비 완료율 (홈 방문 로깅은 없으므로 '시작률'은 외부 방문 수 대비로 별도 산출)
create or replace view public.v_funnel as
select count(*) filter (where started) as started,
       count(*) filter (where completed) as completed,
       round(100.0*count(*) filter (where completed)/nullif(count(*) filter (where started),0),1) as completion_pct
from public.v_sessions;

-- 문항별 도달·이탈 (도달 = question_view, 이탈 = 도달 후 다음 문항/결과로 못 간 세션)
create or replace view public.v_question_dropoff as
with v as (select (props->>'question_id')::int q, count(distinct session_id) viewed
           from public.events where event='question_view' group by 1),
     n as (select (props->>'question_id')::int q, count(distinct session_id) moved
           from public.events where event='question_next' group by 1)
select v.q as question_id, v.viewed, coalesce(n.moved,0) as moved,
       round(100.0*(v.viewed-coalesce(n.moved,0))/v.viewed,1) as dropoff_pct
from v left join n using (q) order by v.q;

-- 문항별 응답 시간·타임아웃 비율
create or replace view public.v_question_timing as
select (props->>'question_id')::int as question_id,
  round(avg((props->>'elapsed_ms')::numeric)/1000,1) as avg_sec,
  round(100.0*avg(((props->>'timed_out')::boolean)::int),1) as timed_out_pct
from public.events where event='question_next' group by 1 order by 1;

-- 캐릭터 분포
create or replace view public.v_character_dist as
select props->>'character_id' as character_id, count(distinct session_id) as sessions,
       round(100.0*count(distinct session_id)/sum(count(distinct session_id)) over (),1) as pct
from public.events where event='result_view' group by 1 order by 2 desc;

-- 추천 혜택 반응률 (결과를 본 세션 중 혜택을 클릭한 비율, 캐릭터별)
create or replace view public.v_reco_ctr as
select s.character_id, count(*) as result_sessions,
       count(*) filter (where s.clicked_reco) as clicked,
       round(100.0*count(*) filter (where s.clicked_reco)/count(*),1) as ctr_pct
from public.v_sessions s where s.completed group by 1 order by 4 desc;

-- ===== 결과 피드백 (rating 코드: very_similar / somewhat / different) =====
-- props(jsonb)에 저장하므로 기존 테이블 변경 불필요. 신규 설치/기존 DB 모두 아래만 실행하면 됨.
create or replace view public.v_feedback_dist as
select props->>'character_id' as character_id, props->>'rating' as rating, count(distinct session_id) as sessions
from public.events where event='feedback_submit' group by 1,2 order by 1,3 desc;

-- (선택) 세션당 피드백/결과 1건만 저장해 중복 집계 방지. 기존 중복 행이 있으면 먼저 정리 후 실행.
create unique index if not exists events_one_feedback_per_session
  on public.events (session_id) where event = 'feedback_submit';
create unique index if not exists events_one_result_per_session
  on public.events (session_id) where event = 'result_view';
