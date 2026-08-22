-- scripts/sql/spray_chart_tables.sql
-- Tabla para almacenar los contactos y coordenadas de Spray Charts

CREATE TABLE IF NOT EXISTS public.batted_balls (
    id BIGSERIAL PRIMARY KEY,
    game_pk BIGINT NOT NULL,
    game_date DATE NOT NULL,
    inning INT,
    half VARCHAR(10),
    season INT NOT NULL,
    team_id BIGINT,
    batter_id BIGINT NOT NULL,
    batter_name VARCHAR(150),
    bat_side VARCHAR(5),
    pitcher_id BIGINT,
    pitcher_name VARCHAR(150),
    pitch_hand VARCHAR(5),
    opposing_team VARCHAR(150),
    is_leones BOOLEAN DEFAULT false,
    event VARCHAR(50),
    event_group VARCHAR(50),
    is_hit BOOLEAN DEFAULT false,
    coord_x NUMERIC(8,2),
    coord_y NUMERIC(8,2),
    x_ft NUMERIC(8,2),
    y_ft NUMERIC(8,2),
    distance_ft NUMERIC(8,2),
    spray_angle NUMERIC(8,2),
    direction VARCHAR(50),
    trajectory VARCHAR(50),
    hardness VARCHAR(50),
    launch_speed NUMERIC(6,2),
    total_distance NUMERIC(6,2),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Índices para consultas ultra rápidas por jugador y temporada
CREATE INDEX IF NOT EXISTS idx_batted_balls_season ON public.batted_balls(season);
CREATE INDEX IF NOT EXISTS idx_batted_balls_batter ON public.batted_balls(batter_id);
CREATE INDEX IF NOT EXISTS idx_batted_balls_team ON public.batted_balls(team_id);
CREATE INDEX IF NOT EXISTS idx_batted_balls_game ON public.batted_balls(game_pk);
