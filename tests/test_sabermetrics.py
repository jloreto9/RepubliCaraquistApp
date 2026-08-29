"""
tests/test_sabermetrics.py
Suite de pruebas unitarias para verificación de integridad matemática y sabermétrica
en RepubliCaraquistApp.
"""
import unittest
import numpy as np
import pandas as pd
import sys
import os

# Asegurar path raíz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.wpa_engine import encode_base_state, format_base_state, RE24
from utils.elo import expected_score, update_elo, BASE_ELO, HOME_ADVANTAGE
from utils.supabase_client import calculate_batting_stats


class TestWPAEngine(unittest.TestCase):
    """Verificación de matriz RE24 y codificación de bases."""

    def test_encode_base_state_all_combinations(self):
        # 0: ---
        self.assertEqual(encode_base_state(False, False, False), 0)
        # 1: 1--
        self.assertEqual(encode_base_state(True, False, False), 1)
        # 2: -2-
        self.assertEqual(encode_base_state(False, True, False), 2)
        # 3: --3 (Crítico: debe ser 3 para alinear con RE24)
        self.assertEqual(encode_base_state(False, False, True), 3)
        # 4: 12- (Crítico: debe ser 4 para alinear con RE24)
        self.assertEqual(encode_base_state(True, True, False), 4)
        # 5: 1-3
        self.assertEqual(encode_base_state(True, False, True), 5)
        # 6: -23
        self.assertEqual(encode_base_state(False, True, True), 6)
        # 7: 123
        self.assertEqual(encode_base_state(True, True, True), 7)

    def test_re24_keys_coverage(self):
        """Verifica que todos los 24 estados (3 outs x 8 base states) existan en RE24."""
        for outs in [0, 1, 2]:
            for base_state in range(8):
                self.assertIn((outs, base_state), RE24)
                self.assertIsInstance(RE24[(outs, base_state)], float)
                self.assertGreater(RE24[(outs, base_state)], 0.0)

    def test_format_base_state(self):
        self.assertEqual(format_base_state(0), "◇ ◇ ◇")
        self.assertEqual(format_base_state(1), "◇ ◇ ◆")
        self.assertEqual(format_base_state(2), "◇ ◆ ◇")
        self.assertEqual(format_base_state(3), "◆ ◇ ◇")
        self.assertEqual(format_base_state(4), "◇ ◆ ◆")
        self.assertEqual(format_base_state(7), "◆ ◆ ◆")


class TestSabermetricCalculations(unittest.TestCase):
    """Verificación de fórmulas de bateo y manejo de valores extremos."""

    def test_obp_calculation_with_hbp_and_sf(self):
        df = pd.DataFrame([{
            'player_id': 1001,
            'ab': 10,
            'r': 2,
            'h': 3,
            'doubles': 1,
            'triples': 0,
            'hr': 1,
            'rbi': 2,
            'bb': 2,
            'hbp': 1,
            'sf': 1,
            'so': 2,
            'sb': 0
        }])
        res = calculate_batting_stats(df)
        self.assertFalse(res.empty)
        # OBP = (3 + 2 + 1) / (10 + 2 + 1 + 1) = 6 / 14 = 0.42857 -> 0.429
        self.assertAlmostEqual(res.iloc[0]['obp'], 0.429, places=3)
        # AVG = 3 / 10 = 0.300
        self.assertAlmostEqual(res.iloc[0]['avg'], 0.300, places=3)
        # SLG = (3 + 1 + 0 + 3*1) / 10 = 7 / 10 = 0.700
        self.assertAlmostEqual(res.iloc[0]['slg'], 0.700, places=3)
        # OPS = 0.429 + 0.700 = 1.129
        self.assertAlmostEqual(res.iloc[0]['ops'], 1.129, places=3)

    def test_zero_ab_handling(self):
        df = pd.DataFrame([{
            'player_id': 1002,
            'ab': 0,
            'r': 0,
            'h': 0,
            'doubles': 0,
            'triples': 0,
            'hr': 0,
            'rbi': 0,
            'bb': 1,
            'hbp': 0,
            'sf': 0,
            'so': 0,
            'sb': 0
        }])
        res = calculate_batting_stats(df)
        self.assertFalse(res.empty)
        self.assertEqual(res.iloc[0]['avg'], 0.0)
        self.assertEqual(res.iloc[0]['obp'], 1.0)
        self.assertEqual(res.iloc[0]['slg'], 0.0)
        self.assertEqual(res.iloc[0]['ops'], 1.0)


class TestELOModel(unittest.TestCase):
    """Verificación del modelo de ratings ELO adaptado."""

    def test_expected_score_symmetry(self):
        # A y B con mismo rating en campo neutral
        self.assertAlmostEqual(expected_score(1500.0, 1500.0), 0.5, places=4)
        # Probabilidades complementarias
        p_a = expected_score(1550.0, 1450.0)
        p_b = expected_score(1450.0, 1550.0)
        self.assertAlmostEqual(p_a + p_b, 1.0, places=4)

    def test_update_elo_home_win(self):
        new_h, new_a = update_elo(1500.0, 1500.0, home_win=True, k=32.0)
        self.assertGreater(new_h, 1500.0)
        self.assertLess(new_a, 1500.0)
        # Suma de delta es cero
        self.assertAlmostEqual((new_h - 1500.0) + (new_a - 1500.0), 0.0, places=4)


if __name__ == '__main__':
    unittest.main()
