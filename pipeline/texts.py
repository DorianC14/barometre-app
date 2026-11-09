"""Textes générés automatiquement à partir des chiffres (sans IA) : signal du jour, explication
des piliers, causes et conséquences sur une période.

Plusieurs tournures sont prévues pour chaque phrase ; le choix dépend de la date et de la zone,
pour que les textes ne se répètent pas d'un jour à l'autre tout en restant stables dans la journée.
"""
from __future__ import annotations

import hashlib

import pandas as pd
from scipy.stats import norm

import config as cfg


# --------------------------------------------------------------------------- outils
def n(x: float, nd: int = 1) -> str:
    """Nombre au format français."""
    s = f"{x:.{nd}f}".replace("-", "−").replace(".", ",")
    return s


def sn(x: float, nd: int = 1) -> str:
    """Nombre signé au format français."""
    return ("+" if x > 0 else "") + n(x, nd)


def pick(options: list[str], *seed) -> str:
    h = int(hashlib.md5("|".join(map(str, seed)).encode()).hexdigest(), 16)
    return options[h % len(options)]


def cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def join(items: list[str]) -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " et " + items[-1]


def low(label: str) -> str:
    """Libellé en minuscule initiale, sauf sigle (« PIB », « OCDE »…)."""
    w = label.split(" (")[0]
    return w if len(w) > 1 and w[1].isupper() else w[:1].lower() + w[1:]


def level(t: float | None) -> str:
    if t is None:
        return "inconnu"
    if t >= 80:
        return "très tendu"
    if t >= 65:
        return "tendu"
    if t > 35:
        return "normal"
    if t > 20:
        return "porteur"
    return "très porteur"


def percentile(score: float) -> int:
    """Part des jours des 10 dernières années moins tendus que le score du jour."""
    return int(round(norm.cdf((score - 50) / cfg.CALIB_POINTS_PER_SD) * 100))


REGION_OF = {"world": "dans le monde", "europe": "en zone euro", "france": "en France",
             "us": "aux États-Unis", "cn": "en Chine", "jp": "au Japon"}


