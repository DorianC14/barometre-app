"""Normalisation, pondération et construction des scores de tension (0 = euphorie, 100 = stress)."""
from __future__ import annotations

import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import norm

import config as cfg
from transforms import _daily


# --------------------------------------------------------------------------- normalisation
def favorability(raw: pd.Series, direction, index: pd.DatetimeIndex) -> pd.Series:
    """Note « favorable aux marchés » de 0 à 100, calculée jour par jour sans regarder le futur.

    - z-score glissant sur 10 ans (3 ans minimum), borné à ±3, converti en percentile (loi normale) ;
    - Min-Max sur l'historique disponible pour les séries trop courtes ;
    - pour l'inflation : 100 − 25 × |π − 2|.
    """
    d = _daily(raw)
    if d.empty:
        return pd.Series(np.nan, index=index)
    if direction == "target":
        f = (100 - 25 * (d - 2).abs()).clip(0, 100)
    else:
        n_obs = raw.dropna().shape[0]
        span_days = (d.index[-1] - d.index[0]).days
        if span_days >= cfg.Z_MIN_DAYS:
            roll = d.rolling(f"{cfg.Z_WINDOW_DAYS}D", min_periods=cfg.Z_MIN_DAYS)
            z = ((d - roll.mean()) / roll.std()).clip(-cfg.Z_CLIP, cfg.Z_CLIP)
            f = pd.Series(norm.cdf(z), index=d.index) * 100
            f[z.isna()] = np.nan
        elif n_obs >= 10:
            lo, hi = d.expanding().min(), d.expanding().max()
            f = ((d - lo) / (hi - lo).replace(0, np.nan) * 100).fillna(50)
        else:
            f = pd.Series(50.0, index=d.index)
        if direction == -1:
            f = 100 - f
    f = f.reindex(f.index.union(index)).ffill().reindex(index)
    return f


def weighted_mean(frame: pd.DataFrame, weights: dict) -> pd.Series:
    """Moyenne pondérée ligne à ligne, poids renormalisés sur les colonnes disponibles."""
    if frame.empty:
        return pd.Series(dtype=float)
    w = pd.Series({c: weights.get(c, 1.0) for c in frame.columns})
    mask = frame.notna()
    num = (frame.fillna(0) * w).sum(axis=1)
    den = (mask * w).sum(axis=1)
    return (num / den.replace(0, np.nan))


def effective_weights(row: pd.Series, weights: dict) -> dict:
    avail = {c: weights.get(c, 1.0) for c in row.index if pd.notna(row[c])}
    tot = sum(avail.values())
    return {c: w / tot for c, w in avail.items()} if tot else {}


# --------------------------------------------------------------------------- utilitaires JSON
def r1(x, nd=1):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    try:
        if pd.isna(x):
            return None
    except (TypeError, ValueError):
        pass
    return round(float(x), nd)


def sparkline(s: pd.Series, days: int = 365) -> list:
    s = s.dropna()
    if s.empty:
        return []
    s = s[s.index >= s.index[-1] - pd.Timedelta(days=days)]
    w = s.resample("W").last().dropna()
    return [[d.strftime("%Y-%m-%d"), r1(v, 3)] for d, v in w.items()]


