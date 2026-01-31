# utils/ai_insights.py
"""
Módulo de Insights con IA para RepubliCaraquistApp.
Genera datos curiosos y análisis usando OpenAI API.
"""

import os
import streamlit as st
from openai import OpenAI
import pandas as pd


def build_insights_prompt(
    standings_df: pd.DataFrame = None,
    recent_games: pd.DataFrame = None,
    batting_stats: pd.DataFrame = None,
    pitching_stats: pd.DataFrame = None,
    advanced_stats: dict = None
) -> str:
    """
    Construye un prompt estructurado para generar insights basados en datos reales.

    Args:
        standings_df: DataFrame con standings de la liga
        recent_games: DataFrame con juegos recientes
        batting_stats: DataFrame con estadísticas de bateo
        pitching_stats: DataFrame con estadísticas de pitcheo
        advanced_stats: Dict con estadísticas avanzadas de Leones

    Returns:
        str: Prompt estructurado para OpenAI
    """
    prompt_parts = []

    prompt_parts.append("""Eres un analista deportivo experto en béisbol venezolano (LVBP),
especializado en los Leones del Caracas. Genera 3-4 datos curiosos, insights estadísticos
o análisis interesantes basados en los siguientes datos actuales.

Instrucciones:
- Usa un tono cercano y apasionado pero profesional
- Incluye comparaciones históricas o contexto cuando sea relevante
- Destaca tendencias positivas o áreas de mejora
- Menciona jugadores destacados por nombre
- Sé conciso pero informativo
- Usa emojis relacionados con béisbol ocasionalmente

Datos actuales:
""")

    # Standings
    if standings_df is not None and not standings_df.empty:
        leones = standings_df[standings_df['team_name'].str.contains('Leones', case=False, na=False)]
        if not leones.empty:
            leo = leones.iloc[0]
            position = standings_df.index.get_loc(leones.index[0]) + 1
            prompt_parts.append(f"""
## Posición en Standings
- Posición actual: {position}° lugar
- Récord: {leo.get('wins', 0)}-{leo.get('losses', 0)} ({leo.get('pct', 0):.3f})
- Racha: {leo.get('streak', 'N/A')}
- Diferencial de carreras: {leo.get('run_diff', 0):+d} (RF: {leo.get('runs_for', 0)}, RA: {leo.get('runs_against', 0)})
- Récord casa: {leo.get('home_record', 'N/A')}
- Récord visitante: {leo.get('away_record', 'N/A')}
- Últimos 10: {leo.get('last_10', 'N/A')}
""")

    # Juegos recientes
    if recent_games is not None and not recent_games.empty:
        games_info = []
        for _, game in recent_games.head(5).iterrows():
            is_home = game.get('home_team_id') == 695
            leones_score = game['home_score'] if is_home else game['away_score']
            opp_score = game['away_score'] if is_home else game['home_score']
            result = "Victoria" if leones_score > opp_score else "Derrota"

            if isinstance(game.get('away_team'), dict):
                rival = game['home_team'].get('name', 'Rival') if not is_home else game['away_team'].get('name', 'Rival')
            else:
                rival = "Rival"

            games_info.append(f"  - {result} vs {rival}: {leones_score}-{opp_score}")

        prompt_parts.append(f"""
## Últimos 5 juegos
{chr(10).join(games_info)}
""")

    # Estadísticas de bateo
    if batting_stats is not None and not batting_stats.empty:
        top_batters = batting_stats.head(5)
        batters_info = []
        for _, b in top_batters.iterrows():
            batters_info.append(f"  - {b['player_name']}: AVG {b['avg']:.3f}, OPS {b['ops']:.3f}, HR {b.get('hr', 0)}, RBI {b.get('rbi', 0)}")

        prompt_parts.append(f"""
## Líderes de Bateo (por OPS)
{chr(10).join(batters_info)}
""")

    # Estadísticas de pitcheo
    if pitching_stats is not None and not pitching_stats.empty:
        top_pitchers = pitching_stats.sort_values('era', ascending=True).head(5)
        pitchers_info = []
        for _, p in top_pitchers.iterrows():
            pitchers_info.append(f"  - {p['player_name']}: ERA {p['era']:.2f}, WHIP {p['whip']:.2f}, K {p.get('so', 0)}, IP {p.get('ip', 0):.1f}")

        prompt_parts.append(f"""
## Líderes de Pitcheo (por ERA)
{chr(10).join(pitchers_info)}
""")

    # Estadísticas avanzadas
    if advanced_stats:
        prompt_parts.append(f"""
## Estadísticas Avanzadas Leones
- Juegos totales: {advanced_stats.get('total_games', 'N/A')}
- Récord general: {advanced_stats.get('record', 'N/A')}
- En casa: {advanced_stats.get('home_record', 'N/A')}
- De visitante: {advanced_stats.get('away_record', 'N/A')}
- Juegos por 1 carrera: {advanced_stats.get('one_run', 'N/A')}
- Extra innings: {advanced_stats.get('extra_inning', 'N/A')}
- Blanqueos propinados: {advanced_stats.get('shutouts', 'N/A')}
- Racha actual: {advanced_stats.get('streak', 'N/A')}
- Octubre: {advanced_stats.get('oct', 'N/A')}
- Noviembre: {advanced_stats.get('nov', 'N/A')}
- Diciembre: {advanced_stats.get('dec', 'N/A')}
""")

    prompt_parts.append("""
Genera los insights en formato markdown con bullet points.
Cada insight debe ser breve (1-2 oraciones) pero interesante.""")

    return "\n".join(prompt_parts)


@st.cache_data(ttl=3600, show_spinner=False)
def get_ai_insights(
    standings_df: pd.DataFrame = None,
    recent_games: pd.DataFrame = None,
    batting_stats: pd.DataFrame = None,
    pitching_stats: pd.DataFrame = None,
    advanced_stats: dict = None
) -> tuple[str, str]:
    """
    Genera insights usando OpenAI API.

    Returns:
        tuple: (insights_text, error_message)
               Si hay error, insights_text será None y error_message contendrá el mensaje.
               Si es exitoso, error_message será None.
    """
    # Verificar API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("OPENAI_API_KEY")
        except:
            pass

    if not api_key:
        return None, "No se encontró la API key de OpenAI. Configura OPENAI_API_KEY en las variables de entorno."

    # Verificar que hay datos
    has_data = any([
        standings_df is not None and not standings_df.empty,
        recent_games is not None and not recent_games.empty,
        batting_stats is not None and not batting_stats.empty,
        pitching_stats is not None and not pitching_stats.empty,
        advanced_stats is not None and len(advanced_stats) > 0
    ])

    if not has_data:
        return None, "No hay datos disponibles para generar insights."

    # Construir prompt
    prompt = build_insights_prompt(
        standings_df=standings_df,
        recent_games=recent_games,
        batting_stats=batting_stats,
        pitching_stats=pitching_stats,
        advanced_stats=advanced_stats
    )

    # Llamar a OpenAI
    try:
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un analista deportivo experto en béisbol venezolano, especializado en la LVBP y los Leones del Caracas."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=800,
            temperature=0.7
        )

        insights = response.choices[0].message.content.strip()
        return insights, None

    except Exception as e:
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            return None, "Error de autenticación con OpenAI. Verifica tu API key."
        elif "rate" in error_msg.lower():
            return None, "Límite de llamadas a la API alcanzado. Intenta más tarde."
        else:
            return None, f"Error al generar insights: {error_msg}"