# --------------------------------------------------------------------------- un indicateur en mots
def describe(ind: dict, R: dict | None = None, region: str = "world") -> str:
    """Phrase courte qui décrit l'état d'un indicateur avec son chiffre clé."""
    i, v, t = ind["id"], ind.get("value"), ind.get("tension")
    comps = [c for c in ind.get("components", []) if c.get("available")]
    c0 = comps[0] if comps else {}
    if v is None:
        return ind["label"].split(" (")[0].lower()
    if i == "pib":
        return f"la croissance atteint {sn(v)} % sur un an"
    if i == "inflation":
        if v > 2.5:
            return f"l'inflation reste au-dessus de la cible, à {n(v)} %"
        if v < 1:
            return f"l'inflation est très basse ({n(v)} %), signe d'une demande faible"
        return f"l'inflation est proche de la cible, à {n(v)} %"
    if i == "cli":
        return f"l'indicateur avancé de l'OCDE est à {n(v)}, {'au-dessus de' if v >= 100 else 'sous'} sa tendance de 100"
    if i == "climat":
        q = {"très tendu": "très dégradés", "tendu": "dégradés", "normal": "dans la moyenne",
             "porteur": "bien orientés", "très porteur": "très bien orientés"}[level(t)]
        return f"le climat des affaires et la confiance sont {q}"
    if i == "chomage":
        return f"le chômage est à {n(v)} %"
    if i == "taux_directeur":
        return f"le taux directeur est à {n(v, 2)} %"
    if i == "taux_anticipe":
        if v > 0.25:
            return f"le marché anticipe des hausses de taux ({sn(v, 2)} pt)"
        if v < -0.25:
            return f"le marché anticipe des baisses de taux ({sn(v, 2)} pt)"
        return f"le marché n'anticipe pas de grand changement de taux ({sn(v, 2)} pt)"
    if i == "taux_10a":
        return f"le taux à 10 ans est à {n(v, 2)} %"
    if i == "pente":
        if v < 0:
            return f"la courbe des taux est inversée ({sn(v, 2)} pt), un signal historique de récession"
        return f"la courbe des taux est positive ({sn(v, 2)} pt)"
    if i == "ecart_souverain":
        return f"l'écart de taux avec l'Allemagne est de {n(v, 2)} pt"
    if i == "tendance":
        return f"les indices sont {n(abs(v))} % {'au-dessus de' if v >= 0 else 'sous'} leur moyenne 200 jours"
    if i == "valorisation":
        q = "chères" if t and t >= 65 else ("bon marché" if t is not None and t <= 35 else "correctement valorisées")
        if c0.get("name", "").startswith("CAPE"):
            return f"les actions sont {q} (CAPE de Shiller à {n(c0['value'])})"
        return f"les actions sont {q} ({n(c0.get('value', v), 2)} fois leur moyenne de 10 ans)"
    if i == "prime_risque":
        if v < 0:
            return f"la prime de risque des actions est négative ({sn(v, 2)} pt) : un placement sans risque rapporte plus que les bénéfices des entreprises"
        return f"la prime de risque des actions est de {sn(v, 2)} pt"
    if i == "change":
        return f"la devise s'écarte de {n(v)} % de sa moyenne d'un an"
    if i == "volatilite":
        return f"la volatilité ({c0.get('name', 'actions').split(' du ')[0].split(' 1 mois')[0]}) est à {n(v)}"
    if i == "brent":
        sgn = None
        if R is not None and "brent" in R:
            b = R["brent"].dropna()
            if len(b) > 64:
                sgn = (b.iloc[-1] / b.iloc[-64] - 1) * 100
        if sgn is not None:
            return f"le pétrole a {'pris' if sgn > 0 else 'perdu'} {n(abs(sgn), 0)} % en 3 mois"
        return f"le pétrole a varié de {n(v, 0)} % en 3 mois"
    if i == "spreads":
        return f"les écarts de crédit (spreads) sont à {n(v, 2)} pt"
    if i == "geopolitique":
        q = {"très tendu": "très élevés", "tendu": "élevés", "normal": "dans la norme",
             "porteur": "faibles", "très porteur": "très faibles"}[level(t)]
        return f"le risque géopolitique et l'incertitude politique sont {q}"
    if i == "or":
        return f"l'or a {'gagné' if v > 0 else 'perdu'} {n(abs(v), 0)} % en 3 mois"
    if i == "credit_impulse":
        return f"le crédit {'accélère' if v > 0 else 'ralentit'} ({sn(v)} pt de PIB)"
    if i == "conditions_fin":
        q = {"très tendu": "très tendues", "tendu": "tendues", "normal": "normales",
             "porteur": "détendues", "très porteur": "très détendues"}[level(t)]
        return f"les conditions de financement sont {q}"
    if i == "sentiment":
        q = "positif" if v > 0.05 else ("négatif" if v < -0.05 else "neutre")
        return f"le ton de la presse est {q}"
    return ind["label"].split(" (")[0].lower()


