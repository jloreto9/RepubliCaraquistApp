"""
tests/test_pitching_streamlit.py
--------------------------------
Suite de pruebas unitarias y de integración para el módulo Pitching Summary,
motores sabermétricos y tarjetas Matchup 360 en RepubliCaraquistApp (Streamlit).

Valida:
1. Resolución de lanzadores (get_pitcher_by_id, search_pitchers) y directorio CARACAS_PITCHERS.
2. Generación de tarjeta panorámica Thomas Nestico (utils/pitching_card.py) para MLB y LVBP a 300 DPI (2400x1350).
3. Generación de tarjeta comparativa Matchup 360 (utils/matchup_card.py) a 300 DPI (1360px de ancho) con tipografía Unicode.
4. Mapeo de colores y paletas sabermétricas.
5. Compatibilidad de funciones en utils/supabase_client.py (fases, estadísticas colectivas).
"""

import io
import os
import sys
import unittest
import pandas as pd
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.pitching_engine import (
    get_pitcher_by_id,
    search_pitchers,
    _get_caracas_pitcher_ids,
    get_available_seasons,
    get_pitch_analysis_for_df,
)
from utils.pitching_card import (
    build_pitching_summary_card,
    _get_pitch_color,
    CANVAS_SIZE,
    CANVAS_SIZE_LVBP,
    DPI,
)
from utils.matchup_card import build_matchup_image
from utils.supabase_client import get_collective_team_stats


class TestPitchingEngineResolution(unittest.TestCase):
    """Verificación de resolución y búsqueda de lanzadores en utils/pitching_engine.py."""

    def test_caracas_pitchers_catalog(self):
        """El catálogo de IDs de lanzadores caraquistas debe contener entradas válidas."""
        ids = _get_caracas_pitcher_ids()
        self.assertIsInstance(ids, set)
        self.assertGreater(len(ids), 10)
        self.assertIn(612797, ids)  # Erick Leal
        self.assertIn(544150, ids)  # Albert Suárez

    def test_get_pitcher_by_id_erick_leal(self):
        """Resolución de Erick Leal (612797)."""
        pitcher = get_pitcher_by_id(612797)
        self.assertIsNotNone(pitcher)
        self.assertEqual(pitcher.get("id"), 612797)
        self.assertIn("Erick Leal", pitcher.get("name", ""))
        self.assertEqual(pitcher.get("throws"), "R")

    def test_get_pitcher_by_id_albert_suarez(self):
        """Resolución de Albert Suárez (544150)."""
        pitcher = get_pitcher_by_id(544150)
        self.assertIsNotNone(pitcher)
        self.assertEqual(pitcher.get("id"), 544150)
        self.assertIn("Albert Su", pitcher.get("name", ""))

    def test_search_pitchers(self):
        """Búsqueda por texto libre."""
        results = search_pitchers("Leal")
        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 1)
        found = any(p.get("id") == 612797 for p in results)
        self.assertTrue(found)

    def test_unknown_pitcher_fallback(self):
        """Lanzador inexistente en MLB API debe retornar estructura por defecto o None sin crashear."""
        pitcher = get_pitcher_by_id(99999999)
        if pitcher is not None:
            self.assertIn("id", pitcher)

    def test_available_seasons(self):
        """get_available_seasons debe retornar temporadas canónicas."""
        seasons = get_available_seasons()
        self.assertIn(2026, seasons)
        self.assertIn(2025, seasons)
        self.assertIn(2024, seasons)

    def test_pitch_analysis_for_df(self):
        """get_pitch_analysis_for_df debe resumir métricas Statcast de un DataFrame."""
        df_dummy = pd.DataFrame([
            {
                "pitch_name": "4-Seam Fastball", "release_speed": 95.0,
                "release_spin_rate": 2400, "pfx_x": 0.8, "pfx_z": 1.4,
                "whiff": True, "description": "swinging_strike", "in_zone": True,
                "plate_x": 0.0, "plate_z": 2.5
            }
        ])
        analysis = get_pitch_analysis_for_df(df_dummy)
        self.assertEqual(analysis["total_pitches"], 1)
        self.assertEqual(len(analysis["statcast_table"]), 1)
        self.assertEqual(analysis["pbp_kpis"]["whiff_pct"], "100.0%")


