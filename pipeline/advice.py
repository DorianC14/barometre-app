"""Pistes d'investissement déduites des indicateurs : règles transparentes, seuils chiffrés,
secteurs et exemples de supports (ETF cotés à Paris ou Francfort, accessibles en PEA ou compte-titres).

Les supports cités sont des exemples pédagogiques, pas des recommandations personnalisées (MIF).
"""
from __future__ import annotations

import config as cfg
from texts import n, sn

# Exemples de supports : (nom, ISIN, type)
ETF = {
    "world": ("iShares Core MSCI World", "IE00B4L5Y983", "ETF actions monde"),
    "sp500": ("iShares Core S&P 500", "IE00B5BMR087", "ETF actions États-Unis"),
    "stoxx50": ("iShares Core EURO STOXX 50", "IE0008471009", "ETF actions zone euro"),
    "cac": ("Amundi CAC 40", "FR0007052782", "ETF actions France"),
    "japan": ("iShares Core MSCI Japan IMI", "IE00B4L5YX21", "ETF actions Japon"),
    "em": ("iShares Core MSCI EM IMI", "IE00BKM4GZ66", "ETF actions émergentes (≈ 25 % Chine)"),
    "gov": ("iShares Core Euro Government Bond", "IE00B4WXJJ64", "ETF obligations d'État zone euro"),
    "gov_short": ("iShares € Govt Bond 1-3yr", "IE00B14X4Q57", "ETF obligations d'État courtes"),
    "ust": ("iShares $ Treasury Bond 7-10yr", "IE00B3VWN518", "ETF obligations d'État américaines"),
    "infl": ("iShares € Inflation Linked Govt Bond", "IE00B0M62X26", "ETF obligations indexées sur l'inflation"),
    "corp": ("iShares Core € Corp Bond", "IE00B3F81R35", "ETF obligations d'entreprises de qualité"),
    "hy": ("iShares € High Yield Corp Bond", "IE00B66F4759", "ETF obligations à haut rendement"),
    "cash": ("Xtrackers II EUR Overnight Rate Swap", "LU0290358497", "ETF monétaire (taux au jour le jour)"),
    "gold": ("Xetra-Gold", "DE000A0S9GB0", "ETC or physique"),
    "commo": ("iShares Diversified Commodity Swap", "IE00BDFL4P12", "ETF matières premières"),
    "energy": ("iShares STOXX Europe 600 Oil & Gas", "DE000A0H08M3", "ETF secteur pétrole et gaz"),
    "banks": ("iShares STOXX Europe 600 Banks", "DE000A0F5UJ7", "ETF secteur banques"),
    "defense": ("VanEck Defense", "IE000YYE6WK5", "ETF secteur défense"),
    "health": ("Xtrackers MSCI World Health Care", "IE00BM67HK77", "ETF secteur santé"),
    "staples": ("Xtrackers MSCI World Consumer Staples", "IE00BM67HN09", "ETF consommation de base"),
    "minvol": ("iShares Edge MSCI World Minimum Volatility", "IE00B8FHGS14", "ETF actions peu volatiles"),
    "quality": ("iShares Edge MSCI World Quality Factor", "IE00BP3QZ601", "ETF actions « qualité »"),
    "value": ("iShares Edge MSCI World Value Factor", "IE00BP3QZB59", "ETF actions « value »"),
    "dividend": ("SPDR S&P Euro Dividend Aristocrats", "IE00B5M1WJ87", "ETF actions à dividendes"),
    "tech": ("iShares S&P 500 Information Technology Sector", "IE00B3WJKG14", "ETF secteur technologie"),
    "reit_eu": ("iShares European Property Yield", "IE00B0M63284", "ETF immobilier coté européen"),
    "reit_world": ("iShares Developed Markets Property Yield", "IE00B1FZS350", "ETF immobilier coté mondial"),
}
REGION_ETF = {"world": "world", "europe": "stoxx50", "france": "cac", "us": "sp500", "cn": "em", "jp": "japan"}


def sup(*keys) -> list[dict]:
    return [{"name": ETF[k][0], "isin": ETF[k][1], "kind": ETF[k][2]} for k in keys]


