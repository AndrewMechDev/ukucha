-- Esquema de persistencia UKUCHA (Fase 5). Ejecutar en el SQL editor de
-- Supabase (Dashboard -> SQL Editor -> New query) antes de configurar
-- SUPABASE_URL / SUPABASE_KEY en el backend. Sin esto, el backend usa
-- NullPersistenceAdapter automaticamente y sigue funcionando igual, solo
-- que no persiste nada -- ver backend/app.py::_build_persistence_backend.

-- eventos de deteccion relevantes (transiciones de alerta), con GPS
create table if not exists detection_events (
    id bigint generated always as identity primary key,
    tipo text not null,                 -- caida_detectada | caida_critica | persona_bajo_escombros
    frame_id bigint,
    detalle text,
    gps jsonb,                          -- {"lat":..,"lon":..,"fix":..,"sats":..} o null si no habia fix
    event_timestamp timestamptz not null,
    created_at timestamptz not null default now()
);

-- historico completo de audio_sensors / env_and_actuation (cada paquete)
create table if not exists telemetry_history (
    id bigint generated always as identity primary key,
    kind text not null,                 -- audio_sensors | env_and_actuation
    node_id text not null,
    timestamp_ms bigint not null,
    data jsonb not null,
    created_at timestamptz not null default now()
);

-- auditoria de comandos enviados hacia el robot (control remoto)
create table if not exists command_log (
    id bigint generated always as identity primary key,
    cmd_id bigint not null,
    command text not null,
    target_node text not null,
    params jsonb,
    event text not null,                -- sent | ack | timeout
    status text,                        -- status del ack ('ok'|'error'), null si no aplica
    created_at timestamptz not null default now()
);

create index if not exists idx_telemetry_history_kind_ts on telemetry_history (kind, timestamp_ms);
create index if not exists idx_command_log_cmd_id on command_log (cmd_id);
create index if not exists idx_detection_events_tipo_ts on detection_events (tipo, event_timestamp);