class TestPitchingCardHDGeneration(unittest.TestCase):
    """Pruebas del generador gráfico de tarjetas HD Thomas Nestico a 300 DPI."""

    def setUp(self):
        self.dummy_pitcher = {
            "name": "Albert Suárez",
            "throws": "R",
            "team": "Baltimore Orioles",
            "photo_url": None,
        }
        self.dummy_game = {
            "role": "Abridor",
            "opponent": "Minnesota Twins",
            "date": "2024-04-17",
            "ip": "5.2",
            "h": 3,
            "r": 0,
            "er": 0,
            "bb": 0,
            "so": 4,
            "pitches": 75,
            "league": "MLB",
        }
        self.dummy_statcast_analysis = {
            "total_pitches": 75,
            "has_statcast": True,
            "statcast_table": [
                {
                    "pitch_name": "4-Seam Fastball", "count": 47, "usage_pct": "62.7%",
                    "velo_avg": 95.9, "velo_max": 97.8, "spin_avg": 2413,
                    "ivb": 16.9, "hb": 10.5, "whiff_pct": "23.4%", "csw_pct": "23.4%", "zone_pct": "57.4%",
                }
            ],
            "pbp_kpis": {
                "csw_pct": "23.4%",
                "whiff_pct": "23.4%",
            },
            "pitches": [
                {
                    "pitch_name": "4-Seam Fastball", "hb": 10.5, "ivb": 16.9,
                    "plate_x": 0.2, "plate_z": 2.8, "is_whiff": False,
                }
            ],
            "innings_workload": [
                {"inning": 1, "pitches": 15, "strikes": 10, "avg_li": 1.1},
                {"inning": 2, "pitches": 12, "strikes": 9, "avg_li": 0.8},
            ],
            "splits_platoon": {
                "vs_lhb": {"pitches": 30, "csw_pct": "25.0%", "whiff_pct": "20.0%", "strike_pct": "65.0%"},
                "vs_rhb": {"pitches": 45, "csw_pct": "22.0%", "whiff_pct": "25.0%", "strike_pct": "67.0%"},
            },
        }

    def test_build_mlb_statcast_card(self):
        """Generación de tarjeta PNG MLB/MiLB a 300 DPI y dimensiones 2400x1350."""
        png_bytes = build_pitching_summary_card(
            pitcher_data=self.dummy_pitcher,
            game_data=self.dummy_game,
            pitch_analysis=self.dummy_statcast_analysis,
            is_lvbp=False,
            season=2024,
        )

        self.assertIsInstance(png_bytes, bytes)
        self.assertGreater(len(png_bytes), 50000)
        self.assertEqual(png_bytes[:8], b"\x89PNG\r\n\x1a\n")

        img = Image.open(io.BytesIO(png_bytes))
        self.assertEqual(img.format, "PNG")
        self.assertEqual(img.size, CANVAS_SIZE)
        dpi = img.info.get("dpi")
        if dpi:
            self.assertEqual(int(round(dpi[0])), 300)
            self.assertEqual(int(round(dpi[1])), 300)

    def test_build_lvbp_card(self):
        """Generación de tarjeta PNG Leones del Caracas (LVBP PBP) a 300 DPI y 2400x1350."""
        caracas_pitcher = {
            "name": "Erick Leal",
            "throws": "R",
            "team": "Leones del Caracas",
            "photo_url": None,
        }
        caracas_game = {
            "role": "Abridor",
            "opponent": "Navegantes del Magallanes",
            "date": "2025-11-20",
            "ip": "5.0",
            "h": 4,
            "r": 1,
            "er": 1,
            "bb": 1,
            "so": 6,
            "pitches": 78,
            "league": "LVBP",
        }
        caracas_analysis = {
            "total_pitches": 78,
            "has_statcast": False,
            "pbp_table": [
                {"destination": "Bolas", "count": 28, "pct": "35.9%"},
                {"destination": "Strikes Cantados", "count": 18, "pct": "23.1%"},
                {"destination": "Strikes Abanicados (Whiff)", "count": 12, "pct": "15.4%"},
                {"destination": "Fouls", "count": 10, "pct": "12.8%"},
                {"destination": "En Juego (Out / Hit)", "count": 10, "pct": "12.8%"},
            ],
            "pbp_kpis": {
                "csw_pct": "38.5%",
                "whiff_pct": "37.5%",
            },
            "innings_workload": [
                {"inning": 1, "pitches": 18, "strikes": 12, "avg_li": 1.2},
                {"inning": 2, "pitches": 15, "strikes": 11, "avg_li": 0.9},
                {"inning": 3, "pitches": 16, "strikes": 10, "avg_li": 1.4},
            ],
            "splits_platoon": {
                "vs_lhb": {"pitches": 35, "csw_pct": "35.0%", "whiff_pct": "30.0%", "strike_pct": "60.0%"},
                "vs_rhb": {"pitches": 43, "csw_pct": "40.0%", "whiff_pct": "42.0%", "strike_pct": "65.0%"},
            },
        }

        png_bytes = build_pitching_summary_card(
            pitcher_data=caracas_pitcher,
            game_data=caracas_game,
            pitch_analysis=caracas_analysis,
            is_lvbp=True,
            season=2025,
        )

        self.assertIsInstance(png_bytes, bytes)
        self.assertGreater(len(png_bytes), 50000)
        self.assertEqual(png_bytes[:8], b"\x89PNG\r\n\x1a\n")

        img = Image.open(io.BytesIO(png_bytes))
        self.assertEqual(img.format, "PNG")
        self.assertEqual(img.size, CANVAS_SIZE_LVBP)

    def test_pitch_colors_coverage(self):
        """Valida que los lanzamientos reconocidos tengan asignación de color."""
        self.assertEqual(_get_pitch_color("4-Seam Fastball"), (210, 45, 73))
        self.assertEqual(_get_pitch_color("Slider"), (238, 231, 22))
        self.assertEqual(_get_pitch_color("Changeup"), (29, 190, 58))
        self.assertEqual(_get_pitch_color("Otro Pitcheo"), (140, 140, 140))

    def test_build_card_streamlit_named_args(self):
        """Valida que build_pitching_summary_card acepte pitcher_info, game_summary, analysis, etc."""
        png_bytes = build_pitching_summary_card(
            pitcher_info=self.dummy_pitcher,
            game_summary=self.dummy_game,
            analysis=self.dummy_statcast_analysis,
            is_lvbp=False,
            mode="game",
            season=2024,
        )
        self.assertIsInstance(png_bytes, bytes)
        self.assertGreater(len(png_bytes), 50000)


