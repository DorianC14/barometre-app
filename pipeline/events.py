"""Grands événements de marché : liste historique sélectionnée à la main, puis détection automatique.

level : "major" (affiché en rouge) ou "minor" (affiché en noir).
zones : None = concerne toutes les zones ; sinon liste des zones concernées (le Monde affiche tout).
"""
from __future__ import annotations

import pandas as pd

import config as cfg

ALL = None
EU = ["europe", "france"]

# (date, libellé, niveau, zones)
HISTORY: list[tuple[str, str, str, list | None]] = [
    ("2007-02-27", "Krach éclair à Shanghai (−9 %), contagion mondiale", "minor", ALL),
    ("2007-08-09", "BNP Paribas gèle trois fonds : début de la crise des subprimes", "major", ALL),
    ("2008-03-16", "Rachat en urgence de Bear Stearns par JPMorgan", "minor", ALL),
    ("2008-07-11", "Pétrole au record historique, près de 147 $ le baril", "minor", ALL),
    ("2008-09-07", "Fannie Mae et Freddie Mac placées sous tutelle", "minor", ["us"]),
    ("2008-09-15", "Faillite de Lehman Brothers", "major", ALL),
    ("2008-10-08", "Baisse de taux coordonnée des grandes banques centrales", "minor", ALL),
    ("2008-11-25", "La Fed lance son premier programme de rachats d'actifs (QE1)", "minor", ALL),
    ("2009-03-09", "Point bas des Bourses après la crise financière", "major", ALL),
    ("2010-05-06", "Crise grecque et « flash crash » à Wall Street", "major", ALL),
    ("2010-11-03", "QE2 : nouveaux rachats d'obligations par la Fed", "minor", ["us", "world"]),
    ("2010-11-28", "Plan d'aide à l'Irlande", "minor", EU),
    ("2011-03-11", "Séisme, tsunami et accident de Fukushima", "major", ["jp", "world"]),
    ("2011-08-05", "Les États-Unis perdent leur note AAA chez S&P", "major", ALL),
    ("2011-11-03", "Mario Draghi arrive à la BCE et baisse les taux", "minor", EU),
    ("2012-07-26", "« Whatever it takes » : Mario Draghi sauve l'euro", "major", ALL),
    ("2012-09-13", "QE3 : rachats d'actifs illimités de la Fed", "minor", ["us", "world"]),
    ("2012-12-26", "Shinzo Abe Premier ministre : début des « Abenomics »", "minor", ["jp"]),
    ("2013-04-04", "Assouplissement monétaire massif de la Banque du Japon", "minor", ["jp", "world"]),
    ("2013-05-22", "« Taper tantrum » : la Fed évoque la fin du QE", "minor", ALL),
    ("2014-06-05", "La BCE passe son taux de dépôt en négatif", "minor", EU),
    ("2014-11-27", "L'OPEP maintient sa production : chute du pétrole", "minor", ALL),
    ("2015-01-15", "La BNS abandonne le plancher de l'euro contre le franc suisse", "minor", EU),
    ("2015-01-22", "La BCE lance son programme de rachats d'actifs (QE)", "minor", EU),
    ("2015-07-05", "Référendum grec : victoire du « non »", "minor", EU),
    ("2015-08-11", "Dévaluation surprise du yuan", "minor", ["cn", "world"]),
    ("2015-08-24", "« Lundi noir » : krach chinois et panique mondiale", "major", ALL),
    ("2015-12-16", "Première hausse des taux de la Fed depuis 2006", "minor", ["us", "world"]),
    ("2016-01-29", "La Banque du Japon adopte des taux négatifs", "minor", ["jp"]),
    ("2016-02-11", "Pétrole sous 30 $ et craintes de récession mondiale", "minor", ALL),
    ("2016-06-24", "Vote du Brexit", "major", ALL),
    ("2016-11-09", "Élection de Donald Trump", "minor", ALL),
    ("2017-05-07", "Élection d'Emmanuel Macron", "minor", EU),
    ("2017-12-22", "Réforme fiscale américaine : baisse de l'impôt sur les sociétés", "minor", ["us"]),
    ("2018-02-05", "« Volmageddon » : choc de volatilité à Wall Street", "minor", ["us", "world"]),
    ("2018-03-22", "Début de la guerre commerciale entre les États-Unis et la Chine", "minor", ALL),
    ("2018-05-29", "Crise politique italienne, envolée des taux italiens", "minor", EU),
    ("2018-11-17", "Début du mouvement des Gilets jaunes", "minor", ["france"]),
    ("2018-12-24", "Chute de fin 2018 (Fed et guerre commerciale)", "major", ALL),
    ("2019-07-31", "Première baisse des taux de la Fed depuis 2008", "minor", ["us", "world"]),
    ("2019-08-14", "Inversion de la courbe des taux américaine", "minor", ["us", "world"]),
    ("2019-09-17", "Tensions sur le marché monétaire américain (repo)", "minor", ["us"]),
    ("2020-01-23", "Confinement de Wuhan : premiers signaux du Covid-19", "minor", ["cn", "world"]),
    ("2020-02-24", "Le Covid-19 gagne l'Europe : début du krach", "minor", ALL),
    ("2020-03-16", "Covid-19 : krach de mars 2020", "major", ALL),
    ("2020-03-23", "La Fed promet des rachats illimités : point bas des marchés", "major", ALL),
    ("2020-04-20", "Le prix du pétrole américain (WTI) devient négatif", "minor", ALL),
    ("2020-07-21", "Plan de relance européen de 750 Md€", "minor", EU),
    ("2020-11-09", "Annonce du premier vaccin efficace contre le Covid-19", "major", ALL),
    ("2021-01-27", "Folie GameStop et des petits porteurs", "minor", ["us"]),
    ("2021-09-20", "Crise du promoteur chinois Evergrande", "minor", ["cn", "world"]),
    ("2021-11-30", "La Fed cesse de qualifier l'inflation de « transitoire »", "minor", ALL),
    ("2022-02-24", "Invasion de l'Ukraine par la Russie", "major", ALL),
    ("2022-03-08", "Pétrole et gaz au plus haut depuis 2008", "minor", ALL),
    ("2022-03-16", "La Fed relève ses taux pour la première fois depuis 2018", "minor", ["us", "world"]),
    ("2022-06-15", "Hausse de taux de 0,75 point par la Fed, une première depuis 1994", "minor", ALL),
    ("2022-07-21", "Première hausse des taux de la BCE depuis 2011", "minor", EU),
    ("2022-09-23", "Mini-budget britannique et crise des gilts", "minor", ALL),
    ("2022-10-12", "Pic d'inflation et des hausses de taux", "major", ALL),
    ("2022-11-11", "Faillite de la plateforme crypto FTX", "minor", ["us"]),
    ("2022-12-20", "La Banque du Japon élargit la marge de fluctuation des taux", "minor", ["jp"]),
    ("2023-03-10", "Faillite de Silicon Valley Bank", "major", ALL),
    ("2023-03-19", "Rachat en urgence de Credit Suisse par UBS", "minor", ALL),
    ("2023-05-01", "Faillite de First Republic Bank", "minor", ["us"]),
    ("2023-07-26", "Dernière hausse de taux de la Fed du cycle", "minor", ["us", "world"]),
    ("2023-09-14", "Dernière hausse de taux de la BCE du cycle", "minor", EU),
    ("2023-10-07", "Attaque du Hamas contre Israël", "minor", ALL),
    ("2023-10-19", "Le taux américain à 10 ans dépasse 5 %", "minor", ALL),
    ("2024-03-19", "La Banque du Japon sort des taux négatifs", "minor", ["jp", "world"]),
    ("2024-06-06", "Première baisse des taux de la BCE depuis 2019", "minor", EU),
    ("2024-06-09", "Dissolution de l'Assemblée nationale", "major", EU),
    ("2024-08-05", "Krach éclair au Japon (Nikkei −12 %), débouclage du carry trade", "major", ["jp", "world", "us"]),
    ("2024-09-18", "La Fed baisse ses taux de 0,5 point", "minor", ["us", "world"]),
    ("2024-09-24", "Plan de relance de la banque centrale chinoise", "minor", ["cn", "world"]),
    ("2024-11-05", "Réélection de Donald Trump", "minor", ALL),
    ("2024-12-04", "Censure du gouvernement Barnier", "minor", ["france"]),
    ("2025-01-27", "Choc DeepSeek sur les valeurs de l'intelligence artificielle", "minor", ["us", "world"]),
    ("2025-03-04", "L'Allemagne annonce un vaste plan d'investissement et de défense", "minor", EU),
    ("2025-04-02", "« Liberation Day » : droits de douane américains généralisés", "major", ALL),
    ("2025-04-09", "Pause de 90 jours sur les droits de douane : rebond historique", "minor", ALL),
    ("2025-05-12", "Trêve commerciale entre les États-Unis et la Chine", "minor", ["us", "cn", "world"]),
    ("2025-06-13", "Frappes israéliennes sur l'Iran, flambée du pétrole", "minor", ALL),
    ("2025-09-08", "Chute du gouvernement Bayrou", "minor", ["france"]),
    ("2025-09-17", "La Fed reprend la baisse de ses taux", "minor", ["us", "world"]),
]
CURATED_UNTIL = "2025-09-30"   # au-delà, les événements sont détectés automatiquement

