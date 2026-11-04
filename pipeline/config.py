"""Définition du baromètre : séries brutes, indicateurs, piliers et pondérations.

Toute la méthodologie chiffrée est ici, pour pouvoir la modifier sans toucher au code.
"""
from __future__ import annotations

import pandas as pd

from transforms import chg, dev1y, impulse, inv_yield, ma_gap, mean_window, price_to_trend, spread, yoy

# ---------------------------------------------------------------------------
# 1. Séries brutes : nom interne -> liste de sources (la première qui répond gagne)
#    Une source = (type, identifiant[, options]). "market" = rafraîchie toutes les 15 min.
# ---------------------------------------------------------------------------
SERIES: dict[str, dict] = {
    # --- Macro (FRED, CSV public sans clé)
    "us_gdp": {"src": [("fred", "GDPC1")]},
    "jp_gdp": {"src": [("fred", "JPNRGDPEXP")]},
    "ea_gdp": {"src": [("fred", "CLVMNACSCAB1GQEA19")]},
    "fr_gdp": {"src": [("fred", "CLVMNACSCAB1GQFR"), ("insee", "010565708")]},
    "us_cpi": {"src": [("fred", "CPIAUCSL")]},
    "ea_hicp": {"src": [("fred", "CP0000EZ19M086NEST")]},
    "fr_cpi": {"src": [("fred", "CP0000FRM086NEST"), ("insee", "001759970")]},
    "us_unemp": {"src": [("fred", "UNRATE")]},
    "ea_unemp": {"src": [("eurostat", "une_rt_m", {"geo": "EA21", "s_adj": "SA", "age": "TOTAL", "sex": "T", "unit": "PC_ACT"}), ("fred", "LRHUTTTTEZM156S"), ("eurostat", "une_rt_m", {"geo": "EA20", "s_adj": "SA", "age": "TOTAL", "sex": "T", "unit": "PC_ACT"})]},
    "fr_unemp": {"src": [("eurostat", "une_rt_m", {"geo": "FR", "s_adj": "SA", "age": "TOTAL", "sex": "T", "unit": "PC_ACT"}), ("fred", "LRHUTTTTFRM156S")]},
    "cli_us": {"src": [("oecd", "USA")]},
    "cli_cn": {"src": [("oecd", "CHN")]},
    "cli_jp": {"src": [("oecd", "JPN")]},
    "cli_ea": {"src": [("oecd", "EA20"), ("oecd", "G4E")]},
    "cli_fr": {"src": [("oecd", "FRA")]},
    "esi_ea": {"src": [("eurostat", "ei_bssi_m_r2", {"geo": "EA21", "indic": "BS-ESI-I", "s_adj": "SA"}),
                       ("eurostat", "ei_bssi_m_r2", {"geo": "EA20", "indic": "BS-ESI-I", "s_adj": "SA"})]},
    "fr_climat": {"src": [("insee", "001565530")]},
    # --- Banques centrales et taux
    "fed_funds": {"src": [("fred", "DFF")]},
    "ecb_dfr": {"src": [("fred", "ECBDFR"), ("ecb", "FM/D.U2.EUR.4F.KR.DFR.LEV")]},
    "us_2y": {"src": [("fred", "DGS2")]},
    "us_10y": {"src": [("yahoo", "^TNX"), ("fred", "DGS10")], "market": True},
    "ea_2y": {"src": [("ecb", "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y")]},
    "ea_10y": {"src": [("ecb", "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y")]},
    "oat_10y": {"src": [("fred", "IRLTLT01FRM156N")]},
    "bund_10y": {"src": [("fred", "IRLTLT01DEM156N")]},
    # --- Marchés (Yahoo en continu, Stooq / FRED en secours)
    "spx": {"src": [("twelvedata", "SPX"), ("yahoo", "^GSPC"), ("fred", "SP500")], "market": True},
    "ndx": {"src": [("twelvedata", "IXIC"), ("yahoo", "^IXIC"), ("fred", "NASDAQCOM")], "market": True},
    "nikkei": {"src": [("yahoo", "^N225"), ("fred", "NIKKEI225")], "market": True},
    "shanghai": {"src": [("twelvedata", "000001:SSE"), ("yahoo", "000001.SS"), ("twelvedata", "MCHI")], "market": True},
    "sx5e": {"src": [("twelvedata", "SX5E"), ("yahoo", "^STOXX50E"), ("stoxx", "h_3msx5e"), ("twelvedata", "FEZ")], "market": True},
    "cac": {"src": [("twelvedata", "FCHI"), ("yahoo", "^FCHI"), ("twelvedata", "EWQ")], "market": True},
    "eurusd": {"src": [("yahoo", "EURUSD=X"), ("ecb", "EXR/D.USD.EUR.SP00.A"), ("fred", "DEXUSEU")], "market": True},
    "dxy": {"src": [("yahoo", "DX-Y.NYB"), ("fred", "DTWEXBGS")], "market": True},
    "gold": {"src": [("twelvedata", "XAU/USD"), ("yahoo", "GC=F")], "market": True},
    "cape": {"src": [("multpl", "shiller-pe")]},
    "spx_pe": {"src": [("multpl", "s-p-500-pe-ratio")]},
    # --- Risque
    "vix": {"src": [("yahoo", "^VIX"), ("fred", "VIXCLS")], "market": True},
    "vstoxx": {"src": [("stoxx", "h_v2tx"), ("yahoo", "^V2TX")], "market": True},
    "brent": {"src": [("yahoo", "BZ=F"), ("fred", "DCOILBRENTEU")], "market": True},
    "us_hy": {"src": [("fred", "BAMLH0A0HYM2")]},
    "eu_hy": {"src": [("fred", "BAMLHE00EHYIOAS")]},
    "gpr": {"src": [("gpr", "daily")]},
    "epu_global": {"src": [("fred", "GEPUCURRENT")]},
    "epu_europe": {"src": [("fred", "EUEPUINDXM"), ("epu", "European")]},
    "epu_fr": {"src": [("epu", "France"), ("fred", "FRAEPUINDXM")]},
    # --- Flux et conditions financières
    "credit_us": {"src": [("fred", "QUSPAM770A")]},
    "credit_cn": {"src": [("fred", "QCNPAM770A")]},
    "credit_ea": {"src": [("fred", "QXMPAM770A")]},
    "nfci": {"src": [("fred", "NFCI")]},
    "ciss": {"src": [("ecb", "CISS/D.U2.Z0Z.4F.EC.SS_CIN.IDX")]},
}