# --------------------------------------------------------------------------- signal du jour
def signal(region: str, score: float, score_7d: float | None, contributions: list, indicators: list,
           boosts: list, R: dict, today: str) -> list[str]:
    """Signal du jour en 3 lignes."""
    zone, _ = cfg.zone_of(score)
    ind = {i["id"]: i for i in indicators if i.get("available")}
    label = cfg.REGIONS[region]
    p = percentile(score)
    if score_7d is None:
        trend = ""
    elif score - score_7d >= 3:
        trend = pick([f", en hausse de {n(score - score_7d, 0)} points sur une semaine",
                      f", {n(score - score_7d, 0)} points de plus qu'il y a 7 jours"], today, region, "up")
    elif score_7d - score >= 3:
        trend = pick([f", en baisse de {n(score_7d - score, 0)} points sur une semaine",
                      f", {n(score_7d - score, 0)} points de moins qu'il y a 7 jours"], today, region, "down")
    else:
        trend = pick([", stable sur une semaine", ", peu changé sur 7 jours"], today, region, "flat")
    l1 = (f"{label} : {zone.lower()} ({n(score, 0)}/100){trend}. "
          + pick([f"La tension est plus forte que {p} % des jours des dix dernières années.",
                  f"Seuls {100 - p} % des jours des dix dernières années ont été plus tendus.",
                  f"C'est plus tendu que {p} % des séances de la dernière décennie."], today, region, "p")
          if p >= 50 else
          f"{label} : {zone.lower()} ({n(score, 0)}/100){trend}. "
          + pick([f"La tension est plus faible que {100 - p} % des jours des dix dernières années.",
                  f"C'est plus calme que {100 - p} % des séances de la dernière décennie."], today, region, "p"))

    up = [c for c in contributions if (c["contribution"] or 0) > 0.3 and c["id"] in ind][:2]
    down = [c for c in contributions if (c["contribution"] or 0) < -0.3 and c["id"] in ind][:2]
    if up:
        opener = pick(["Ce qui tend le marché : ", "Principales sources d'inquiétude : ",
                       "La tension vient surtout de là : "], today, region, "o1")
        l2 = opener + join([describe(ind[c["id"]], R, region) for c in up]) + "."
    else:
        l2 = "Aucun indicateur ne tire franchement la tension vers le haut."
    if down:
        opener = pick(["En face, ", "À l'inverse, ", "Côté soutiens, "], today, region, "o2")
        l3 = opener + join([describe(ind[c["id"]], R, region) for c in down]) + "."
    else:
        l3 = "Peu de soutiens visibles pour l'instant."
    if boosts:
        b = max(boosts, key=lambda x: x["multiplier"])
        l3 += f" À surveiller : le poids de « {b['label'].split(' (')[0].lower()} » est relevé de {n((b['multiplier'] - 1) * 100, 0)} % après un mouvement brutal."
    else:
        l3 += " " + {
            "Euphorie": "Prudence face aux excès : c'est souvent dans ces phases que les corrections se préparent.",
            "Favorable": "Le contexte reste porteur pour les actifs risqués.",
            "Neutre": "Les signaux se compensent : un portefeuille équilibré reste adapté.",
            "Prudence": "Le moment invite à réduire le risque et à garder des liquidités.",
            "Stress": "Priorité à la protection du capital.",
        }[zone]
    return [l1, l2, l3]


# --------------------------------------------------------------------------- piliers
MEANING = {
    "macro": {"tense": "En clair : l'économie réelle ralentit ou s'écarte de son équilibre, ce qui pèse sur les bénéfices des entreprises.",
              "normal": "En clair : l'économie réelle tourne à un rythme habituel, sans signal d'alerte particulier.",
              "calm": "En clair : l'économie réelle est solide, un appui pour les bénéfices des entreprises."},
    "bc": {"tense": "En clair : l'argent coûte cher, ce qui freine le crédit, l'immobilier et la valorisation des actions.",
           "normal": "En clair : la politique monétaire n'est ni un frein ni un moteur marqué.",
           "calm": "En clair : l'argent est bon marché, ce qui soutient le crédit, l'immobilier et les actions."},
    "marches": {"tense": "En clair : les marchés montrent des signes de fatigue ou d'excès de prix, la marge de sécurité est faible.",
                "normal": "En clair : les marchés évoluent sans excès dans un sens ou dans l'autre.",
                "calm": "En clair : la dynamique des marchés est bonne et les prix ne sont pas excessifs."},
    "risque": {"tense": "En clair : les investisseurs se protègent, les chocs ont plus de chances de se propager.",
               "normal": "En clair : le niveau de risque perçu est habituel.",
               "calm": "En clair : la peur est faible ; attention toutefois à la complaisance."},
    "flux": {"tense": "En clair : l'argent circule moins facilement et le ton de l'actualité est morose.",
             "normal": "En clair : le crédit et le sentiment ne donnent pas de signal fort.",
             "calm": "En clair : le crédit circule bien et l'actualité est plutôt bien orientée."},
}


