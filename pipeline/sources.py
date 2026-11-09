"""Collecte automatique des séries brutes depuis des sources ouvertes.

Chaque fonction renvoie une pd.Series indexée par date (DatetimeIndex, sans fuseau),
triée, sans valeurs manquantes. En cas d'échec, une exception est levée : l'appelant
se rabat alors sur la source de secours ou sur le cache local.
"""
from __future__ import annotations

import io
import json
import os
import re
import time

import pandas as pd
import requests

# On se présente honnêtement comme un script (pas de faux navigateur). Une source qui
# refuse les clients automatisés est abandonnée au profit de la suivante.
UA = {"User-Agent": f"python-requests/{requests.__version__}"}
SCRIPT_UA = UA
TIMEOUT = 40


def _get(url: str, params: dict | None = None, retries: int = 3, headers: dict | None = None,
         timeout: float = TIMEOUT, **kw) -> requests.Response:
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers or UA, timeout=timeout, **kw)
            if r.status_code == 200:
                return r
            last = RuntimeError(f"HTTP {r.status_code} sur {url}")
        except requests.RequestException as e:  # réseau
            last = e
        time.sleep(2 * (i + 1))
    raise last  # type: ignore[misc]


def _clean(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce").dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None) if getattr(s.index, "tz", None) else pd.to_datetime(s.index)
    s = s[~s.index.duplicated(keep="last")].sort_index()
    if s.empty:
        raise ValueError("série vide")
    return s.astype(float)


# --------------------------------------------------------------------------- FRED
def fred(series_id: str, start: str = "1990-01-01") -> pd.Series:
    """FRED (Fed de Saint-Louis). Le CSV public ne demande pas de clé API."""
    r = _get("https://fred.stlouisfed.org/graph/fredgraph.csv", {"id": series_id, "cosd": start},
             headers=SCRIPT_UA, timeout=25)
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["date", "value"]
    return _clean(df.set_index("date")["value"].replace(".", None))


# --------------------------------------------------------------------------- BCE
def ecb(key: str, start: str = "1999-01-01") -> pd.Series:
    """Portail de données de la BCE (API SDMX, sans clé). key = 'FLOW/SERIE'."""
    flow, series = key.split("/", 1)
    r = _get(
        f"https://data-api.ecb.europa.eu/service/data/{flow}/{series}",
        {"format": "csvdata", "startPeriod": start},
    )
    df = pd.read_csv(io.StringIO(r.text))
    return _clean(df.set_index("TIME_PERIOD")["OBS_VALUE"])


# --------------------------------------------------------------------------- Eurostat
def eurostat(dataset: str, filters: dict) -> pd.Series:
    """API JSON-stat d'Eurostat (sans clé)."""
    r = _get(
        f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}",
        {**filters, "format": "JSON", "lang": "fr"},
    )
    js = r.json()
    times = js["dimension"]["time"]["category"]["index"]  # {"2024-01": 0, ...}
    inv = {v: k for k, v in times.items()}
    # Une seule série après filtrage : la position = l'index de temps.
    values = {inv[int(k) % len(inv)]: v for k, v in js["value"].items()}
    s = pd.Series(values)
    s.index = pd.PeriodIndex(s.index.str.replace("M", "-"), freq="M").to_timestamp()
    return _clean(s)


# --------------------------------------------------------------------------- INSEE
def insee(idbank: str) -> pd.Series:
    """Banque de données macroéconomiques de l'INSEE (SDMX, sans clé)."""
    r = _get(f"https://bdm.insee.fr/series/sdmx/data/SERIES_BDM/{idbank}", {"startPeriod": "1995"})
    obs = re.findall(r'<Obs[^>]*TIME_PERIOD="([^"]+)"[^>]*OBS_VALUE="([^"]+)"', r.text)
    if not obs:
        obs = [(t, v) for v, t in re.findall(r'<Obs[^>]*OBS_VALUE="([^"]+)"[^>]*TIME_PERIOD="([^"]+)"', r.text)]
    s = pd.Series({t: v for t, v in obs})
    idx = s.index.str.replace(r"-Q(\d)", lambda m: f"-{(int(m.group(1)) - 1) * 3 + 1:02d}", regex=True)
    s.index = pd.to_datetime(idx)
    return _clean(s)


# --------------------------------------------------------------------------- OCDE
def oecd_cli(country: str) -> pd.Series:
    """Indicateur composite avancé de l'OCDE (amplitude ajustée, ~100 = tendance)."""
    url = (
        "https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI,4.1/"
        f"{country}.M.LI...AA...H"
    )
    r = _get(url, {"startPeriod": "1995-01", "format": "csvfilewithlabels"})
    df = pd.read_csv(io.StringIO(r.text))
    return _clean(df.set_index("TIME_PERIOD")["OBS_VALUE"])