SOURCE_LABELS = {
    "fred": "FRED (Fed de Saint-Louis)",
    "ecb": "BCE Data Portal",
    "eurostat": "Eurostat",
    "insee": "INSEE",
    "oecd": "OCDE",
    "yahoo": "Yahoo Finance",
    "stooq": "Stooq",
    "stoxx": "STOXX (fichiers officiels)",
    "twelvedata": "Twelve Data (API)",
    "epu": "Economic Policy Uncertainty (Baker, Bloom, Davis)",
    "multpl": "multpl (données Shiller)",
    "gpr": "Caldara & Iacoviello (GPR)",
    "news": "Presse (flux RSS)",
}

# ---------------------------------------------------------------------------
# 2. Piliers et pondérations (somme = 1)
# ---------------------------------------------------------------------------
PILLARS = {
    "bc": {"label": "Banques centrales", "weight": 0.25},
    "risque": {"label": "Risque et géopolitique", "weight": 0.20},
    "marches": {"label": "Marchés", "weight": 0.20},
    "macro": {"label": "Macro", "weight": 0.20},
    "flux": {"label": "Flux et sentiment", "weight": 0.15},
}
PILLAR_ORDER = ["macro", "bc", "marches", "risque", "flux"]

REGIONS = {"world": "Monde", "europe": "Europe / France"}

# Poids des zones dans le score Monde (part approximative du PIB mondial, FMI)
GDP_W = {"us": 0.26, "ea": 0.15, "cn": 0.17, "jp": 0.04}


def C(name: str, fn, weight: float = 1.0, unit: str | None = None) -> dict:
    """Composante d'un indicateur : fn(R) -> série brute affichée."""
    return {"name": name, "fn": fn, "weight": weight, "unit": unit}