def pillar_text(pillar: dict, normal: float | None, indicators: list, R: dict, region: str, today: str) -> list[str]:
    """3 lignes d'explication pour un pilier."""
    pid, score = pillar["id"], pillar["score"]
    inds = [i for i in indicators if i["pillar"] == pid and i.get("available") and i.get("tension") is not None]
    if score is None or not inds:
        return ["Données insuffisantes pour ce pilier aujourd'hui."]
    names = join([low(i["label"]) for i in inds])
    if normal is not None:
        gap = score - normal
        rel = (f"au-dessus de sa moyenne des dix dernières années ({n(normal, 0)})" if gap >= 5 else
               f"sous sa moyenne des dix dernières années ({n(normal, 0)})" if gap <= -5 else
               f"proche de sa moyenne des dix dernières années ({n(normal, 0)})")
    else:
        rel = ""
    d7 = pillar.get("score_7d")
    move = ""
    if d7 is not None and abs(score - d7) >= 2:
        move = f", {'en hausse' if score > d7 else 'en baisse'} de {n(abs(score - d7), 0)} points sur 7 jours"
    l1 = (pick([f"Note de {n(score, 0)}/100, {rel}{move}.", f"Avec {n(score, 0)}/100, le pilier est {rel}{move}."],
               today, region, pid) + f" Il regroupe : {names}.")
    hi = max(inds, key=lambda i: i["tension"])
    lo = min(inds, key=lambda i: i["tension"])
    th, tl = hi["tension"], lo["tension"]
    if th >= 60:
        tail = f"c'est l'élément le plus tendu du pilier ({n(th, 0)}/100)"
    elif th >= 40:
        tail = f"c'est le point le moins favorable du pilier, sans être alarmant ({n(th, 0)}/100)"
    else:
        tail = f"même le point le moins favorable du pilier reste détendu ({n(th, 0)}/100)"
    l2 = cap(describe(hi, R, region)) + " : " + tail + "."
    if lo["id"] != hi["id"]:
        if tl <= 45:
            l2 += " " + pick(["À l'inverse, ", "En revanche, ", "Côté positif, "], today, region, pid, "lo") \
                  + describe(lo, R, region) + f" ({n(tl, 0)}/100)."
        else:
            l2 += f" Même le point le plus favorable reste un peu tendu : {describe(lo, R, region)} ({n(tl, 0)}/100)."
    key = "tense" if score >= 60 else ("calm" if score <= 40 else "normal")
    return [l1, l2, MEANING[pid][key]]


# --------------------------------------------------------------------------- historique : causes et conséquences
RANGES = {"1M": 31, "6M": 183, "1A": 366, "3A": 1096, "10A": 3653, "Tout": None}
PILLAR_WORD = {"macro": "la macroéconomie", "bc": "les banques centrales et les taux", "marches": "les marchés",
               "risque": "le risque et la géopolitique", "flux": "le crédit et le sentiment"}
MAIN_INDEX = {"world": ("spx", "le S&P 500"), "europe": ("sx5e", "l'Euro Stoxx 50"), "france": ("cac", "le CAC 40"),
              "us": ("spx", "le S&P 500"), "cn": ("shanghai", "le Shanghai Composite"), "jp": ("nikkei", "le Nikkei")}
MAIN_YIELD = {"world": ("us_10y", "le taux américain à 10 ans"), "europe": ("ea_10y", "le taux à 10 ans de la zone euro"),
              "france": ("oat_10y", "l'OAT à 10 ans"), "us": ("us_10y", "le taux à 10 ans"),
              "jp": ("jp_10y", "le taux japonais à 10 ans"), "cn": ("pboc", "le taux directeur chinois")}


def _at(s: pd.Series | None, d: pd.Timestamp):
    if s is None:
        return None
    s = s.dropna()
    s = s[s.index <= d]
    return float(s.iloc[-1]) if len(s) else None