def _oecd_csv(url: str, start: str) -> pd.Series:
    r = _get(url, {"startPeriod": start, "format": "csvfile"})
    df = pd.read_csv(io.StringIO(r.text))
    t = df["TIME_PERIOD"].astype(str)
    # trimestres « 2026-Q3 » -> premier mois du trimestre
    t = t.str.replace(r"-Q(\d)", lambda m: f"-{(int(m.group(1)) - 1) * 3 + 1:02d}", regex=True)
    return _clean(pd.Series(df["OBS_VALUE"].values, index=pd.to_datetime(t)))


def bis(key: str, start: str = "1995-01") -> pd.Series:
    """Banque des règlements internationaux (API SDMX, sans clé). key = 'FLUX/VERSION/SERIE'.
    Ex. « WS_LONG_CPI/1.0/M.JP.771 » (inflation sur 1 an), « WS_CBPOL/1.0/D.JP » (taux directeur)."""
    r = _get(f"https://stats.bis.org/api/v2/data/dataflow/BIS/{key}", {"startPeriod": start, "format": "csv"})
    df = pd.read_csv(io.StringIO(r.text))
    t = df["TIME_PERIOD"].astype(str)
    return _clean(pd.Series(df["OBS_VALUE"].values, index=pd.to_datetime(t)))


def oecd_cpi(country: str) -> pd.Series:
    """Inflation sur 1 an (%, indice des prix à la consommation), base de prix de l'OCDE.
    Couvre aussi la Chine, absente des séries FRED à jour."""
    return _oecd_csv(
        f"https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/{country}.M.N.CPI.PA._T.N.GY",
        "1995-01")


def oecd_gdp(country: str) -> pd.Series:
    """Croissance du PIB en volume sur 1 an (%), comptes trimestriels de l'OCDE."""
    return _oecd_csv(
        f"https://sdmx.oecd.org/public/rest/data/OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA,/Q.Y.{country}.S1.S1.B1GQ._Z._Z._Z.PC.L.GY.T0102",
        "1995-Q1")


# --------------------------------------------------------------------------- Yahoo
def _yahoo_params(rng: str, interval: str) -> dict:
    # range=max renvoie des points mensuels : on passe des bornes explicites pour du quotidien.
    if rng == "max":
        return {"period1": 0, "period2": int(time.time()), "interval": interval,
                "includePrePost": "false"}
    return {"range": rng, "interval": interval, "includePrePost": "false"}


def yahoo(ticker: str, rng: str = "max", interval: str = "1d") -> pd.Series:
    """Yahoo Finance (gratuit, non officiel, données différées ~15 min)."""
    last = None
    for host in ("query1", "query2"):
        try:
            r = _get(
                f"https://{host}.finance.yahoo.com/v8/finance/chart/{ticker}",
                _yahoo_params(rng, interval),
                retries=1, timeout=20,
            )
            res = r.json()["chart"]["result"][0]
            ts = pd.to_datetime(res["timestamp"], unit="s")
            close = res["indicators"]["quote"][0]["close"]
            s = pd.Series(close, index=ts)
            # Dernier cours en temps (quasi) réel
            meta = res.get("meta", {})
            if meta.get("regularMarketPrice") and meta.get("regularMarketTime"):
                t = pd.to_datetime(meta["regularMarketTime"], unit="s")
                s.loc[t] = meta["regularMarketPrice"]
            s.index = s.index.normalize() if interval == "1d" else s.index
            return _clean(s)
        except Exception as e:  # noqa: BLE001
            last = e
    raise last  # type: ignore[misc]


# --------------------------------------------------------------------------- Twelve Data
# Offre gratuite : 800 crédits par jour et 8 par minute (1 crédit = 1 série demandée).
# L'offre gratuite refuse les indices : le baromètre y prend 4 séries par actualisation (or XAU/USD,
# ETF FEZ pour l'Euro Stoxx 50, EWQ pour le CAC 40, MCHI pour la Chine) quand Yahoo ne répond pas ;
# SPY et ONEQ ne servent que si Yahoo et FRED tombent. Toutes les 15 min ≈ 400 crédits par jour.
# Clé : TWELVEDATA_API_KEY.
_TD_LAST = [0.0]
_TD_MIN_GAP = 8.0  # secondes entre deux appels (8 par minute)


