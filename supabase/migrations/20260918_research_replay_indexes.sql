create index if not exists events_probe_run_seq_idx
  on public.events(probe_run_id, seq);

create index if not exists evaluations_session_id_idx
  on public.evaluations(session_id);