def rule(title, why, idea, supports, horizon="6 à 12 mois", risk="modéré", importance=1, category="Marchés"):
    return {"title": title, "why": why, "idea": idea, "supports": supports, "horizon": horizon,
            "risk": risk, "importance": importance, "category": category}


def advice_rules(res: dict, region: str, zone: str, regime: dict | None) -> list:
    comp = res["composites"]
    tens = {i["id"]: i.get("tension") for i in res["indicators"] if i.get("available")}
    pillars = {p: float(res["T_pillars"][p].iloc[-1]) for p in res["T_pillars"].columns
               if res["T_pillars"][p].notna().any()}
    R = res.get("R", {})
    out = []

    def last(k):
        s = comp.get(k)
        return None if s is None or s.empty else float(s.iloc[-1])

    # ---- taux
    ta = last("taux_anticipe")
    if ta is not None and ta > 0.25:
        out.append(rule("Hausse de taux anticipée",
                        f"Les taux courts de marché dépassent le taux directeur de {n(ta, 2)} point (seuil : +0,25) : le marché parie sur une hausse.",
                        "Raccourcir la durée des obligations : une obligation courte perd peu quand les taux montent. Les banques profitent de marges plus élevées.",
                        sup("gov_short", "banks"), importance=3, category="Obligations"))
    elif ta is not None and ta < -0.25:
        out.append(rule("Baisse de taux anticipée",
                        f"Les taux courts de marché sont {n(abs(ta), 2)} point sous le taux directeur (seuil : −0,25) : le marché parie sur une baisse.",
                        "Allonger la durée des obligations : leur prix monte quand les taux baissent. L'immobilier coté et les valeurs de croissance en profitent aussi.",
                        sup("gov", "reit_eu"), importance=3, category="Obligations"))
    pe = last("pente")
    if pe is not None and pe < 0:
        out.append(rule("Courbe des taux inversée",
                        f"Le taux long est sous le taux court ({sn(pe, 2)} pt). Depuis 50 ans, cette inversion a précédé la plupart des récessions américaines, avec 6 à 24 mois d'avance.",
                        "Réduire les secteurs cycliques (industrie, consommation discrétionnaire) au profit d'entreprises solides et peu endettées, et des secteurs défensifs (santé, consommation de base).",
                        sup("quality", "health", "staples"), horizon="12 à 24 mois", importance=3, category="Actions"))
    # ---- pétrole
    raw_b = R.get("brent")
    if raw_b is not None and len(raw_b.dropna()) > 63:
        rb = raw_b.dropna()
        b = float((rb.iloc[-1] / rb.iloc[-64] - 1) * 100)
        if b > 15:
            out.append(rule("Pétrole en forte hausse",
                            f"Le Brent a pris {n(b, 0)} % en 3 mois (seuil : +15 %), à {n(float(rb.iloc[-1]), 0)} $ le baril.",
                            "Le secteur de l'énergie profite directement de la hausse. Pour se protéger du retour de l'inflation, les obligations indexées sont adaptées. Transport aérien et chimie souffrent.",
                            sup("energy", "infl"), horizon="3 à 6 mois", risk="élevé", importance=2, category="Secteurs"))
        elif b < -15:
            out.append(rule("Pétrole en forte baisse",
                            f"Le Brent a perdu {n(abs(b), 0)} % en 3 mois (seuil : −15 %), à {n(float(rb.iloc[-1]), 0)} $ le baril.",
                            "Moins de pression sur l'inflation et sur les coûts des entreprises : favorable à la consommation et au transport. Alléger le secteur pétrolier.",
                            sup("staples"), horizon="3 à 6 mois", importance=2, category="Secteurs"))
    # ---- géopolitique
    if (tens.get("geopolitique") or 0) > 70:
        out.append(rule("Risque géopolitique élevé",
                        f"La note de risque géopolitique et d'incertitude est à {n(tens['geopolitique'], 0)}/100 (seuil : 70).",
                        "L'or est la protection historique contre les crises (5 à 15 % du portefeuille). Le secteur de la défense profite de la hausse des budgets militaires, mais il est volatil.",
                        sup("gold", "defense"), risk="modéré à élevé", importance=2, category="Protection"))
    # ---- valorisation
    v = tens.get("valorisation")
    if v is not None and v > 75:
        out.append(rule("Actions chères",
                        f"La valorisation est notée {n(v, 0)}/100 (seuil : 75) : les prix sont élevés par rapport aux bénéfices et à leur historique.",
                        "Ne pas tout vendre, mais investir de façon progressive (un montant fixe chaque mois) et privilégier les entreprises bon marché ou qui versent des dividendes réguliers.",
                        sup("value", "dividend"), horizon="12 mois et plus", importance=2, category="Actions"))
    elif v is not None and v < 30:
        out.append(rule("Actions bon marché",
                        f"La valorisation est notée {n(v, 0)}/100 (seuil : 30) : les actions sont peu chères au regard de leur historique.",
                        "Renforcer progressivement un ETF indiciel large de la zone : historiquement, acheter quand les prix sont bas a donné de meilleurs rendements à 5 ans.",
                        sup(REGION_ETF[region]), horizon="3 à 5 ans", importance=2, category="Actions"))
    pr = last("prime_risque")
    if pr is not None and pr < 0.5:
        out.append(rule("Obligations compétitives face aux actions",
                        (f"La prime de risque des actions est négative ({sn(pr, 2)} pt, seuil : 0,5) : les bénéfices des entreprises rapportent moins qu'une obligation d'État sans risque."
                         if pr < 0 else
                         f"La prime de risque des actions n'est que de {sn(pr, 2)} pt (seuil : 0,5) : les bénéfices rapportent à peine plus qu'une obligation d'État sans risque."),
                        "Le couple rendement / risque penche vers les obligations d'État : renforcer cette poche plutôt que les actions américaines.",
                        sup("ust", "gov"), horizon="12 mois", risk="faible à modéré", importance=2, category="Obligations"))
    # ---- volatilité
    vo = tens.get("volatilite")
    if vo is not None and vo > 75:
        out.append(rule("Volatilité forte",
                        f"La volatilité est notée {n(vo, 0)}/100 (seuil : 75) : les marchés bougent beaucoup plus que d'habitude.",
                        "Éviter l'effet de levier, étaler les achats sur plusieurs semaines, et préférer des actions qui bougent moins que le marché.",
                        sup("minvol"), horizon="1 à 3 mois", importance=3, category="Protection"))
    elif vo is not None and vo < 15:
        out.append(rule("Volatilité très basse",
                        f"La volatilité est notée {n(vo, 0)}/100 (seuil : 15) : le marché est très calme, parfois trop.",
                        "Le calme précède souvent les secousses : c'est le bon moment pour prendre une partie de ses gains et rééquilibrer vers l'allocation cible.",
                        sup("cash"), horizon="1 à 3 mois", importance=1, category="Protection"))
    # ---- inflation
    inf = last("inflation")
    if inf is not None and inf > 3:
        out.append(rule("Inflation élevée",
                        f"L'inflation est à {n(inf)} % (seuil : 3 %, cible des banques centrales : 2 %).",
                        "Les obligations indexées sur l'inflation protègent le pouvoir d'achat ; les matières premières montent souvent avec les prix.",
                        sup("infl", "commo"), horizon="6 à 12 mois", importance=2, category="Obligations"))
    elif inf is not None and inf < 1:
        out.append(rule("Inflation très basse",
                        f"L'inflation n'est que de {n(inf)} % (seuil : 1 %) : risque de déflation et de nouvelles baisses de taux.",
                        "Les obligations d'État longues sont favorisées : leur prix monte quand la banque centrale assouplit.",
                        sup("gov"), horizon="12 mois", risk="faible à modéré", importance=2, category="Obligations"))
    # ---- crédit
    sp = tens.get("spreads")
    if sp is not None and sp > 70:
        out.append(rule("Crédit sous tension",
                        f"Les écarts de crédit sont notés {n(sp, 0)}/100 (seuil : 70) : les entreprises fragiles paient beaucoup plus cher pour emprunter.",
                        "Éviter les obligations à haut rendement et rester sur des émetteurs de qualité (catégorie « investment grade »).",
                        sup("corp"), importance=2, category="Obligations"))
    elif sp is not None and sp < 20:
        out.append(rule("Crédit très bon marché",
                        f"Les écarts de crédit sont notés {n(sp, 0)}/100 (seuil : 20) : le risque de défaut est très peu rémunéré.",
                        "Le haut rendement rapporte peu pour le risque pris : préférer les obligations d'entreprises de qualité.",
                        sup("corp"), importance=1, category="Obligations"))
    # ---- immobilier (toujours présent)
    bc = pillars.get("bc")
    alloc = cfg.ALLOCATION[zone]["Immobilier"]
    if bc is not None and bc >= 65:
        out.append(rule("Immobilier : sous pression des taux",
                        f"Le pilier Banques centrales est à {n(bc, 0)}/100 : le crédit est cher, ce qui pèse sur les prix de l'immobilier.",
                        f"Garder une petite part ({alloc} % dans l'allocation du jour), plutôt via des foncières cotées (revendables à tout moment). Les SCPI se réservent à un horizon de 8 ans et plus.",
                        sup("reit_eu"), horizon="12 mois et plus", importance=2, category="Immobilier"))
    elif (bc is not None and bc <= 40) or (ta is not None and ta < -0.25):
        out.append(rule("Immobilier : porté par la baisse des taux",
                        f"Le pilier Banques centrales est à {n(bc or 0, 0)}/100 : l'argent devient moins cher, ce qui soutient les prix et les loyers.",
                        f"Renforcer l'immobilier coté ({alloc} % dans l'allocation du jour) : foncières européennes ou mondiales. Les SCPI restent un placement de long terme (8 ans et plus).",
                        sup("reit_eu", "reit_world"), horizon="12 mois et plus", importance=2, category="Immobilier"))
    else:
        out.append(rule("Immobilier : part normale",
                        f"Le pilier Banques centrales est à {n(bc or 50, 0)}/100 : ni frein ni moteur marqué pour l'immobilier.",
                        f"Garder la part prévue ({alloc} % dans l'allocation du jour), en diversifiant entre bureaux, commerces, logistique et santé via un ETF de foncières cotées.",
                        sup("reit_world"), horizon="12 mois et plus", importance=1, category="Immobilier"))
    # ---- or
    raw_g = R.get("gold")
    if raw_g is not None and len(raw_g.dropna()) > 63:
        g = raw_g.dropna()
        gc = float((g.iloc[-1] / g.iloc[-64] - 1) * 100)
        if gc > 10:
            out.append(rule("Or en forte hausse",
                            f"L'or a pris {n(gc, 0)} % en 3 mois (seuil : +10 %).",
                            "Ne pas courir après la hausse : garder la part prévue et rééquilibrer si elle dépasse nettement sa cible.",
                            sup("gold"), horizon="6 mois", importance=1, category="Protection"))
        elif gc < -8:
            out.append(rule("Or en correction",
                            f"L'or a perdu {n(abs(gc), 0)} % en 3 mois (seuil : −8 %).",
                            "Point d'entrée possible pour constituer ou compléter la poche d'or, en plusieurs fois.",
                            sup("gold"), horizon="12 mois et plus", importance=1, category="Protection"))
    # ---- régime All Weather
    if regime:
        etf = {"Expansion désinflationniste": ("world", "corp"), "Surchauffe": ("commo", "value", "infl"),
               "Stagflation": ("gold", "infl", "commo"), "Ralentissement désinflationniste": ("gov", "quality")}[regime["name"]]
        out.append(rule(f"Régime : {regime['name'].lower()}",
                        f"{regime['description']} (indicateur avancé {sn(regime['growth_change'] or 0, 2)} pt sur 3 mois, inflation {sn(regime['inflation_change'] or 0, 2)} pt sur 6 mois).",
                        f"Classes d'actifs historiquement les plus porteuses dans ce régime : {regime['assets'][0].lower() + regime['assets'][1:]}",
                        sup(*etf), horizon="6 à 12 mois", importance=2, category="Allocation"))
    out.sort(key=lambda r: -r["importance"])
    return out