def _td_memo_path():
    root = os.environ.get("DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    return os.path.join(root, "raw", "twelvedata_refus.json")


def _td_memo() -> dict:
    try:
        with open(_td_memo_path()) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _td_remember(symbol: str, msg: str):
    memo = _td_memo()
    memo[symbol] = {"until": time.time() + 7 * 86400, "message": msg[:200]}
    os.makedirs(os.path.dirname(_td_memo_path()), exist_ok=True)
    with open(_td_memo_path(), "w") as f:
        json.dump(memo, f, ensure_ascii=False, indent=1)


def twelvedata(symbol: str, quick: bool = False) -> pd.Series:
    """Twelve Data (API officielle, clé gratuite). symbol = « SPX », « XAU/USD », « 000001:SSE »…

    Un symbole refusé par l'offre gratuite est mis de côté 7 jours pour ne pas gaspiller de crédits.
    """
    key = os.environ.get("TWELVEDATA_API_KEY", "").strip()
    if not key:
        raise RuntimeError("TWELVEDATA_API_KEY absente")
    memo = _td_memo().get(symbol)
    if memo and memo.get("until", 0) > time.time():
        raise RuntimeError(f"symbole non couvert par l'offre ({memo.get('message', '')})")
    sym, _, exchange = symbol.partition(":")
    params = {"symbol": sym, "interval": "1day", "outputsize": 40 if quick else 5000,
              "order": "ASC", "timezone": "UTC", "apikey": key}
    if exchange:
        params["exchange"] = exchange
    wait = _TD_MIN_GAP - (time.time() - _TD_LAST[0])
    if wait > 0:
        time.sleep(wait)
    _TD_LAST[0] = time.time()
    r = requests.get("https://api.twelvedata.com/time_series", params=params, headers=UA, timeout=TIMEOUT)
    js = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code != 200 or js.get("status") == "error":
        code, msg = js.get("code", r.status_code), js.get("message", f"HTTP {r.status_code}")
        if code in (400, 403, 404):  # symbole inconnu ou réservé aux offres payantes
            _td_remember(symbol, msg)
        raise RuntimeError(f"Twelve Data {code} : {msg[:150]}")
    vals = js.get("values") or []
    s = pd.Series({v["datetime"][:10]: v["close"] for v in vals})
    return _clean(s)


def stoxx(stem: str) -> pd.Series:
    """STOXX (fichiers officiels publics). « h_3msx5e » = Euro Stoxx 50 sur 3 mois (l'historique
    long vient du cache), « h_v2tx » = VSTOXX depuis 1999."""
    r = _get(f"https://www.stoxx.com/document/Indices/Current/HistoricalData/{stem}.txt",
             retries=2, timeout=25)
    rows = [ln.split(";") for ln in r.text.splitlines() if ln.count(";") >= 2]
    vals = {pd.to_datetime(d.strip(), format="%d.%m.%Y", errors="coerce"): v.strip()
            for d, _, v, *rest in rows}
    s = pd.Series(vals)
    s = s[s.index.notna()]
    return _clean(s)


def stooq(symbol: str) -> pd.Series:
    """Stooq : source de secours pour les indices."""
    r = _get("https://stooq.com/q/d/l/", {"s": symbol, "i": "d"})
    df = pd.read_csv(io.StringIO(r.text))
    return _clean(df.set_index("Date")["Close"])


# --------------------------------------------------------------------------- Valorisation
def multpl(page: str) -> pd.Series:
    """multpl.com : PER et CAPE de Shiller du S&P 500 (mensuel)."""
    r = _get(f"https://www.multpl.com/{page}/table/by-month")
    tables = pd.read_html(io.StringIO(r.text))
    df = tables[0]
    df.columns = ["date", "value"]
    df["value"] = df["value"].astype(str).str.extract(r"([\d.]+)")[0]
    return _clean(df.set_index("date")["value"])


# --------------------------------------------------------------------------- Géopolitique
def gpr_daily() -> pd.Series:
    """Indice de risque géopolitique de Caldara et Iacoviello (quotidien)."""
    r = _get("https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls")
    df = pd.read_excel(io.BytesIO(r.content))
    date_col = "date" if "date" in df.columns else df.columns[0]
    val_col = "GPRD" if "GPRD" in df.columns else df.columns[1]
    s = df.set_index(pd.to_datetime(df[date_col]))[val_col]
    return _clean(s)


def gpr_country(code: str) -> pd.Series:
    """Risque géopolitique propre à un pays (Caldara et Iacoviello, mensuel). code = « CHN », « JPN »…"""
    r = _get("https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls")
    df = pd.read_excel(io.BytesIO(r.content))
    return _clean(pd.Series(df[f"GPRC_{code}"].values, index=pd.to_datetime(df["month"])))


def epu_japan() -> pd.Series:
    """Incertitude politique au Japon (Baker, Bloom, Davis, Arbatli et al.), mensuel."""
    r = _get("https://www.policyuncertainty.com/media/Japan_Policy_Uncertainty_Data.xlsx", timeout=30)
    df = pd.read_excel(io.BytesIO(r.content))
    df = df[pd.to_numeric(df["Year"], errors="coerce").notna() & pd.to_numeric(df["Month"], errors="coerce").notna()]
    idx = pd.to_datetime(dict(year=df["Year"].astype(int), month=df["Month"].astype(int), day=1))
    return _clean(pd.Series(df.iloc[:, 2].values, index=idx))


def epu_europe(country: str) -> pd.Series:
    """Indices d'incertitude politique (Baker, Bloom et Davis), fichier officiel Europe."""
    r = _get("https://www.policyuncertainty.com/media/Europe_Policy_Uncertainty_Data.xlsx", timeout=30)
    df = pd.read_excel(io.BytesIO(r.content))
    df = df[pd.to_numeric(df["Year"], errors="coerce").notna()]
    idx = pd.to_datetime(dict(year=df["Year"].astype(int), month=df["Month"].astype(int), day=1))
    return _clean(pd.Series(df[f"{country}_News_Index"].values, index=idx))
