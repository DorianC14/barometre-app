"""Définition du baromètre : séries brutes, indicateurs, piliers et pondérations.

Toute la méthodologie chiffrée est ici, pour pouvoir la modifier sans toucher au code.
"""
from __future__ import annotations

import pandas as pd

from transforms import chg, dev1y, impulse, inv_yield, ma_gap, mean_window, price_to_trend, realized_vol, spread, yoy

# ---------------------------------------------------------------------------
# 1. Séries brutes : nom interne -> liste de sources (la première qui répond gagne)
#    Une source = (type, identifiant[, options]). "market" = rafraîchie toutes les 15 min.
# ---------------------------------------------------------------------------
# ETF européens cotés en dollars (Twelve Data) : convertis en euros avec EUR/USD avant calcul,
# pour suivre l'indice qu'ils répliquent et non le change.
ETF_EN_EUROS = {"twelvedata:FEZ", "twelvedata:EWQ"}

SERIES: dict[str, dict] = {
    # --- Macro (FRED, CSV public sans clé ; OCDE et BRI pour la Chine et le Japon)
    "us_gdp": {"src": [("fred", "GDPC1")]},
    "jp_gdp": {"src": [("fred", "JPNRGDPEXP")]},
    "ea_gdp": {"src": [("fred", "CLVMNACSCAB1GQEA19")]},
    "fr_gdp": {"src": [("fred", "CLVMNACSCAB1GQFR"), ("insee", "010565708")]},
    "cn_gdp": {"src": [("oecd_gdp", "CHN")]},            # déjà en % sur 1 an
    "us_cpi": {"src": [("fred", "CPIAUCSL")]},
    "ea_hicp": {"src": [("fred", "CP0000EZ19M086NEST")]},
    "fr_cpi": {"src": [("fred", "CP0000FRM086NEST"), ("insee", "001759970")]},
    "jp_cpi": {"src": [("bis", "WS_LONG_CPI/1.0/M.JP.771")]},  # déjà en % sur 1 an
    "cn_cpi": {"src": [("bis", "WS_LONG_CPI/1.0/M.CN.771"), ("oecd_cpi", "CHN")]},  # déjà en % sur 1 an
    "us_unemp": {"src": [("fred", "UNRATE")]},
    "ea_unemp": {"src": [("eurostat", "une_rt_m", {"geo": "EA21", "s_adj": "SA", "age": "TOTAL", "sex": "T", "unit": "PC_ACT"}), ("fred", "LRHUTTTTEZM156S"), ("eurostat", "une_rt_m", {"geo": "EA20", "s_adj": "SA", "age": "TOTAL", "sex": "T", "unit": "PC_ACT"})]},
    "fr_unemp": {"src": [("eurostat", "une_rt_m", {"geo": "FR", "s_adj": "SA", "age": "TOTAL", "sex": "T", "unit": "PC_ACT"}), ("fred", "LRHUTTTTFRM156S")]},
    "jp_unemp": {"src": [("fred", "LRHUTTTTJPM156S"), ("fred", "LRUN64TTJPM156S")]},
    "cli_us": {"src": [("oecd", "USA")]},
    "cli_cn": {"src": [("oecd", "CHN")]},
    "cli_jp": {"src": [("oecd", "JPN")]},
    "cli_ea": {"src": [("oecd", "EA20"), ("oecd", "G4E")]},
    "cli_fr": {"src": [("oecd", "FRA")]},
    "esi_ea": {"src": [("eurostat", "ei_bssi_m_r2", {"geo": "EA21", "indic": "BS-ESI-I", "s_adj": "SA"}),
                       ("eurostat", "ei_bssi_m_r2", {"geo": "EA20", "indic": "BS-ESI-I", "s_adj": "SA"})]},
    "fr_climat": {"src": [("insee", "001565530")]},
    "us_business": {"src": [("fred", "BSCICP02USM460S")]},   # confiance des entreprises (OCDE)
    "us_conso": {"src": [("fred", "UMCSENT")]},              # confiance des ménages (Michigan)
    "cn_conso": {"src": [("fred", "CSCICP02CNM460S")]},      # confiance des ménages (OCDE)
    # --- Banques centrales et taux
    "fed_funds": {"src": [("fred", "DFF")]},
    "ecb_dfr": {"src": [("fred", "ECBDFR"), ("ecb", "FM/D.U2.EUR.4F.KR.DFR.LEV")]},
    "boj": {"src": [("bis", "WS_CBPOL/1.0/D.JP"), ("fred", "IRSTCI01JPM156N")]},
    "pboc": {"src": [("bis", "WS_CBPOL/1.0/D.CN")]},          # Loan Prime Rate 1 an
    "us_2y": {"src": [("fred", "DGS2")]},
    "us_10y": {"src": [("yahoo", "^TNX"), ("fred", "DGS10")], "market": True},
    "ea_2y": {"src": [("ecb", "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y")]},
    "ea_10y": {"src": [("ecb", "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y")]},
    "oat_10y": {"src": [("fred", "IRLTLT01FRM156N")]},
    "bund_10y": {"src": [("fred", "IRLTLT01DEM156N")]},
    "btp_10y": {"src": [("fred", "IRLTLT01ITM156N")]},
    "jp_10y": {"src": [("fred", "IRLTLT01JPM156N")]},
    "jp_3m": {"src": [("fred", "IR3TIB01JPM156N")]},
    "jp_call": {"src": [("fred", "IRSTCI01JPM156N")]},
    "cn_3m": {"src": [("fred", "IR3TIB01CNM156N")]},
    # --- Marchés : indices via Yahoo (FRED / STOXX en secours) ; l'offre gratuite Twelve Data
    # refuse les indices (SPX, SX5E réservés Pro ; FCHI, IXIC, 000001:SSE inconnus) : elle sert
    # pour l'or spot (XAU/USD) et, en dernier recours, pour des ETF répliquant chaque indice.
    "spx": {"src": [("yahoo", "^GSPC"), ("fred", "SP500"), ("twelvedata", "SPY")], "market": True},
    "ndx": {"src": [("yahoo", "^IXIC"), ("fred", "NASDAQCOM"), ("twelvedata", "ONEQ")], "market": True},
    "nikkei": {"src": [("yahoo", "^N225"), ("fred", "NIKKEI225")], "market": True},
    "shanghai": {"src": [("yahoo", "000001.SS"), ("twelvedata", "MCHI")], "market": True},
    "sx5e": {"src": [("yahoo", "^STOXX50E"), ("twelvedata", "FEZ"), ("stoxx", "h_3msx5e")], "market": True},
    "cac": {"src": [("yahoo", "^FCHI"), ("twelvedata", "EWQ")], "market": True},
    "eurusd": {"src": [("yahoo", "EURUSD=X"), ("ecb", "EXR/D.USD.EUR.SP00.A"), ("fred", "DEXUSEU")], "market": True},
    "usdjpy": {"src": [("yahoo", "JPY=X"), ("fred", "DEXJPUS")], "market": True},
    "usdcny": {"src": [("yahoo", "CNY=X"), ("fred", "DEXCHUS")], "market": True},
    "dxy": {"src": [("yahoo", "DX-Y.NYB"), ("fred", "DTWEXBGS")], "market": True},
    "gold": {"src": [("twelvedata", "XAU/USD"), ("yahoo", "GC=F")], "market": True},
    "reit": {"src": [("yahoo", "VNQ"), ("twelvedata", "VNQ")]},  # immobilier coté (test historique)
    "cape": {"src": [("multpl", "shiller-pe")]},
    "spx_pe": {"src": [("multpl", "s-p-500-pe-ratio")]},
    # --- Risque
    "vix": {"src": [("yahoo", "^VIX"), ("fred", "VIXCLS")], "market": True},
    "vstoxx": {"src": [("stoxx", "h_v2tx"), ("yahoo", "^V2TX")], "market": True},
    "brent": {"src": [("yahoo", "BZ=F"), ("fred", "DCOILBRENTEU")], "market": True},
    "us_hy": {"src": [("fred", "BAMLH0A0HYM2")]},
    "eu_hy": {"src": [("fred", "BAMLHE00EHYIOAS")]},
    "asia_credit": {"src": [("fred", "BAMLEMRACRPIASIAOAS")]},
    "gpr": {"src": [("gpr", "daily")]},
    "gpr_us": {"src": [("gpr_country", "USA")]},
    "gpr_fr": {"src": [("gpr_country", "FRA")]},
    "gpr_cn": {"src": [("gpr_country", "CHN")]},
    "gpr_jp": {"src": [("gpr_country", "JPN")]},
    "epu_global": {"src": [("fred", "GEPUCURRENT")]},
    "epu_us": {"src": [("fred", "USEPUINDXD")]},
    "epu_europe": {"src": [("fred", "EUEPUINDXM"), ("epu", "European")]},
    "epu_fr": {"src": [("epu", "France"), ("fred", "FRAEPUINDXM")]},
    "epu_jp": {"src": [("epu_japan", "")]},
    # --- Flux et conditions financières
    "credit_us": {"src": [("fred", "QUSPAM770A")]},
    "credit_cn": {"src": [("fred", "QCNPAM770A")]},
    "credit_ea": {"src": [("fred", "QXMPAM770A")]},
    "credit_fr": {"src": [("fred", "QFRPAM770A")]},
    "credit_jp": {"src": [("fred", "QJPPAM770A")]},
    "nfci": {"src": [("fred", "NFCI")]},
    "ciss": {"src": [("ecb", "CISS/D.U2.Z0Z.4F.EC.SS_CIN.IDX")]},
    "ciss_fr": {"src": [("ecb", "CISS/D.FR.Z0Z.4F.EC.SS_CIN.IDX")]},
}