INDEX_NAMES = {"spx": ("Le S&P 500", ["us", "world"]), "sx5e": ("L'Euro Stoxx 50", ["europe"]),
               "cac": ("Le CAC 40", ["france"]), "nikkei": ("Le Nikkei", ["jp"]),
               "shanghai": ("Le Shanghai Composite", ["cn"])}
BANKS = {"fed_funds": ("La Fed", ["us", "world"]), "ecb_dfr": ("La BCE", EU),
         "boj": ("La Banque du Japon", ["jp"]), "pboc": ("La banque centrale chinoise", ["cn"])}


def _pct(x: float) -> str:
    return f"{abs(x):.1f}".replace(".", ",")


def detect(R: dict, scores: dict, since: pd.Timestamp) -> list[dict]:
    """Événements repérés dans les données depuis `since` : décisions de taux, fortes séances,
    poussées de volatilité, chocs pétroliers et bonds du score."""
    out = []

    def add(d, label, level, zones):
        out.append({"date": pd.Timestamp(d).strftime("%Y-%m-%d"), "label": label, "level": level,
                    "zones": zones, "auto": True})

    for k, (name, zones) in BANKS.items():
        s = R.get(k)
        if s is None:
            continue
        s = s.dropna()
        s = s[s.index >= since - pd.Timedelta(days=10)]
        # taux effectif : on cherche les marches d'au moins 0,15 point sur 3 jours
        d = s.diff(3) if k == "fed_funds" else s.diff()
        step = 0.05 if k == "pboc" else 0.25     # la Chine bouge par pas de 0,05 à 0,10 point
        thr = 0.05 if k == "pboc" else 0.15
        last = None
        for t, v in d.items():
            if t < since or pd.isna(v) or abs(v) < thr or (last is not None and (t - last).days < 20):
                continue
            last = t
            sens = "relève" if v > 0 else "abaisse"
            size = f"{abs(round(v / step) * step):.2f}".rstrip("0").rstrip(".").replace(".", ",")
            add(t, f"{name} {sens} ses taux de {size} point", "major" if abs(v) >= 0.45 else "minor", zones)
    for k, (name, zones) in INDEX_NAMES.items():
        s = R.get(k)
        if s is None:
            continue
        s = s.dropna()
        r = s.pct_change() * 100
        r = r[s.index.to_series().diff().dt.days.le(4).values]   # séances consécutives seulement
        for t, v in r[r.index >= since].items():
            if abs(v) >= 3:
                verb = "chute" if v < 0 else "bondit"
                add(t, f"{name} {verb} de {_pct(v)} % en une séance", "major" if abs(v) >= 5 else "minor", zones)
    vix = R.get("vix")
    if vix is not None:
        v = vix.dropna()
        prev_hi = v.rolling(20).max().shift(1)
        for t in v[(v.index >= since) & (v >= 30) & (prev_hi < 30)].index:
            add(t, f"Poussée de peur à Wall Street : le VIX dépasse 30 ({v.loc[t]:.0f})", "major" if v.loc[t] >= 40 else "minor", ALL)
    brent = R.get("brent")
    if brent is not None:
        b = brent.dropna()
        r = (b.pct_change() * 100)[b.index.to_series().diff().dt.days.le(4).values]
        for t, v in r[r.index >= since].items():
            if abs(v) >= 8:
                add(t, f"Le pétrole {'s envole' if v > 0 else 'plonge'} de {_pct(v)} % en une séance".replace("s envole", "s'envole"),
                    "major" if abs(v) >= 12 else "minor", ALL)
    for region, T in scores.items():
        T = T.dropna()
        d5 = T.diff(5)
        last = None
        for t, v in d5[d5.index >= since].items():
            if abs(v) >= 20 and (last is None or (t - last).days > 10):
                last = t
                sens = "bondit" if v > 0 else "recule"
                add(t, f"Le score {cfg.REGIONS[region]} {sens} de {abs(v):.0f} points en 5 jours",
                    "major" if abs(v) >= 30 else "minor", [region])
    # un seul événement du même libellé par jour
    seen, uniq = set(), []
    for e in sorted(out, key=lambda e: e["date"]):
        key = (e["date"], e["label"])
        if key not in seen:
            seen.add(key)
            uniq.append(e)
    return uniq


def all_events(R: dict, scores: dict, today: pd.Timestamp) -> list[dict]:
    hist = [{"date": d, "label": l, "level": lv, "zones": z, "auto": False} for d, l, lv, z in HISTORY]
    since = max(pd.Timestamp(CURATED_UNTIL) + pd.Timedelta(days=1), today - pd.Timedelta(days=400))
    return hist + detect(R, scores, since)
