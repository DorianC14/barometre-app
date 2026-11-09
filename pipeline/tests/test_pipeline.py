"""Tests de la logique de calcul (hors ligne). Lancer : python -m pytest pipeline/tests"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config as cfg  # noqa: E402
import news  # noqa: E402
import scoring as sc  # noqa: E402
from transforms import impulse, yoy  # noqa: E402


def test_sentiment_fr():
    assert news.sentiment("Le CAC 40 s'envole, rebond record des banques", "fr")[0] > 0
    assert news.sentiment("Krach : la Bourse chute, craintes de récession", "fr")[0] < 0
    assert news.sentiment("Pas de récession en vue selon la BCE", "fr")[0] > 0
    assert news.sentiment("La BCE annonce une baisse des taux", "fr")[0] > 0


def test_sentiment_en():
    assert news.sentiment("Stocks rally to record high on strong earnings", "en")[0] > 0
    assert news.sentiment("Markets tumble as recession fears grow", "en")[0] < 0
    assert news.sentiment("Fed says there is no recession", "en")[0] > 0


def test_cluster_groups_same_topic():
    items = [
        {"title": "La BCE maintient ses taux directeurs inchangés", "summary": "", "link": "a", "source": "Les Echos", "published": "2026-11-02T08:00:00Z", "sentiment": 0.0},
        {"title": "Taux directeurs : la BCE maintient le statu quo", "summary": "", "link": "b", "source": "Zonebourse", "published": "2026-11-02T07:00:00Z", "sentiment": 0.1},
        {"title": "Le pétrole recule nettement", "summary": "", "link": "c", "source": "Boursorama", "published": "2026-11-02T06:00:00Z", "sentiment": -0.5},
    ]
    topics = news.cluster(items)
    assert topics[0]["count"] == 2 and len(topics[0]["sources"]) == 2


def test_favorability_bounds_and_direction():
    idx = pd.date_range("2000-01-01", "2026-01-01", freq="D")
    up = pd.Series(np.linspace(0, 10, len(idx)), index=idx)
    f_pos = sc.favorability(up, 1, idx)
    f_neg = sc.favorability(up, -1, idx)
    assert f_pos.dropna().between(0, 100).all()
    assert f_pos.iloc[-1] > 80 and f_neg.iloc[-1] < 20


def test_inflation_target():
    idx = pd.date_range("2020-01-01", periods=3, freq="D")
    s = pd.Series([2.0, 4.0, 0.0], index=idx)
    f = sc.favorability(s, "target", idx)
    assert list(f.round(1)) == [100.0, 50.0, 50.0]


def _random_R(seed=0):
    idx = pd.date_range("1995-01-01", "2026-01-01", freq="D")
    rng = np.random.default_rng(seed)
    return {k: pd.Series(100 + rng.normal(0, 1, len(idx)).cumsum(), index=idx).abs() + 1 for k in cfg.SERIES}, idx


def test_all_regions_and_contributions_sum_to_score():
    R, idx = _random_R()
    for region in cfg.REGIONS:
        res = sc.compute_region(R, region, pd.date_range(cfg.CALC_START, "2026-01-01"), {}, idx[-1])
        assert res["indicators"], region
        T = res["T"].dropna()
        assert T.between(0, 100).all()
        total = 50 + sum(c["contribution"] for c in res["contributions"]) + res["calib"]["adjust"]
        assert abs(total - T.iloc[-1]) < 0.5


def test_calibration_spreads_scores():
    """Un score brut resserré autour de 50 doit couvrir toute l'échelle une fois calé."""
    idx = pd.date_range("2000-01-01", "2026-01-01", freq="D")
    rng = np.random.default_rng(1)
    raw = pd.Series(50 + 5 * np.sin(np.arange(len(idx)) / 200) + rng.normal(0, 1, len(idx)), index=idx)
    cal = sc.calibrate(raw)[0].dropna()
    assert cal.min() < 20 and cal.max() > 80
    assert 0.25 < (cal.between(40, 60)).mean() < 0.55


def test_shock_multiplier_bounded_and_decays():
    idx = pd.date_range("2020-01-01", periods=120, freq="D")
    F = pd.Series(50.0, index=idx)
    F.iloc[60:] = 90.0                      # saut de 40 points
    m, _ = sc.shock_multiplier(F)
    assert m.max() <= 1 + cfg.SHOCK_MAX_BOOST + 1e-9
    assert m.iloc[61] > 1.4 and m.iloc[59] == 1.0
    assert m.iloc[100] < 1.05               # revenu à la normale en quelques semaines


def test_pick_edition():
    import run
    from datetime import datetime, timezone
    # hiver (UTC+1) : 7 h 10 UTC = 8 h 10 à Paris -> édition de 8 h 30
    e = run.pick_edition(datetime(2026, 1, 15, 7, 10, tzinfo=timezone.utc), set(), True)
    assert e["id"] == "preouverture"
    # 8 h 10 UTC = 9 h 10 -> 9 h 30
    assert run.pick_edition(datetime(2026, 1, 15, 8, 10, tzinfo=timezone.utc), {"preouverture"}, True)["id"] == "ouverture"
    # 6 h 10 UTC = 7 h 10 -> trop tôt
    assert run.pick_edition(datetime(2026, 1, 15, 6, 10, tzinfo=timezone.utc), set(), True) is None
    # été (UTC+2) : 8 h 10 UTC = 10 h 10, édition de 9 h 30 déjà publiée -> rien
    assert run.pick_edition(datetime(2026, 7, 15, 8, 10, tzinfo=timezone.utc), {"preouverture", "ouverture"}, True) is None
    # été : 18 h 40 UTC = 20 h 40 -> 21 h
    assert run.pick_edition(datetime(2026, 7, 15, 18, 40, tzinfo=timezone.utc), set(), True)["id"] == "soir"


def test_zones_inverted_scale():
    assert cfg.zone_of(10)[0] == "Euphorie"
    assert cfg.zone_of(90)[0] == "Stress"
    assert sum(p["weight"] for p in cfg.PILLARS.values()) == 1.0
    for zone, alloc in cfg.ALLOCATION.items():
        assert sum(alloc.values()) == 100, zone
        assert list(alloc) == cfg.ASSETS


def test_news_day_synthesis():
    review = {"generated_at": "2026-11-09T07:20:00Z", "sections": {
        "europe": {"sentiment": 0.1, "theme": "l'énergie", "topics": [
            {"title": "Le pétrole recule nettement après l'accord de l'OPEP", "sources": ["A", "B"], "count": 3,
             "tone": "neutre", "link": "x"},
            {"title": "Bourse : Cours de bourse et CAC 40 en direct", "sources": ["A", "B", "C"], "count": 3,
             "tone": "neutre", "link": "y"}]},
        "international": {"sentiment": 0.0, "theme": None, "topics": []}}}
    news.EDITION_ORDER[:] = cfg.EDITIONS
    day = news.update_day({}, review, "preouverture", "2026-11-09")
    lines = day["synthese"]["lines"]
    assert len(lines) == 1 and "pétrole" in lines[0]["text"] and lines[0]["time"] == "8 h 30"


def test_transforms():
    q = pd.Series([100, 101, 102, 103, 104, 106, 108, 110, 112], index=pd.date_range("2020-01-01", periods=9, freq="QS"))
    assert round(yoy(q).iloc[0], 2) == 4.0
    assert len(impulse(q)) == 1