# --------------------------------------------------------------------------- poids variables
def shock_multiplier(F: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Multiplicateur de poids (1 à 1 + SHOCK_MAX_BOOST) déclenché par un mouvement brutal de la note.

    intensité = (|variation de la note sur 5 jours| − 10) / (25 − 10), bornée entre 0 et 1 ;
    le surplus de poids décroît ensuite de moitié chaque semaine. Renvoie (multiplicateur, variation).
    """
    d = F.diff(cfg.SHOCK_LOOKBACK)
    inten = ((d.abs() - cfg.SHOCK_START) / (cfg.SHOCK_FULL - cfg.SHOCK_START)).clip(0, 1).fillna(0).to_numpy()
    decay = 0.5 ** (1 / cfg.SHOCK_HALF_LIFE)
    e = np.empty_like(inten)
    prev = 0.0
    for k, x in enumerate(inten):
        prev = x if x > prev * decay else prev * decay
        e[k] = prev
    return pd.Series(1 + cfg.SHOCK_MAX_BOOST * e, index=F.index), d


def weighted_mean_tv(frame: pd.DataFrame, W: pd.DataFrame) -> pd.Series:
    """Moyenne pondérée avec des poids qui varient dans le temps (mêmes colonnes que frame)."""
    mask = frame.notna()
    num = (frame.fillna(0) * W).sum(axis=1)
    den = (W * mask).sum(axis=1)
    return num / den.replace(0, np.nan)


# --------------------------------------------------------------------------- calage de l'échelle
def calibrate(T_raw: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Étire le score brut selon son rang dans les 10 dernières années : score = 50 + 20 × Φ⁻¹(rang).

    À chaque date, le score brut n'est comparé qu'aux 10 années précédentes (pas d'information
    future), comme chaque indicateur. Φ⁻¹ convertit ce rang en « nombre d'écarts-types » d'une loi normale :
    les zones correspondent alors à des fréquences fixes, symétriques vers le haut et vers le bas
    (euphorie et stress ≈ 7 % des jours chacun, favorable et prudence ≈ 24 %, neutre ≈ 38 %).
    Renvoie (score calé, moyenne historique du brut, écart-type historique du brut).
    """
    s = T_raw.dropna()
    win = f"{cfg.CALIB_WINDOW_DAYS}D"
    n = s.rolling(win, min_periods=cfg.CALIB_MIN_DAYS).count()
    rank = s.rolling(win, min_periods=cfg.CALIB_MIN_DAYS).rank()
    p = ((rank - 0.5) / n).clip(0.001, 0.999)       # percentile strictement entre 0 et 1
    cal = pd.Series(50 + cfg.CALIB_POINTS_PER_SD * norm.ppf(p), index=s.index).clip(0, 100)
    cal[p.isna()] = np.nan
    mu = s.rolling(win, min_periods=cfg.CALIB_MIN_DAYS).mean()
    sd = s.rolling(win, min_periods=cfg.CALIB_MIN_DAYS).std()
    return cal.reindex(T_raw.index), mu.reindex(T_raw.index), sd.reindex(T_raw.index)


# --------------------------------------------------------------------------- calcul par région
def compute_region(R: dict, region: str, index: pd.DatetimeIndex, sources_used: dict, today: pd.Timestamp):
    indicators_out = []
    ind_F = {}
    ind_weights = {}
    ind_pillar = {}
    composites = {}
    mult, shock_d = {}, {}

    for ind in cfg.INDICATORS:
        comps = ind.get(region)
        if not comps:
            continue
        comp_F, comp_w, comp_out, comp_raw = {}, {}, [], {}
        for c in comps:
            try:
                raw = c["fn"](R).dropna()
                if raw.empty:
                    raise ValueError("vide")
            except Exception:  # noqa: BLE001 — série manquante : composante ignorée
                comp_out.append({"name": c["name"], "available": False})
                continue
            F = favorability(raw, ind["direction"], index)
            comp_F[c["name"]] = F
            comp_w[c["name"]] = c["weight"]
            comp_raw[c["name"]] = raw
            last_date = raw.index[-1]
            stale_days = cfg.STALE_AFTER.get(ind["freq"], 60)
            comp_out.append({
                "name": c["name"],
                "available": True,
                "value": r1(raw.iloc[-1], 2),
                "unit": c.get("unit") or ind["unit"],
                "date": last_date.strftime("%Y-%m-%d"),
                "fresh": bool((today - last_date).days <= stale_days),
                "tension": r1(100 - F.iloc[-1]),
                "spark": sparkline(raw),
            })
        if not comp_F:
            indicators_out.append({**_ind_meta(ind), "available": False, "components": comp_out})
            continue
        fr = pd.DataFrame(comp_F)
        F_ind = weighted_mean(fr, comp_w)
        ind_F[ind["id"]] = F_ind
        ind_weights[ind["id"]] = ind.get("weight", 1)
        ind_pillar[ind["id"]] = ind["pillar"]
        mult[ind["id"]], shock_d[ind["id"]] = shock_multiplier(F_ind)
        # composite brut (mêmes unités) pour le régime et les règles de conseil
        rawf = pd.DataFrame({k: _daily(v) for k, v in comp_raw.items()})
        composites[ind["id"]] = weighted_mean(rawf, comp_w).dropna()
        srcs = sorted({sources_used.get(k, "") for k in _series_used(ind, region)} - {""})
        T_ind = 100 - F_ind
        indicators_out.append({
            **_ind_meta(ind),
            "available": True,
            "tension": r1(T_ind.iloc[-1]),
            "tension_7d": r1(T_ind.iloc[-8]) if len(F_ind) > 8 else None,
            "normal": r1(T_ind.dropna().mean()),
            "value": r1(composites[ind["id"]].iloc[-1], 2) if len(composites[ind["id"]]) else None,
            "components": comp_out,
            "sources": [cfg.SOURCE_LABELS.get(s.split(":")[0], s) for s in srcs],
        })

    # ---- piliers (poids des indicateurs variables dans le temps)
    pillar_F = {}
    W_ind = {i: mult[i] * ind_weights[i] for i in ind_F}
    for p in cfg.PILLAR_ORDER:
        ids = [i for i, pp in ind_pillar.items() if pp == p]
        if ids:
            pillar_F[p] = weighted_mean_tv(pd.DataFrame({i: ind_F[i] for i in ids}),
                                           pd.DataFrame({i: W_ind[i] for i in ids}))
    pw = {p: cfg.PILLARS[p]["weight"] for p in pillar_F}
    PF = pd.DataFrame(pillar_F)
    T_raw = 100 - weighted_mean(PF, pw)
    T, mu, sd = calibrate(T_raw)
    T_pillars = 100 - PF

    # ---- variantes de robustesse (calées de la même façon)
    eq_T = calibrate(100 - weighted_mean(PF, {p: 1 for p in PF.columns}))[0]
    pca_raw, pca_w = _pca_variant(ind_F)
    pca_T = calibrate(pca_raw)[0] if pca_raw is not None else None

    # ---- contributions à la date du jour, en points du score calé :
    #      c_i = (20 / écart-type) × W_p × v_i × (T_i − normale_i)   où normale_i = moyenne passée de T_i
    last = index[-1]
    k = cfg.CALIB_POINTS_PER_SD / sd.iloc[-1] if pd.notna(sd.iloc[-1]) and sd.iloc[-1] > 0 else 1.0
    wp_eff = effective_weights(PF.loc[last], pw)
    contributions, boosts = [], []
    for p, Wp in wp_eff.items():
        ids = [i for i, pp in ind_pillar.items() if pp == p and pd.notna(ind_F[i].loc[last])]
        vi = effective_weights(pd.Series({i: ind_F[i].loc[last] for i in ids}),
                               {i: float(W_ind[i].loc[last]) for i in ids})
        for i, v in vi.items():
            Ti = 100 - ind_F[i].loc[last]
            hist_i = (100 - ind_F[i]).dropna()
            normal = float(hist_i[hist_i.index > last - pd.Timedelta(days=cfg.CALIB_WINDOW_DAYS)].mean())
            contributions.append({
                "id": i, "label": _label(i), "pillar": p,
                "weight": r1(Wp * v * 100, 1),
                "base_weight": r1(Wp * ind_weights[i] / sum(ind_weights[j] for j in ids) * 100, 1),
                "tension": r1(Ti), "normal": r1(normal),
                "contribution": k * Wp * v * (Ti - normal),
            })
            m = float(mult[i].loc[last])
            if m > 1.02:
                d = shock_d[i]
                recent = d[(d.index > last - pd.Timedelta(days=45)) & (d.abs() >= cfg.SHOCK_START)]
                when = recent.abs().idxmax() if not recent.empty else last
                boosts.append({"id": i, "label": _label(i), "pillar": p, "multiplier": r1(m, 2),
                               "date": when.strftime("%Y-%m-%d"),
                               "change": r1(-float(d.loc[when])) if pd.notna(d.loc[when]) else None})
    score = float(T.iloc[-1]) if pd.notna(T.iloc[-1]) else float(T_raw.iloc[-1])
    # Le calage n'est pas linéaire : on répartit l'écart réel du score à 50 au prorata des
    # contributions linéaires, quand elles vont dans le même sens (cas normal).
    tot = sum(c["contribution"] or 0 for c in contributions)
    if tot * (score - 50) > 0 and abs(tot) >= 0.5:
        f = (score - 50) / tot
        for c in contributions:
            c["contribution"] = r1((c["contribution"] or 0) * f, 2)
    contributions.sort(key=lambda c: -abs(c["contribution"] or 0))
    pillar_points = {}
    for c in contributions:
        pillar_points[c["pillar"]] = pillar_points.get(c["pillar"], 0) + (c["contribution"] or 0)
    adjust = score - 50 - sum(pillar_points.values())

    return {
        "R": R, "T": T, "T_raw": T_raw, "calib": {"mean": r1(mu.iloc[-1]), "sd": r1(sd.iloc[-1], 2),
                                                 "raw": r1(T_raw.iloc[-1]), "adjust": r1(adjust, 2)},
        "T_pillars": T_pillars, "eq_T": eq_T, "pca_T": pca_T, "pca_w": pca_w,
        "indicators": indicators_out, "contributions": contributions, "boosts": boosts,
        "pillar_points": {p: r1(v, 2) for p, v in pillar_points.items()},
        "composites": composites, "ind_F": ind_F, "pillar_weights_eff": wp_eff,
    }


def _ind_meta(ind):
    return {
        "id": ind["id"], "label": ind["label"], "pillar": ind["pillar"],
        "pillar_label": cfg.PILLARS[ind["pillar"]]["label"],
        "direction": {1: "+", -1: "−", "target": "cible 2 %"}[ind["direction"]],
        "unit": ind["unit"], "freq": ind["freq"], "weight_in_pillar": ind.get("weight", 1),
    }


def _label(i):
    return next(x["label"] for x in cfg.INDICATORS if x["id"] == i)


def _series_used(ind, region):
    """Devine les séries brutes utilisées par un indicateur (pour citer les sources)."""
    import inspect
    names = set()
    for c in ind.get(region, []):
        try:
            src = inspect.getsource(c["fn"])
        except (OSError, TypeError):
            continue
        for k in list(cfg.SERIES) + ["news_world", "news_europe"]:
            if f'"{k}"' in src:
                names.add(k)
    return names


def _pca_variant(ind_F: dict):
    """Pondération statistique : poids = |chargements| de la 1re composante principale."""
    df = pd.DataFrame(ind_F)
    df = df[df.index >= df.index.max() - pd.Timedelta(days=cfg.Z_WINDOW_DAYS)]
    # On écarte les indicateurs trop récents (ex. sentiment des news) qui videraient l'échantillon.
    df = df.loc[:, df.notna().mean() >= 0.8].dropna()
    df = df.loc[:, df.std() > 1e-9]
    if df.shape[0] < 250 or df.shape[1] < 3:
        return None, {}
    X = (df - df.mean()) / df.std()
    _, _, vt = np.linalg.svd(X.values, full_matrices=False)
    load = np.abs(vt[0])
    w = dict(zip(df.columns, load / load.sum()))
    full = pd.DataFrame(ind_F)
    T = 100 - weighted_mean(full[list(w)], w)
    return T, {k: r1(v * 100, 1) for k, v in w.items()}


# --------------------------------------------------------------------------- régime All Weather
REGIMES = {
    (True, False): ("Expansion désinflationniste", "Croissance en hausse, inflation en baisse",
                    "Actions et obligations d'entreprises historiquement les plus porteuses."),
    (True, True): ("Surchauffe", "Croissance en hausse, inflation en hausse",
                   "Matières premières, actions « value » et obligations indexées sur l'inflation."),
    (False, True): ("Stagflation", "Croissance en baisse, inflation en hausse",
                    "Or, obligations indexées sur l'inflation et matières premières."),
    (False, False): ("Ralentissement désinflationniste", "Croissance en baisse, inflation en baisse",
                     "Obligations d'État longues, puis actions défensives."),
}


def regime(composites: dict) -> dict | None:
    cli, infl = composites.get("cli"), composites.get("inflation")
    if cli is None or infl is None or len(cli) < 200 or len(infl) < 200:
        return None
    g_now, g_prev = cli.iloc[-1], cli.asof(cli.index[-1] - pd.Timedelta(days=91))
    i_now, i_prev = infl.iloc[-1], infl.asof(infl.index[-1] - pd.Timedelta(days=182))
    key = (bool(g_now > g_prev), bool(i_now > i_prev))
    name, desc, assets = REGIMES[key]
    return {
        "name": name, "description": desc, "assets": assets,
        "growth_up": key[0], "inflation_up": key[1],
        "growth_change": r1(g_now - g_prev, 2), "inflation_change": r1(i_now - i_prev, 2),
    }


# --------------------------------------------------------------------------- test historique indicatif
BT = {  # actions [(série, poids)], taux 10 ans (obligations), taux court (liquidités)
    "world": ([("spx", 0.6), ("sx5e", 0.4)], "us_10y", "fed_funds"),
    "europe": ([("sx5e", 1.0)], "ea_10y", "ecb_dfr"),
    "france": ([("cac", 1.0)], "oat_10y", "ecb_dfr"),
    "us": ([("spx", 1.0)], "us_10y", "fed_funds"),
    "cn": ([("shanghai", 1.0)], "us_10y", "cn_3m"),
    "jp": ([("nikkei", 1.0)], "jp_10y", "boj"),
}


def backtest(T: pd.Series, R: dict, region: str) -> dict | None:
    """Allocation dynamique selon la zone (mois précédent) vs portefeuille fixe 60/40, rendements approximés."""
    try:
        eqs, yk, ck = BT[region]
        eq = sum(w * R[k].resample("ME").last().pct_change() for k, w in eqs)
        y = _daily(R[yk]).resample("ME").last()
        cash = _daily(R[ck]).resample("ME").last() / 1200
        bond = y.shift(1) / 1200 - 8 * (y - y.shift(1)) / 100
        gold = R["gold"].resample("ME").last().pct_change()
        # immobilier coté (REIT) ; à défaut, les actions de la zone
        reit = R["reit"].resample("ME").last().pct_change() if "reit" in R else eq
    except KeyError:
        return None
    sig = T.resample("ME").last().shift(1)
    df = pd.DataFrame({"eq": eq, "bond": bond, "gold": gold, "cash": cash, "reit": reit, "sig": sig})
    df["reit"] = df["reit"].fillna(df["eq"])
    df = df.dropna()
    df = df[df.index >= cfg.HISTORY_START]
    if len(df) < 24:
        return None
    strat, bench = [], []
    for _, row in df.iterrows():
        a = cfg.ALLOCATION[cfg.zone_of(row["sig"])[0]]
        strat.append(a["Actions"] / 100 * row["eq"] + a["Obligations"] / 100 * row["bond"]
                     + a["Immobilier"] / 100 * row["reit"]
                     + a["Or"] / 100 * row["gold"] + a["Liquidités"] / 100 * row["cash"])
        bench.append(0.6 * row["eq"] + 0.4 * row["bond"])
    s, b = pd.Series(strat, index=df.index), pd.Series(bench, index=df.index)

    def stats(x):
        idx = (1 + x).cumprod()
        yrs = len(x) / 12
        return {
            "annual_return": r1((idx.iloc[-1] ** (1 / yrs) - 1) * 100),
            "volatility": r1(x.std() * math.sqrt(12) * 100),
            "max_drawdown": r1((idx / idx.cummax() - 1).min() * 100),
        }, idx

    ss, si = stats(s)
    bs, bi = stats(b)
    return {
        "series": [[d.strftime("%Y-%m"), r1(si[d] * 100), r1(bi[d] * 100)] for d in df.index],
        "strategy": ss, "benchmark": bs,
    }


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