# ---------------------------------------------------------------------------
# 3. Indicateurs. direction : +1 = une hausse est favorable aux marchés,
#    -1 = défavorable, "target" = distance à la cible de 2 % (inflation).
#    "weight" = poids dans le pilier (1 par défaut, 2 pour le taux anticipé).
# ---------------------------------------------------------------------------
INDICATORS: list[dict] = [
    # ======================= MACRO
    {
        "id": "pib", "label": "Croissance du PIB", "pillar": "macro", "direction": 1,
        "unit": "% sur 1 an", "freq": "Trimestrielle",
        "world": [C("États-Unis", lambda R: yoy(R["us_gdp"]), GDP_W["us"]),
                  C("Zone euro", lambda R: yoy(R["ea_gdp"]), GDP_W["ea"]),
                  C("Japon", lambda R: yoy(R["jp_gdp"]), GDP_W["jp"])],
        "europe": [C("Zone euro", lambda R: yoy(R["ea_gdp"])),
                   C("France", lambda R: yoy(R["fr_gdp"]))],
    },
    {
        "id": "inflation", "label": "Inflation", "pillar": "macro", "direction": "target",
        "unit": "% sur 1 an", "freq": "Mensuelle",
        "world": [C("États-Unis (CPI)", lambda R: yoy(R["us_cpi"]), 0.6),
                  C("Zone euro (HICP)", lambda R: yoy(R["ea_hicp"]), 0.4)],
        "europe": [C("Zone euro (HICP)", lambda R: yoy(R["ea_hicp"])),
                   C("France (IPCH)", lambda R: yoy(R["fr_cpi"]))],
    },
    {
        "id": "cli", "label": "Indicateur avancé OCDE (proxy PMI)", "pillar": "macro", "direction": 1,
        "unit": "indice (100 = tendance)", "freq": "Mensuelle",
        "world": [C("États-Unis", lambda R: R["cli_us"], GDP_W["us"]),
                  C("Chine", lambda R: R["cli_cn"], GDP_W["cn"]),
                  C("Europe (grands pays, OCDE)", lambda R: R["cli_ea"], GDP_W["ea"]),
                  C("Japon", lambda R: R["cli_jp"], GDP_W["jp"])],
        "europe": [C("Europe (grands pays, OCDE)", lambda R: R["cli_ea"]),
                   C("France", lambda R: R["cli_fr"])],
    },
    {
        "id": "climat", "label": "Climat des affaires", "pillar": "macro", "direction": 1,
        "unit": "indice (100 = moyenne)", "freq": "Mensuelle",
        "europe": [C("Sentiment économique zone euro", lambda R: R["esi_ea"]),
                   C("Climat des affaires France (INSEE)", lambda R: R["fr_climat"])],
    },
    {
        "id": "chomage", "label": "Chômage", "pillar": "macro", "direction": -1,
        "unit": "% de la population active", "freq": "Mensuelle",
        "world": [C("États-Unis", lambda R: R["us_unemp"], 0.6),
                  C("Zone euro", lambda R: R["ea_unemp"], 0.4)],
        "europe": [C("Zone euro", lambda R: R["ea_unemp"]),
                   C("France", lambda R: R["fr_unemp"])],
    },
    # ======================= BANQUES CENTRALES
    {
        "id": "taux_directeur", "label": "Taux directeur", "pillar": "bc", "direction": -1,
        "unit": "%", "freq": "À chaque réunion",
        "world": [C("Fed (Fed funds)", lambda R: R["fed_funds"], 0.6),
                  C("BCE (taux de dépôt)", lambda R: R["ecb_dfr"], 0.4)],
        "europe": [C("BCE (taux de dépôt)", lambda R: R["ecb_dfr"])],
    },
    {
        "id": "taux_anticipe", "label": "Taux directeur anticipé (2 ans − taux directeur)", "pillar": "bc",
        "direction": -1, "weight": 2, "unit": "points de %", "freq": "Quotidienne",
        "world": [C("Treasury 2 ans − Fed funds", lambda R: spread(R["us_2y"], R["fed_funds"]))],
        "europe": [C("Taux 2 ans zone euro − dépôt BCE", lambda R: spread(R["ea_2y"], R["ecb_dfr"]))],
    },
    {
        "id": "taux_10a", "label": "Taux souverain 10 ans", "pillar": "bc", "direction": -1,
        "unit": "%", "freq": "Quotidienne",
        "world": [C("Treasury 10 ans", lambda R: R["us_10y"])],
        "europe": [C("Taux 10 ans zone euro (AAA)", lambda R: R["ea_10y"]),
                   C("OAT 10 ans", lambda R: R["oat_10y"])],
    },
    {
        "id": "pente", "label": "Pente de la courbe (10 ans − 2 ans)", "pillar": "bc", "direction": 1,
        "unit": "points de %", "freq": "Quotidienne",
        "world": [C("États-Unis", lambda R: spread(R["us_10y"], R["us_2y"]))],
        "europe": [C("Zone euro", lambda R: spread(R["ea_10y"], R["ea_2y"]))],
    },
    {
        "id": "oat_bund", "label": "Écart OAT − Bund 10 ans", "pillar": "bc", "direction": -1,
        "unit": "points de %", "freq": "Mensuelle",
        "europe": [C("France − Allemagne", lambda R: spread(R["oat_10y"], R["bund_10y"]))],
    },
    # ======================= MARCHÉS
    {
        "id": "tendance", "label": "Tendance des indices (écart à la moyenne 200 jours)", "pillar": "marches",
        "direction": 1, "unit": "%", "freq": "Continue",
        "world": [C("S&P 500", lambda R: ma_gap(R["spx"]), 0.35),
                  C("Nasdaq", lambda R: ma_gap(R["ndx"]), 0.15),
                  C("Euro Stoxx 50", lambda R: ma_gap(R["sx5e"]), 0.20),
                  C("Shanghai", lambda R: ma_gap(R["shanghai"]), 0.18),
                  C("Nikkei 225", lambda R: ma_gap(R["nikkei"]), 0.12)],
        "europe": [C("Euro Stoxx 50", lambda R: ma_gap(R["sx5e"])),
                   C("CAC 40", lambda R: ma_gap(R["cac"]))],
    },
    {
        "id": "valorisation", "label": "Valorisation des actions", "pillar": "marches", "direction": -1,
        "unit": "ratio", "freq": "Mensuelle",
        "world": [C("CAPE de Shiller S&P 500", lambda R: R["cape"], 0.5, "x"),
                  C("PER S&P 500", lambda R: R["spx_pe"], 0.5, "x")],
        "europe": [C("Euro Stoxx 50 / moyenne 10 ans (proxy)", lambda R: price_to_trend(R["sx5e"]), 0.5, "ratio"),
                   C("CAC 40 / moyenne 10 ans (proxy)", lambda R: price_to_trend(R["cac"]), 0.5, "ratio")],
    },
    {
        "id": "prime_risque", "label": "Prime de risque actions (rendement des bénéfices − taux 10 ans)",
        "pillar": "marches", "direction": 1, "unit": "points de %", "freq": "Mensuelle",
        "world": [C("S&P 500", lambda R: spread(inv_yield(R["spx_pe"]), R["us_10y"]))],
    },
    {
        "id": "change", "label": "Change (écart à la moyenne 1 an)", "pillar": "marches", "direction": -1,
        "unit": "% (valeur absolue)", "freq": "Continue",
        "world": [C("Dollar index", lambda R: dev1y(R["dxy"]))],
        "europe": [C("EUR/USD", lambda R: dev1y(R["eurusd"]))],
    },
    # ======================= RISQUE
    {
        "id": "volatilite", "label": "Volatilité implicite", "pillar": "risque", "direction": -1,
        "unit": "points", "freq": "Continue",
        "world": [C("VIX", lambda R: R["vix"])],
        "europe": [C("VSTOXX", lambda R: R.get("vstoxx", R["vix"]))],
    },
    {
        "id": "brent", "label": "Pétrole Brent (ampleur de la variation sur 3 mois)", "pillar": "risque", "direction": -1,
        "unit": "% sur 3 mois (valeur absolue)", "freq": "Continue",
        "world": [C("Brent en dollars", lambda R: chg(R["brent"], 63).abs())],
        "europe": [C("Brent en euros", lambda R: chg(R["brent"] / R["eurusd"].reindex(R["brent"].index, method="ffill"), 63).abs())],
    },
    {
        "id": "spreads", "label": "Spreads de crédit haut rendement", "pillar": "risque", "direction": -1,
        "unit": "points de %", "freq": "Quotidienne",
        "world": [C("ICE BofA US High Yield", lambda R: R["us_hy"])],
        "europe": [C("ICE BofA Euro High Yield", lambda R: R["eu_hy"])],
    },
    {
        "id": "geopolitique", "label": "Risque géopolitique et incertitude", "pillar": "risque", "direction": -1,
        "unit": "indice", "freq": "Quotidienne et mensuelle",
        "world": [C("Indice GPR (moyenne 30 jours)", lambda R: mean_window(R["gpr"], 30), 0.6),
                  C("Incertitude politique mondiale (EPU)", lambda R: R["epu_global"], 0.4)],
        "europe": [C("Incertitude politique Europe (EPU)", lambda R: R["epu_europe"]),
                   C("Incertitude politique France (EPU)", lambda R: R["epu_fr"])],
    },
    {
        "id": "or", "label": "Or (variation 3 mois)", "pillar": "risque", "direction": -1,
        "unit": "% sur 3 mois", "freq": "Continue",
        "world": [C("Or en dollars", lambda R: chg(R["gold"], 63))],
        "europe": [C("Or en euros", lambda R: chg(R["gold"] / R["eurusd"].reindex(R["gold"].index, method="ffill"), 63))],
    },
    # ======================= FLUX ET SENTIMENT
    {
        "id": "credit_impulse", "label": "Credit impulse", "pillar": "flux", "direction": 1,
        "unit": "points de PIB", "freq": "Trimestrielle",
        "world": [C("Chine", lambda R: impulse(R["credit_cn"]), 0.5),
                  C("États-Unis", lambda R: impulse(R["credit_us"]), 0.5)],
        "europe": [C("Zone euro", lambda R: impulse(R["credit_ea"]))],
    },
    {
        "id": "conditions_fin", "label": "Conditions financières (stress)", "pillar": "flux", "direction": -1,
        "unit": "indice", "freq": "Hebdomadaire",
        "world": [C("NFCI (Fed de Chicago)", lambda R: R["nfci"])],
        "europe": [C("CISS (BCE)", lambda R: R["ciss"])],
    },
    {
        "id": "sentiment", "label": "Sentiment des news (dictionnaire)", "pillar": "flux", "direction": 1,
        "unit": "score de −1 à +1", "freq": "2 fois par jour",
        "world": [C("Presse internationale", lambda R: R["news_world"])],
        "europe": [C("Presse française et européenne", lambda R: R["news_europe"])],
    },
]