SOURCE_LABELS = {
    "fred": "FRED (Fed de Saint-Louis)",
    "ecb": "BCE Data Portal",
    "eurostat": "Eurostat",
    "insee": "INSEE",
    "oecd": "OCDE",
    "oecd_gdp": "OCDE",
    "oecd_cpi": "OCDE",
    "bis": "Banque des règlements internationaux (BRI)",
    "yahoo": "Yahoo Finance",
    "stooq": "Stooq",
    "stoxx": "STOXX (fichiers officiels)",
    "twelvedata": "Twelve Data (API)",
    "epu": "Economic Policy Uncertainty (Baker, Bloom, Davis)",
    "epu_japan": "Economic Policy Uncertainty (Baker, Bloom, Davis)",
    "multpl": "multpl (données Shiller)",
    "gpr": "Caldara & Iacoviello (GPR)",
    "gpr_country": "Caldara & Iacoviello (GPR par pays)",
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

# Zones suivies, dans l'ordre d'affichage
REGIONS = {
    "world": "Monde",
    "europe": "Europe (zone euro)",
    "france": "France",
    "us": "États-Unis",
    "cn": "Chine",
    "jp": "Japon",
}
# Revue de presse utilisée pour le sentiment de chaque zone
NEWS_OF_REGION = {"world": "news_world", "europe": "news_europe", "france": "news_europe",
                  "us": "news_world", "cn": "news_world", "jp": "news_world"}

# Poids des zones dans le score Monde (part approximative du PIB mondial, FMI)
GDP_W = {"us": 0.26, "ea": 0.15, "cn": 0.17, "jp": 0.04}


def C(name: str, fn, weight: float = 1.0, unit: str | None = None) -> dict:
    """Composante d'un indicateur : fn(R) -> série brute affichée."""
    return {"name": name, "fn": fn, "weight": weight, "unit": unit}


def _in(cur: str, R: dict, series: str) -> pd.Series:
    """Prix en dollars converti dans une autre devise (« eur » ou « jpy »)."""
    s = R[series]
    if cur == "eur":
        return s / R["eurusd"].reindex(s.index, method="ffill")
    if cur == "jpy":
        return s * R["usdjpy"].reindex(s.index, method="ffill")
    return s


# ---------------------------------------------------------------------------
# 3. Indicateurs. direction : +1 = une hausse est favorable aux marchés,
#    -1 = défavorable, "target" = distance à la cible de 2 % (inflation).
#    "weight" = poids dans le pilier (1 par défaut, 2 pour le taux anticipé).
#    Une clé par zone (world, europe, france, us, cn, jp) : composantes propres à la zone.
# ---------------------------------------------------------------------------
INDICATORS: list[dict] = [
    # ======================= MACRO
    {
        "id": "pib", "label": "Croissance du PIB", "pillar": "macro", "direction": 1,
        "unit": "% sur 1 an", "freq": "Trimestrielle",
        "world": [C("États-Unis", lambda R: yoy(R["us_gdp"]), GDP_W["us"]),
                  C("Chine", lambda R: R["cn_gdp"], GDP_W["cn"]),
                  C("Zone euro", lambda R: yoy(R["ea_gdp"]), GDP_W["ea"]),
                  C("Japon", lambda R: yoy(R["jp_gdp"]), GDP_W["jp"])],
        "europe": [C("Zone euro", lambda R: yoy(R["ea_gdp"]))],
        "france": [C("France", lambda R: yoy(R["fr_gdp"]))],
        "us": [C("États-Unis", lambda R: yoy(R["us_gdp"]))],
        "cn": [C("Chine", lambda R: R["cn_gdp"])],
        "jp": [C("Japon", lambda R: yoy(R["jp_gdp"]))],
    },
    {
        "id": "inflation", "label": "Inflation", "pillar": "macro", "direction": "target",
        "unit": "% sur 1 an", "freq": "Mensuelle",
        "world": [C("États-Unis (CPI)", lambda R: yoy(R["us_cpi"]), GDP_W["us"]),
                  C("Chine", lambda R: R["cn_cpi"], GDP_W["cn"]),
                  C("Zone euro (HICP)", lambda R: yoy(R["ea_hicp"]), GDP_W["ea"]),
                  C("Japon", lambda R: R["jp_cpi"], GDP_W["jp"])],
        "europe": [C("Zone euro (HICP)", lambda R: yoy(R["ea_hicp"]))],
        "france": [C("France (IPCH)", lambda R: yoy(R["fr_cpi"]))],
        "us": [C("États-Unis (CPI)", lambda R: yoy(R["us_cpi"]))],
        "cn": [C("Chine (CPI)", lambda R: R["cn_cpi"])],
        "jp": [C("Japon (CPI)", lambda R: R["jp_cpi"])],
    },
    {
        "id": "cli", "label": "Indicateur avancé OCDE (proxy PMI)", "pillar": "macro", "direction": 1,
        "unit": "indice (100 = tendance)", "freq": "Mensuelle",
        "world": [C("États-Unis", lambda R: R["cli_us"], GDP_W["us"]),
                  C("Chine", lambda R: R["cli_cn"], GDP_W["cn"]),
                  C("Europe (grands pays, OCDE)", lambda R: R["cli_ea"], GDP_W["ea"]),
                  C("Japon", lambda R: R["cli_jp"], GDP_W["jp"])],
        "europe": [C("Europe (grands pays, OCDE)", lambda R: R["cli_ea"])],
        "france": [C("France", lambda R: R["cli_fr"])],
        "us": [C("États-Unis", lambda R: R["cli_us"])],
        "cn": [C("Chine", lambda R: R["cli_cn"])],
        "jp": [C("Japon", lambda R: R["cli_jp"])],
    },
    {
        "id": "climat", "label": "Climat des affaires et confiance", "pillar": "macro", "direction": 1,
        "unit": "indice", "freq": "Mensuelle",
        "europe": [C("Sentiment économique zone euro (Commission)", lambda R: R["esi_ea"])],
        "france": [C("Climat des affaires France (INSEE)", lambda R: R["fr_climat"])],
        "us": [C("Confiance des entreprises (OCDE)", lambda R: R["us_business"]),
               C("Confiance des ménages (Michigan)", lambda R: R["us_conso"])],
        "cn": [C("Confiance des ménages (OCDE)", lambda R: R["cn_conso"])],
    },
    {
        "id": "chomage", "label": "Chômage", "pillar": "macro", "direction": -1,
        "unit": "% de la population active", "freq": "Mensuelle",
        "world": [C("États-Unis", lambda R: R["us_unemp"], GDP_W["us"]),
                  C("Zone euro", lambda R: R["ea_unemp"], GDP_W["ea"]),
                  C("Japon", lambda R: R["jp_unemp"], GDP_W["jp"])],
        "europe": [C("Zone euro", lambda R: R["ea_unemp"])],
        "france": [C("France", lambda R: R["fr_unemp"])],
        "us": [C("États-Unis", lambda R: R["us_unemp"])],
        "jp": [C("Japon", lambda R: R["jp_unemp"])],
    },
    # ======================= BANQUES CENTRALES
    {
        "id": "taux_directeur", "label": "Taux directeur", "pillar": "bc", "direction": -1,
        "unit": "%", "freq": "À chaque réunion",
        "world": [C("Fed (Fed funds)", lambda R: R["fed_funds"], GDP_W["us"]),
                  C("Banque populaire de Chine (LPR 1 an)", lambda R: R["pboc"], GDP_W["cn"]),
                  C("BCE (taux de dépôt)", lambda R: R["ecb_dfr"], GDP_W["ea"]),
                  C("Banque du Japon", lambda R: R["boj"], GDP_W["jp"])],
        "europe": [C("BCE (taux de dépôt)", lambda R: R["ecb_dfr"])],
        "france": [C("BCE (taux de dépôt)", lambda R: R["ecb_dfr"])],
        "us": [C("Fed (Fed funds)", lambda R: R["fed_funds"])],
        "cn": [C("Banque populaire de Chine (LPR 1 an)", lambda R: R["pboc"])],
        "jp": [C("Banque du Japon (taux au jour le jour)", lambda R: R["boj"])],
    },
    {
        "id": "taux_anticipe", "label": "Taux directeur anticipé (taux court de marché − taux directeur)", "pillar": "bc",
        "direction": -1, "weight": 2, "unit": "points de %", "freq": "Quotidienne",
        "world": [C("Treasury 2 ans − Fed funds", lambda R: spread(R["us_2y"], R["fed_funds"]), 0.6),
                  C("Taux 2 ans zone euro − dépôt BCE", lambda R: spread(R["ea_2y"], R["ecb_dfr"]), 0.4)],
        "europe": [C("Taux 2 ans zone euro − dépôt BCE", lambda R: spread(R["ea_2y"], R["ecb_dfr"]))],
        "france": [C("Taux 2 ans zone euro − dépôt BCE", lambda R: spread(R["ea_2y"], R["ecb_dfr"]))],
        "us": [C("Treasury 2 ans − Fed funds", lambda R: spread(R["us_2y"], R["fed_funds"]))],
        "cn": [C("Taux interbancaire 3 mois − LPR 1 an", lambda R: spread(R["cn_3m"], R["pboc"]))],
        "jp": [C("Tibor 3 mois − taux au jour le jour", lambda R: spread(R["jp_3m"], R["jp_call"]))],
    },
    {
        "id": "taux_10a", "label": "Taux souverain 10 ans", "pillar": "bc", "direction": -1,
        "unit": "%", "freq": "Quotidienne",
        "world": [C("Treasury 10 ans", lambda R: R["us_10y"])],
        "europe": [C("Taux 10 ans zone euro (AAA)", lambda R: R["ea_10y"])],
        "france": [C("OAT 10 ans", lambda R: R["oat_10y"])],
        "us": [C("Treasury 10 ans", lambda R: R["us_10y"])],
        "jp": [C("JGB 10 ans", lambda R: R["jp_10y"])],
    },
    {
        "id": "pente", "label": "Pente de la courbe (10 ans − court terme)", "pillar": "bc", "direction": 1,
        "unit": "points de %", "freq": "Quotidienne",
        "world": [C("États-Unis (10 ans − 2 ans)", lambda R: spread(R["us_10y"], R["us_2y"]))],
        "europe": [C("Zone euro (10 ans − 2 ans)", lambda R: spread(R["ea_10y"], R["ea_2y"]))],
        "france": [C("OAT 10 ans − taux 2 ans zone euro", lambda R: spread(R["oat_10y"], R["ea_2y"]))],
        "us": [C("États-Unis (10 ans − 2 ans)", lambda R: spread(R["us_10y"], R["us_2y"]))],
        "jp": [C("Japon (10 ans − taux au jour le jour)", lambda R: spread(R["jp_10y"], R["jp_call"]))],
    },
    {
        "id": "ecart_souverain", "label": "Écart de taux avec l'Allemagne (10 ans)", "pillar": "bc", "direction": -1,
        "unit": "points de %", "freq": "Mensuelle",
        "europe": [C("Italie − Allemagne (BTP − Bund)", lambda R: spread(R["btp_10y"], R["bund_10y"]))],
        "france": [C("France − Allemagne (OAT − Bund)", lambda R: spread(R["oat_10y"], R["bund_10y"]))],
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
        "europe": [C("Euro Stoxx 50", lambda R: ma_gap(R["sx5e"]))],
        "france": [C("CAC 40", lambda R: ma_gap(R["cac"]))],
        "us": [C("S&P 500", lambda R: ma_gap(R["spx"]), 0.7), C("Nasdaq", lambda R: ma_gap(R["ndx"]), 0.3)],
        "cn": [C("Shanghai Composite", lambda R: ma_gap(R["shanghai"]))],
        "jp": [C("Nikkei 225", lambda R: ma_gap(R["nikkei"]))],
    },
    {
        "id": "valorisation", "label": "Valorisation des actions", "pillar": "marches", "direction": -1,
        "unit": "ratio", "freq": "Mensuelle",
        "world": [C("CAPE de Shiller S&P 500", lambda R: R["cape"], 0.5, "x"),
                  C("PER S&P 500", lambda R: R["spx_pe"], 0.5, "x")],
        "europe": [C("Euro Stoxx 50 / moyenne 10 ans (proxy)", lambda R: price_to_trend(R["sx5e"]), 1, "ratio")],
        "france": [C("CAC 40 / moyenne 10 ans (proxy)", lambda R: price_to_trend(R["cac"]), 1, "ratio")],
        "us": [C("CAPE de Shiller S&P 500", lambda R: R["cape"], 0.5, "x"),
               C("PER S&P 500", lambda R: R["spx_pe"], 0.5, "x")],
        "cn": [C("Shanghai / moyenne 10 ans (proxy)", lambda R: price_to_trend(R["shanghai"]), 1, "ratio")],
        "jp": [C("Nikkei / moyenne 10 ans (proxy)", lambda R: price_to_trend(R["nikkei"]), 1, "ratio")],
    },
    {
        "id": "prime_risque", "label": "Prime de risque actions (rendement des bénéfices − taux 10 ans)",
        "pillar": "marches", "direction": 1, "unit": "points de %", "freq": "Mensuelle",
        "world": [C("S&P 500", lambda R: spread(inv_yield(R["spx_pe"]), R["us_10y"]))],
        "us": [C("S&P 500", lambda R: spread(inv_yield(R["spx_pe"]), R["us_10y"]))],
    },
    {
        "id": "change", "label": "Change (écart à la moyenne 1 an)", "pillar": "marches", "direction": -1,
        "unit": "% (valeur absolue)", "freq": "Continue",
        "world": [C("Dollar index", lambda R: dev1y(R["dxy"]))],
        "europe": [C("EUR/USD", lambda R: dev1y(R["eurusd"]))],
        "france": [C("EUR/USD", lambda R: dev1y(R["eurusd"]))],
        "us": [C("Dollar index", lambda R: dev1y(R["dxy"]))],
        "cn": [C("USD/CNY (yuan)", lambda R: dev1y(R["usdcny"]))],
        "jp": [C("USD/JPY (yen)", lambda R: dev1y(R["usdjpy"]))],
    },
    # ======================= RISQUE
    {
        "id": "volatilite", "label": "Volatilité des actions", "pillar": "risque", "direction": -1,
        "unit": "points", "freq": "Continue",
        "world": [C("VIX", lambda R: R["vix"])],
        "europe": [C("VSTOXX", lambda R: R.get("vstoxx", R["vix"]))],
        "france": [C("VSTOXX", lambda R: R.get("vstoxx", R["vix"]))],
        "us": [C("VIX", lambda R: R["vix"])],
        "cn": [C("Volatilité réalisée 1 mois du Shanghai", lambda R: realized_vol(R["shanghai"]), 1, "% annualisé")],
        "jp": [C("Volatilité réalisée 1 mois du Nikkei", lambda R: realized_vol(R["nikkei"]), 1, "% annualisé")],
    },
    {
        "id": "brent", "label": "Pétrole Brent (ampleur de la variation sur 3 mois)", "pillar": "risque", "direction": -1,
        "unit": "% sur 3 mois (valeur absolue)", "freq": "Continue",
        "world": [C("Brent en dollars", lambda R: chg(R["brent"], 63).abs())],
        "europe": [C("Brent en euros", lambda R: chg(_in("eur", R, "brent"), 63).abs())],
        "france": [C("Brent en euros", lambda R: chg(_in("eur", R, "brent"), 63).abs())],
        "us": [C("Brent en dollars", lambda R: chg(R["brent"], 63).abs())],
        "cn": [C("Brent en dollars", lambda R: chg(R["brent"], 63).abs())],
        "jp": [C("Brent en yens", lambda R: chg(_in("jpy", R, "brent"), 63).abs())],
    },
    {
        "id": "spreads", "label": "Spreads de crédit", "pillar": "risque", "direction": -1,
        "unit": "points de %", "freq": "Quotidienne",
        "world": [C("ICE BofA US High Yield", lambda R: R["us_hy"])],
        "europe": [C("ICE BofA Euro High Yield", lambda R: R["eu_hy"])],
        "france": [C("ICE BofA Euro High Yield", lambda R: R["eu_hy"])],
        "us": [C("ICE BofA US High Yield", lambda R: R["us_hy"])],
        "cn": [C("ICE BofA obligations d'entreprises Asie émergente", lambda R: R["asia_credit"])],
        "jp": [C("ICE BofA obligations d'entreprises Asie (proxy)", lambda R: R["asia_credit"])],
    },
    {
        "id": "geopolitique", "label": "Risque géopolitique et incertitude", "pillar": "risque", "direction": -1,
        "unit": "indice", "freq": "Quotidienne et mensuelle",
        "world": [C("Indice GPR (moyenne 30 jours)", lambda R: mean_window(R["gpr"], 30), 0.6),
                  C("Incertitude politique mondiale (EPU)", lambda R: R["epu_global"], 0.4)],
        "europe": [C("Incertitude politique Europe (EPU)", lambda R: R["epu_europe"], 0.6),
                   C("Indice GPR mondial (moyenne 30 jours)", lambda R: mean_window(R["gpr"], 30), 0.4)],
        "france": [C("Incertitude politique France (EPU)", lambda R: R["epu_fr"], 0.6),
                   C("Risque géopolitique France (GPR)", lambda R: R["gpr_fr"], 0.4)],
        "us": [C("Incertitude politique États-Unis (EPU, moyenne 30 jours)", lambda R: mean_window(R["epu_us"], 30), 0.6),
               C("Risque géopolitique États-Unis (GPR)", lambda R: R["gpr_us"], 0.4)],
        "cn": [C("Risque géopolitique Chine (GPR)", lambda R: R["gpr_cn"])],
        "jp": [C("Incertitude politique Japon (EPU)", lambda R: R["epu_jp"], 0.6),
               C("Risque géopolitique Japon (GPR)", lambda R: R["gpr_jp"], 0.4)],
    },
    {
        "id": "or", "label": "Or (variation 3 mois)", "pillar": "risque", "direction": -1,
        "unit": "% sur 3 mois", "freq": "Continue",
        "world": [C("Or en dollars", lambda R: chg(R["gold"], 63))],
        "europe": [C("Or en euros", lambda R: chg(_in("eur", R, "gold"), 63))],
        "france": [C("Or en euros", lambda R: chg(_in("eur", R, "gold"), 63))],
        "us": [C("Or en dollars", lambda R: chg(R["gold"], 63))],
        "cn": [C("Or en dollars", lambda R: chg(R["gold"], 63))],
        "jp": [C("Or en yens", lambda R: chg(_in("jpy", R, "gold"), 63))],
    },
    # ======================= FLUX ET SENTIMENT
    {
        "id": "credit_impulse", "label": "Credit impulse", "pillar": "flux", "direction": 1,
        "unit": "points de PIB", "freq": "Trimestrielle",
        "world": [C("Chine", lambda R: impulse(R["credit_cn"]), 0.5),
                  C("États-Unis", lambda R: impulse(R["credit_us"]), 0.5)],
        "europe": [C("Zone euro", lambda R: impulse(R["credit_ea"]))],
        "france": [C("France", lambda R: impulse(R["credit_fr"]))],
        "us": [C("États-Unis", lambda R: impulse(R["credit_us"]))],
        "cn": [C("Chine", lambda R: impulse(R["credit_cn"]))],
        "jp": [C("Japon", lambda R: impulse(R["credit_jp"]))],
    },
    {
        "id": "conditions_fin", "label": "Conditions financières (stress)", "pillar": "flux", "direction": -1,
        "unit": "indice", "freq": "Hebdomadaire",
        "world": [C("NFCI (Fed de Chicago)", lambda R: R["nfci"])],
        "europe": [C("CISS zone euro (BCE)", lambda R: R["ciss"])],
        "france": [C("CISS France (BCE)", lambda R: R["ciss_fr"])],
        "us": [C("NFCI (Fed de Chicago)", lambda R: R["nfci"])],
    },
    {
        "id": "sentiment", "label": "Sentiment des news (dictionnaire)", "pillar": "flux", "direction": 1,
        "unit": "score de −1 à +1", "freq": "4 fois par jour",
        "world": [C("Presse internationale", lambda R: R["news_world"])],
        "europe": [C("Presse française et européenne", lambda R: R["news_europe"])],
        "france": [C("Presse française et européenne", lambda R: R["news_europe"])],
        "us": [C("Presse internationale", lambda R: R["news_world"])],
        "cn": [C("Presse internationale", lambda R: R["news_world"])],
        "jp": [C("Presse internationale", lambda R: R["news_world"])],
    },
]

# Normalisation
Z_WINDOW_DAYS = 3650   # 10 ans
Z_MIN_DAYS = 1095      # 3 ans minimum, sinon Min-Max sur l'historique disponible
Z_CLIP = 3.0
HISTORY_START = "2007-01-01"   # début de l'historique publié
CALC_START = "2000-01-01"      # début du calcul interne (sert à caler l'échelle avant 2007)

# Calage de l'échelle (« étirement »). Moyenner 22 notes ramène toujours vers 50 : sans calage,
# le score brut n'est jamais sorti de 27-77 depuis 2007. On classe donc le score brut du jour
# parmi ceux des 10 dernières années (percentile p), puis : score = 50 + 20 × Φ⁻¹(p), borné à 0-100.
# 20 points = 1 écart-type : neutre = à moins d'un demi écart-type de la normale,
# euphorie et stress = au-delà de 1,5 écart-type (≈ 7 % des jours chacun).
CALIB_POINTS_PER_SD = 20.0
CALIB_WINDOW_DAYS = 3650       # comparaison aux 10 dernières années
CALIB_MIN_DAYS = 1095          # 3 ans d'historique au minimum

# Poids variables dans le temps (« surpondération conjoncturelle ») : quand la note d'un
# indicateur bouge fortement en quelques jours (décision de banque centrale, choc de marché…),
# son poids dans le pilier augmente, au plus de 50 %, puis revient à la normale.
SHOCK_LOOKBACK = 5        # jours
SHOCK_START = 10.0        # points de note : début de la surpondération
SHOCK_FULL = 25.0         # points de note : surpondération maximale
SHOCK_MAX_BOOST = 0.5     # +50 % au plus (poids × 1,5)
SHOCK_HALF_LIFE = 7.0     # jours : le surplus de poids est divisé par 2 chaque semaine (≈ 3 semaines)

# Délai au-delà duquel une donnée est signalée « en retard » (jours)
STALE_AFTER = {
    "Continue": 5, "Quotidienne": 7, "Quotidienne et mensuelle": 45, "Hebdomadaire": 15,
    "Mensuelle": 80, "Trimestrielle": 200, "À chaque réunion": 7, "4 fois par jour": 2,
}

ZONES = [  # bornes du score de tension
    (20, "Euphorie", "Environnement très porteur, mais risque d'excès : rester discipliné."),
    (40, "Favorable", "Contexte propice aux actifs risqués."),
    (60, "Neutre", "Signaux mitigés : portefeuille équilibré."),
    (80, "Prudence", "Tensions visibles : réduire le risque."),
    (101, "Stress", "Crise ou forte aversion au risque : priorité à la protection."),
]

# Allocation indicative (profil équilibré) par zone. L'immobilier est de l'immobilier coté
# (foncières, SIIC, REIT) : liquide et coté chaque jour. Très sensible aux taux, il est réduit
# quand la tension monte.
ASSETS = ["Actions", "Obligations", "Immobilier", "Or", "Liquidités"]
ALLOCATION = {
    "Euphorie": {"Actions": 45, "Obligations": 25, "Immobilier": 5, "Or": 10, "Liquidités": 15},
    "Favorable": {"Actions": 55, "Obligations": 20, "Immobilier": 10, "Or": 5, "Liquidités": 10},
    "Neutre": {"Actions": 40, "Obligations": 30, "Immobilier": 10, "Or": 10, "Liquidités": 10},
    "Prudence": {"Actions": 28, "Obligations": 37, "Immobilier": 5, "Or": 15, "Liquidités": 15},
    "Stress": {"Actions": 15, "Obligations": 42, "Immobilier": 3, "Or": 20, "Liquidités": 20},
}

# Éditions de la revue de presse (heure de Paris), week-end compris
EDITIONS = [
    {"id": "preouverture", "time": "08:30", "label": "8 h 30 · avant l'ouverture de la Bourse de Paris"},
    {"id": "ouverture", "time": "09:30", "label": "9 h 30 · 30 minutes après l'ouverture"},
    {"id": "journee", "time": "17:00", "label": "17 h · les news de la journée"},
    {"id": "soir", "time": "21:00", "label": "21 h · bilan de la journée"},
]


def zone_of(score: float) -> tuple[str, str]:
    for bound, name, text in ZONES:
        if score < bound:
            return name, text
    return ZONES[-1][1], ZONES[-1][2]


def market_series() -> list[str]:
    return [k for k, v in SERIES.items() if v.get("market")]


def empty_series() -> pd.Series:
    return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
