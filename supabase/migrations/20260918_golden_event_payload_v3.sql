create or replace function public.ingest_probe_atomic(
  p_submission uuid,
  p_locale text,
  p_instrument text,
  p_family text,
  p_world text,
  p_terminal text,
  p_events jsonb
)
returns table(session_id uuid, duplicate boolean, event_count integer)
language plpgsql
security invoker
set search_path = public
as $$
declare
  v_session_id uuid;
  v_probe_run_id uuid;
  v_count integer := jsonb_array_length(p_events);
begin
  insert into public.sessions(
    client_submission_id, locale, consent_version, instrument_version,
    status, completed_at, client_schema_version
  ) values (
    p_submission, p_locale, 'v1', p_instrument,
    'completed', now(), 'v2-rich-events'
  )
  on conflict (client_submission_id) where client_submission_id is not null
  do nothing
  returning sessions.session_id into v_session_id;

  if v_session_id is null then
    select s.session_id into v_session_id
    from public.sessions s
    where s.client_submission_id = p_submission;

    return query select v_session_id, true, v_count;
    return;
  end if;

  insert into public.probe_runs(
    session_id, probe_family, world_variant, terminal_action, completed_at
  ) values (
    v_session_id, p_family, p_world, nullif(p_terminal,''), now()
  ) returning probe_run_id into v_probe_run_id;

  insert into public.events(
    session_id, probe_run_id, seq, elapsed_ms, event_type, object_id, payload_json
  )
  select
    v_session_id,
    v_probe_run_id,
    x.ord::bigint,
    least(86400000::bigint, greatest(0::bigint, coalesce((x.e->>'t')::bigint, 0))),
    left(coalesce(nullif(x.e->>'event',''),'unknown'),80),
    nullif(left(coalesce(x.e->>'target',''),160),''),
    (
      x.e - 'event' - 'target' - 't' - 'seq'
    ) || jsonb_build_object(
      'client_seq', coalesce(
        case when coalesce(x.e->>'client_seq','') ~ '^[0-9]+$' then (x.e->>'client_seq')::bigint end,
        case when coalesce(x.e->>'seq','') ~ '^[0-9]+$' then (x.e->>'seq')::bigint end,
        x.ord::bigint
      ),
      'locale', coalesce(nullif(left(coalesce(x.e->>'locale',''),16),''), p_locale)
    )
  from jsonb_array_elements(p_events) with ordinality as x(e,ord);

  return query select v_session_id, false, v_count;
end;
$$;

revoke all on function public.ingest_probe_atomic(uuid,text,text,text,text,text,jsonb) from public, anon, authenticated;
grant execute on function public.ingest_probe_atomic(uuid,text,text,text,text,text,jsonb) to service_role;