# Normalisation
Z_WINDOW_DAYS = 3650   # 10 ans
Z_MIN_DAYS = 1095      # 3 ans minimum, sinon Min-Max sur l'historique disponible
Z_CLIP = 3.0
HISTORY_START = "2007-01-01"

# Délai au-delà duquel une donnée est signalée « en retard » (jours)
STALE_AFTER = {
    "Continue": 5, "Quotidienne": 7, "Quotidienne et mensuelle": 45, "Hebdomadaire": 15,
    "Mensuelle": 80, "Trimestrielle": 200, "À chaque réunion": 7, "2 fois par jour": 2,
}

ZONES = [  # bornes du score de tension
    (20, "Euphorie", "Environnement très porteur, mais risque d'excès : rester discipliné."),
    (40, "Favorable", "Contexte propice aux actifs risqués."),
    (60, "Neutre", "Signaux mitigés : portefeuille équilibré."),
    (80, "Prudence", "Tensions visibles : réduire le risque."),
    (101, "Stress", "Crise ou forte aversion au risque : priorité à la protection."),
]

# Allocation indicative (profil équilibré) par zone : actions, obligations, or, liquidités
ALLOCATION = {
    "Euphorie": {"Actions": 50, "Obligations": 25, "Or": 10, "Liquidités": 15},
    "Favorable": {"Actions": 60, "Obligations": 25, "Or": 5, "Liquidités": 10},
    "Neutre": {"Actions": 45, "Obligations": 35, "Or": 10, "Liquidités": 10},
    "Prudence": {"Actions": 30, "Obligations": 40, "Or": 15, "Liquidités": 15},
    "Stress": {"Actions": 15, "Obligations": 45, "Or": 20, "Liquidités": 20},
}


def zone_of(score: float) -> tuple[str, str]:
    for bound, name, text in ZONES:
        if score < bound:
            return name, text
    return ZONES[-1][1], ZONES[-1][2]


def market_series() -> list[str]:
    return [k for k, v in SERIES.items() if v.get("market")]


def empty_series() -> pd.Series:
    return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
