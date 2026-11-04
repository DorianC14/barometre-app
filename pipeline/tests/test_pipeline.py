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


def test_contributions_sum_to_score():
    idx = pd.date_range("2000-01-01", "2026-01-01", freq="D")
    rng = np.random.default_rng(0)
    R = {k: pd.Series(100 + rng.normal(0, 1, len(idx)).cumsum(), index=idx).abs() + 1 for k in cfg.SERIES}
    res = sc.compute_region(R, "world", pd.date_range("2010-01-01", "2026-01-01"), {}, idx[-1])
    total = 50 + sum(c["contribution"] for c in res["contributions"])
    assert abs(total - res["T"].iloc[-1]) < 0.5


def test_zones_inverted_scale():
    assert cfg.zone_of(10)[0] == "Euphorie"
    assert cfg.zone_of(90)[0] == "Stress"
    assert sum(p["weight"] for p in cfg.PILLARS.values()) == 1.0


def test_transforms():
    q = pd.Series([100, 101, 102, 103, 104, 106, 108, 110, 112], index=pd.date_range("2020-01-01", periods=9, freq="QS"))
    assert round(yoy(q).iloc[0], 2) == 4.0
    assert len(impulse(q)) == 1
