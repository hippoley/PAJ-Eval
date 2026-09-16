CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE sessions (
  session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  locale text NOT NULL,
  consent_version text NOT NULL,
  instrument_version text NOT NULL,
  assignment_id text,
  treatment_arm text,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','withdrawn'))
);

CREATE TABLE probe_runs (
  probe_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES sessions(session_id),
  probe_family text NOT NULL,
  world_variant text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  terminal_action text
);

CREATE TABLE events (
  event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES sessions(session_id),
  probe_run_id uuid REFERENCES probe_runs(probe_run_id),
  seq bigint NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  elapsed_ms bigint NOT NULL CHECK (elapsed_ms >= 0),
  event_type text NOT NULL,
  object_id text,
  payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE(session_id, seq)
);

CREATE TABLE derived_features (
  feature_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  probe_run_id uuid NOT NULL REFERENCES probe_runs(probe_run_id),
  extractor_version text NOT NULL,
  feature_name text NOT NULL,
  feature_value jsonb NOT NULL,
  evidence_event_ids uuid[] NOT NULL DEFAULT '{}'
);

CREATE TABLE evaluations (
  evaluation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES sessions(session_id),
  scoring_version text NOT NULL,
  construct text NOT NULL,
  estimate double precision,
  uncertainty double precision,
  evidence_feature_ids uuid[] NOT NULL DEFAULT '{}',
  validation_status text NOT NULL DEFAULT 'exploratory'
);

CREATE INDEX events_session_seq_idx ON events(session_id, seq);
CREATE INDEX probe_runs_session_idx ON probe_runs(session_id);
CREATE INDEX derived_features_run_idx ON derived_features(probe_run_id);
