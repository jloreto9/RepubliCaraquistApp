-- scripts/sql/elo_tables.sql
-- Tablas para ELO por temporada y fase

create table if not exists public.elo_ratings (
  season integer not null,
  phase text not null,
  team_id integer not null,
  elo numeric(8,2) not null default 1500,
  games_played integer not null default 0,
  last_game_id bigint,
  game_datetime timestamptz,
  updated_at timestamptz not null default now(),
  constraint elo_ratings_pkey primary key (season, phase, team_id)
);

create table if not exists public.elo_game_log (
  season integer not null,
  phase text not null,
  game_id bigint not null,
  game_datetime timestamptz,
  home_team_id integer not null,
  away_team_id integer not null,
  home_score integer,
  away_score integer,
  home_elo_before numeric(8,2),
  away_elo_before numeric(8,2),
  home_elo_after numeric(8,2),
  away_elo_after numeric(8,2),
  k_value integer,
  home_advantage integer,
  updated_at timestamptz not null default now(),
  constraint elo_game_log_pkey primary key (season, phase, game_id)
);

create index if not exists idx_elo_ratings_season_phase
  on public.elo_ratings (season, phase);

create index if not exists idx_elo_ratings_season_phase_game_datetime
  on public.elo_ratings (season, phase, game_datetime);

create index if not exists idx_elo_game_log_season_phase
  on public.elo_game_log (season, phase);

create index if not exists idx_elo_game_log_season_phase_game_datetime
  on public.elo_game_log (season, phase, game_datetime);