class TestMatchup360Card(unittest.TestCase):
    """Pruebas del generador gráfico de tarjetas Matchup 360 H2H (utils/matchup_card.py)."""

    def test_build_matchup_image_png(self):
        """build_matchup_image debe generar PNG a 300 DPI y 1360px de ancho con caracteres especiales."""
        p1 = {"name": "José Rondón", "badge": "CAR", "pos": "OF", "headshot": None, "team_logo": None}
        p2 = {"name": "Renato Núñez", "badge": "MAG", "pos": "1B", "headshot": None, "team_logo": None}
        rows = [
            {"category": "Ofensiva", "metric": "wOBA", "val_1": ".412", "val_2": ".395", "winner": "José Rondón (CAR)", "is_header": False},
            {"category": "Ofensiva", "metric": "wRC+", "val_1": "155", "val_2": "142", "winner": "José Rondón (CAR)", "is_header": False},
            {"category": "Volumen", "metric": "HR", "val_1": "12", "val_2": "14", "winner": "Renato Núñez (MAG)", "is_header": False},
        ]
        png_bytes = build_matchup_image(
            p1, p2, rows, is_batter=True, season=2025,
            phase_1="Temporada Regular", phase_2="Round Robin"
        )
        self.assertIsInstance(png_bytes, bytes)
        self.assertGreater(len(png_bytes), 5000)
        self.assertEqual(png_bytes[:8], b"\x89PNG\r\n\x1a\n")

        im = Image.open(io.BytesIO(png_bytes))
        self.assertEqual(im.format, "PNG")
        self.assertEqual(im.size[0], 1360)
        dpi = im.info.get("dpi")
        if dpi:
            self.assertAlmostEqual(dpi[0], 300.0, delta=1.0)
            self.assertAlmostEqual(dpi[1], 300.0, delta=1.0)


class TestSupabaseClientParity(unittest.TestCase):
    """Pruebas de paridad funcional en utils/supabase_client.py."""

    def test_collective_team_stats_signature(self):
        """Verifica que get_collective_team_stats admita season, phase y group."""
        stats = get_collective_team_stats(season=2024, phase='R', group='all')
        self.assertIsInstance(stats, dict)
        self.assertIn('batting', stats)
        self.assertIn('pitching', stats)
        self.assertIn('fielding', stats)


if __name__ == "__main__":
    unittest.main()