def period_texts(region: str, T: pd.Series, T_pillars: pd.DataFrame, ind_F: dict, R: dict,
                 events: list, start_hist: str) -> dict:
    """Pour chaque période de l'onglet Historique : ce qui a changé, pourquoi, avec quelles conséquences."""
    out = {}
    T = T.dropna()
    if T.empty:
        return out
    end = T.index[-1]
    for k, days in RANGES.items():
        start = max(pd.Timestamp(start_hist), end - pd.Timedelta(days=days)) if days else pd.Timestamp(start_hist)
        seg = T[T.index >= start]
        if len(seg) < 5:
            continue
        a, b = float(seg.iloc[0]), float(seg.iloc[-1])
        d = b - a
        za, zb = cfg.zone_of(a)[0], cfg.zone_of(b)[0]
        hi_d, lo_d = seg.idxmax(), seg.idxmin()
        if abs(d) < 3:
            s1 = f"Sur la période, le score est globalement stable ({n(a, 0)} → {n(b, 0)}), mais il a oscillé entre {n(seg.min(), 0)} et {n(seg.max(), 0)}."
        else:
            s1 = (f"Sur la période, le score {'monte' if d > 0 else 'baisse'} de {n(abs(d), 0)} points ({n(a, 0)} → {n(b, 0)})"
                  + (f" et passe de la zone « {za.lower()} » à « {zb.lower()} »." if za != zb else f" et reste en zone « {zb.lower()} ».")
                  )
        # causes : piliers et indicateurs qui ont le plus bougé
        pch = {}
        for p in T_pillars.columns:
            pa, pb = _at(T_pillars[p], seg.index[0]), _at(T_pillars[p], end)
            if pa is not None and pb is not None:
                pch[p] = pb - pa
        causes = sorted(pch.items(), key=lambda x: -abs(x[1]))[:2]
        cs = [f"{PILLAR_WORD[p]} ({sn(v, 0)} pts)" for p, v in causes if abs(v) >= 3]
        ich = {}
        for i, F in ind_F.items():
            fa, fb = _at(F, seg.index[0]), _at(F, end)
            if fa is not None and fb is not None:
                ich[i] = (100 - fb) - (100 - fa)
        top_i = sorted(ich.items(), key=lambda x: -abs(x[1]))[:2]
        lab = {x["id"]: x["label"] for x in cfg.INDICATORS}
        is_ = [f"{low(lab[i])} ({'plus' if v > 0 else 'moins'} tendu de {n(abs(v), 0)} pts)" for i, v in top_i if abs(v) >= 5]
        if cs:
            s2 = "Principales causes : " + join(cs) + (", en particulier " + join(is_) if is_ else "") + "."
        elif is_:
            s2 = "Ce sont surtout des indicateurs isolés qui ont bougé : " + join(is_) + "."
        else:
            s2 = "Aucun pilier n'a beaucoup bougé : les variations se compensent."
        evs = [e for e in events if e["date"] >= seg.index[0].strftime("%Y-%m-%d")
               and (e.get("zones") is None or region in e["zones"])]
        majors = [e for e in evs if e["level"] == "major"]
        if days and days <= 366:
            shown = (majors or evs)[-3:]
        else:   # sur longue période : les grands événements de la liste historique
            shown = [e for e in majors if not e.get("auto")][-4:] or majors[-3:]
        s3 = ("Événements marquants : " + " ; ".join(f"{e['label']} ({pd.Timestamp(e['date']).strftime('%d/%m/%Y')})" for e in shown) + ".") if shown else ""
        # conséquences sur les marchés
        cons = []
        ik, iname = MAIN_INDEX[region]
        x0, x1 = _at(R.get(ik), seg.index[0]), _at(R.get(ik), end)
        if x0 and x1:
            cons.append(f"{iname} {sn((x1 / x0 - 1) * 100, 0)} %")
        yk, yname = MAIN_YIELD[region]
        y0, y1 = _at(R.get(yk), seg.index[0]), _at(R.get(yk), end)
        if y0 is not None and y1 is not None:
            cons.append(f"{yname} {sn(y1 - y0, 2)} pt")
        g0, g1 = _at(R.get("gold"), seg.index[0]), _at(R.get("gold"), end)
        if g0 and g1:
            cons.append(f"l'or {sn((g1 / g0 - 1) * 100, 0)} %")
        b0, b1 = _at(R.get("brent"), seg.index[0]), _at(R.get("brent"), end)
        if b0 and b1:
            cons.append(f"le pétrole {sn((b1 / b0 - 1) * 100, 0)} %")
        s4 = ("Conséquences sur les marchés : " + join(cons) + ".") if cons else ""
        s5 = (f"Pic de tension le {hi_d.strftime('%d/%m/%Y')} ({n(seg.max(), 0)}), point le plus calme le {lo_d.strftime('%d/%m/%Y')} ({n(seg.min(), 0)}).")
        out[k] = " ".join(x for x in [s1, s2, s3, s4, s5] if x)
    return out
