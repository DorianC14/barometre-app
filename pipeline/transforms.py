"""Transformations des séries brutes en indicateurs économiques lisibles."""
from __future__ import annotations

import pandas as pd


def _daily(s: pd.Series) -> pd.Series:
    """Série calendaire quotidienne, valeurs prolongées jusqu'à la publication suivante."""
    s = s.dropna().sort_index()
    if s.empty:
        return s
    idx = pd.date_range(s.index[0], s.index[-1], freq="D")
    return s.reindex(s.index.union(idx)).ffill().reindex(idx)


def yoy(s: pd.Series) -> pd.Series:
    """Variation sur 1 an en % (calculée à la fréquence d'origine)."""
    s = s.dropna().sort_index()
    prev = s.reindex(s.index - pd.DateOffset(years=1), method="nearest", tolerance=pd.Timedelta(days=20))
    out = (s.values / prev.values - 1) * 100
    return pd.Series(out, index=s.index).dropna()


def chg(s: pd.Series, periods: int) -> pd.Series:
    """Variation en % sur `periods` séances."""
    s = s.dropna().sort_index()
    return (s / s.shift(periods) - 1).dropna() * 100


def ma_gap(s: pd.Series, n: int = 200) -> pd.Series:
    """Écart en % du cours à sa moyenne mobile `n` séances."""
    s = s.dropna().sort_index()
    return ((s / s.rolling(n, min_periods=int(n * 0.8)).mean()) - 1).dropna() * 100


def dev1y(s: pd.Series) -> pd.Series:
    """Écart absolu en % à la moyenne sur 1 an (mouvement brutal = stress)."""
    s = s.dropna().sort_index()
    return ((s / s.rolling(252, min_periods=200).mean() - 1).abs()).dropna() * 100


def price_to_trend(s: pd.Series) -> pd.Series:
    """Cours rapporté à sa moyenne sur 10 ans : proxy de valorisation quand le PER n'est pas libre."""
    s = s.dropna().sort_index()
    return (s / s.rolling(2520, min_periods=1260).mean()).dropna()


def spread(a: pd.Series, b: pd.Series) -> pd.Series:
    """Différence a − b, alignée en quotidien."""
    a, b = _daily(a), _daily(b)
    idx = a.index.intersection(b.index)
    return (a.reindex(idx) - b.reindex(idx)).dropna()


def inv_yield(pe: pd.Series) -> pd.Series:
    """Rendement des bénéfices (1 / PER) en %."""
    return (100 / pe.dropna()).replace([float("inf")], pd.NA).dropna()


def mean_window(s: pd.Series, days: int) -> pd.Series:
    return s.dropna().sort_index().rolling(f"{days}D").mean().dropna()


def impulse(ratio: pd.Series) -> pd.Series:
    """Credit impulse (approche Biggs-Mayer-Pick) à partir du crédit au secteur privé en % du PIB.

    impulse_t = (ratio_t − ratio_{t−4}) − (ratio_{t−4} − ratio_{t−8}), données trimestrielles :
    c'est la variation du flux de nouveau crédit, rapportée au PIB, sur un an.
    """
    r = ratio.dropna().sort_index()
    flow = r - r.shift(4)
    return (flow - flow.shift(4)).dropna()


def realized_vol(s: pd.Series, n: int = 21) -> pd.Series:
    """Volatilité réalisée sur `n` séances, annualisée en % : remplace la volatilité implicite
    quand aucun indice de type VIX n'est disponible gratuitement (Chine, Japon)."""
    import numpy as np
    s = s.dropna().sort_index()
    r = np.log(s / s.shift(1))
    return (r.rolling(n, min_periods=int(n * 0.8)).std() * (252 ** 0.5) * 100).dropna()
