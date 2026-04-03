# scripts/elo_sanity_check.py
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.elo import update_elo

PHASE_BY_GAME_TYPE = {
    'R': 'regular',
    'D': 'wildcard_playin',
    'L': 'round_robin',
    'W': 'final',
}


def map_phase(game_type_code):
    if not game_type_code:
        return 'unknown'
    return PHASE_BY_GAME_TYPE.get(str(game_type_code).upper(), 'unknown')


def run_checks():
    assert map_phase('R') == 'regular'
    assert map_phase('D') == 'wildcard_playin'
    assert map_phase('L') == 'round_robin'
    assert map_phase('W') == 'final'
    assert map_phase('X') == 'unknown'

    home_new, away_new = update_elo(1500, 1500, True, k=20, home_advantage=35)
    assert home_new > 1500, 'El ganador debe subir ELO'
    assert away_new < 1500, 'El perdedor debe bajar ELO'

    home_new2, away_new2 = update_elo(1500, 1500, False, k=20, home_advantage=35)
    assert home_new2 < 1500, 'Si pierde local, su ELO debe bajar'
    assert away_new2 > 1500, 'Si gana visitante, su ELO debe subir'

    print('OK: sanity checks de fase y direccion ELO')


if __name__ == '__main__':
    run_checks()
