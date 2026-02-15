# utils/elo.py
BASE_ELO = 1500
HOME_ADVANTAGE = 35
K_BY_PHASE = {
    'regular': 20,
    'wildcard_playin': 25,
    'round_robin': 22,
    'final': 28,
    'unknown': 20,
}


def expected_score(r_a, r_b):
    """Probabilidad esperada de A contra B con escala 400."""
    return 1.0 / (1.0 + 10 ** ((r_b - r_a) / 400.0))


def update_elo(r_home, r_away, home_win, k, home_advantage=HOME_ADVANTAGE):
    """Actualiza ELO de local y visitante de forma determinista."""
    home_effective = r_home + home_advantage
    exp_home = expected_score(home_effective, r_away)
    score_home = 1.0 if home_win else 0.0

    delta = k * (score_home - exp_home)
    new_home = r_home + delta
    new_away = r_away - delta
    return new_home, new_away
