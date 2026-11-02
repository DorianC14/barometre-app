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


# --------------------------------------------------------------------------- calcul par région
def compute_region(R: dict, region: str, index: pd.DatetimeIndex, sources_used: dict, today: pd.Timestamp):
    indicators_out = []
    ind_F = {}
    ind_weights = {}
    ind_pillar = {}
    composites = {}

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
        # composite brut (mêmes unités) pour le régime et les règles de conseil
        rawf = pd.DataFrame({k: _daily(v) for k, v in comp_raw.items()})
        composites[ind["id"]] = weighted_mean(rawf, comp_w).dropna()
        srcs = sorted({sources_used.get(k, "") for k in _series_used(ind, region)} - {""})
        indicators_out.append({
            **_ind_meta(ind),
            "available": True,
            "tension": r1(100 - F_ind.iloc[-1]),
            "tension_7d": r1(100 - F_ind.iloc[-8]) if len(F_ind) > 8 else None,
            "components": comp_out,
            "sources": [cfg.SOURCE_LABELS.get(s, s) for s in srcs],
        })

    # ---- piliers
    pillar_F = {}
    for p in cfg.PILLAR_ORDER:
        ids = [i for i, pp in ind_pillar.items() if pp == p]
        if ids:
            pillar_F[p] = weighted_mean(pd.DataFrame({i: ind_F[i] for i in ids}), ind_weights)
    pw = {p: cfg.PILLARS[p]["weight"] for p in pillar_F}
    PF = pd.DataFrame(pillar_F)
    global_F = weighted_mean(PF, pw)
    T = 100 - global_F
    T_pillars = 100 - PF

    # ---- variantes de robustesse
    eq_T = 100 - weighted_mean(PF, {p: 1 for p in PF.columns})
    pca_T, pca_w = _pca_variant(ind_F)

    # ---- contributions à la date du jour : c_i = W_p × v_i × (T_i − 50)
    last = index[-1]
    wp_eff = effective_weights(PF.loc[last], pw)
    contributions = []
    for p, Wp in wp_eff.items():
        ids = [i for i, pp in ind_pillar.items() if pp == p and pd.notna(ind_F[i].loc[last])]
        vi = effective_weights(pd.Series({i: ind_F[i].loc[last] for i in ids}), ind_weights)
        for i, v in vi.items():
            Ti = 100 - ind_F[i].loc[last]
            contributions.append({
                "id": i, "label": _label(i), "pillar": p,
                "weight": r1(Wp * v * 100, 1),
                "tension": r1(Ti),
                "contribution": r1(Wp * v * (Ti - 50), 2),
            })
    contributions.sort(key=lambda c: -abs(c["contribution"] or 0))

    return {
        "T": T, "T_pillars": T_pillars, "eq_T": eq_T, "pca_T": pca_T, "pca_w": pca_w,
        "indicators": indicators_out, "contributions": contributions,
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
    df = pd.DataFrame(ind_F).dropna()
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


# --------------------------------------------------------------------------- conseils
def advice_rules(res: dict) -> list:
    comp = res["composites"]
    tens = {i["id"]: i.get("tension") for i in res["indicators"] if i.get("available")}
    rules = []

    def last(k):
        s = comp.get(k)
        return None if s is None or s.empty else float(s.iloc[-1])

    ta = last("taux_anticipe")
    if ta is not None and ta < -0.25:
        rules.append(("Baisse de taux anticipée", f"Le marché anticipe une baisse des taux directeurs ({ta:+.2f} pt).",
                      "Obligations longues et valeurs de croissance favorisées."))
    elif ta is not None and ta > 0.25:
        rules.append(("Hausse de taux anticipée", f"Le marché anticipe une hausse des taux directeurs ({ta:+.2f} pt).",
                      "Obligations courtes, banques et valeurs « value » favorisées."))
    b = last("brent")
    if b is not None and b > 15:
        rules.append(("Pétrole en forte hausse", f"Le Brent a pris {b:.0f} % en 3 mois.",
                      "Énergie favorisée ; transport aérien et consommation pénalisés."))
    elif b is not None and b < -15:
        rules.append(("Pétrole en forte baisse", f"Le Brent a perdu {abs(b):.0f} % en 3 mois.",
                      "Transport et consommation soutenus ; énergie pénalisée."))
    pe = last("pente")
    if pe is not None and pe < 0:
        rules.append(("Courbe des taux inversée", f"Le 10 ans est sous le 2 ans ({pe:+.2f} pt) : signal historique de récession.",
                      "Réduire les valeurs cycliques, privilégier la qualité."))
    if (tens.get("geopolitique") or 0) > 70:
        rules.append(("Risque géopolitique élevé", "L'incertitude géopolitique est au-dessus de sa norme.",
                      "Renforcer l'or et le secteur de la défense."))
    if (tens.get("valorisation") or 0) > 75:
        rules.append(("Actions chères", "La valorisation des actions est élevée par rapport à son historique.",
                      "Rester sélectif, privilégier les valeurs à dividende et la diversification."))
    if (tens.get("volatilite") or 0) > 75:
        rules.append(("Volatilité forte", "La volatilité implicite est nettement au-dessus de la normale.",
                      "Réduire l'effet de levier et étaler les achats dans le temps."))
    return [{"title": t, "why": w, "idea": i} for t, w, i in rules]


# --------------------------------------------------------------------------- test historique indicatif
def backtest(T: pd.Series, R: dict, region: str) -> dict | None:
    """Allocation dynamique selon la zone (mois précédent) vs portefeuille fixe 60/40, rendements approximés."""
    try:
        if region == "world":
            eq = 0.6 * R["spx"].resample("ME").last().pct_change() + 0.4 * R["sx5e"].resample("ME").last().pct_change()
            y = _daily(R["us_10y"]).resample("ME").last()
            cash = _daily(R["fed_funds"]).resample("ME").last() / 1200
        else:
            eq = 0.5 * R["sx5e"].resample("ME").last().pct_change() + 0.5 * R["cac"].resample("ME").last().pct_change()
            y = _daily(R["ea_10y"]).resample("ME").last()
            cash = _daily(R["ecb_dfr"]).resample("ME").last() / 1200
        bond = y.shift(1) / 1200 - 8 * (y - y.shift(1)) / 100
        gold = R["gold"].resample("ME").last().pct_change()
    except KeyError:
        return None
    sig = T.resample("ME").last().shift(1)
    df = pd.DataFrame({"eq": eq, "bond": bond, "gold": gold, "cash": cash, "sig": sig}).dropna()
    df = df[df.index >= cfg.HISTORY_START]
    if len(df) < 24:
        return None
    strat, bench = [], []
    for _, row in df.iterrows():
        a = cfg.ALLOCATION[cfg.zone_of(row["sig"])[0]]
        strat.append(a["Actions"] / 100 * row["eq"] + a["Obligations"] / 100 * row["bond"]
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


# --------------------------------------------------------------------------- phrase du jour
def signal_sentence(score: float, contributions: list) -> str:
    zone, _ = cfg.zone_of(score)
    up = [c["label"].split(" (")[0].lower() for c in contributions if (c["contribution"] or 0) > 0.3][:2]
    down = [c["label"].split(" (")[0].lower() for c in contributions if (c["contribution"] or 0) < -0.3][:2]
    parts = [f"{zone} ({score:.0f}/100)."]
    if up:
        parts.append("Tension alimentée surtout par : " + " et ".join(up) + ".")
    if down:
        parts.append("Soutiens principaux : " + " et ".join(down) + ".")
    return " ".join(parts)


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
