"""Collecte automatique des séries brutes depuis des sources ouvertes.

Chaque fonction renvoie une pd.Series indexée par date (DatetimeIndex, sans fuseau),
triée, sans valeurs manquantes. En cas d'échec, une exception est levée : l'appelant
se rabat alors sur la source de secours ou sur le cache local.
"""
from __future__ import annotations

import io
import re
import time

import pandas as pd
import requests

UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}
TIMEOUT = 40


def _get(url: str, params: dict | None = None, retries: int = 3, **kw) -> requests.Response:
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=TIMEOUT, **kw)
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
    r = _get("https://fred.stlouisfed.org/graph/fredgraph.csv", {"id": series_id, "cosd": start})
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


# --------------------------------------------------------------------------- Yahoo
def yahoo(ticker: str, rng: str = "max", interval: str = "1d") -> pd.Series:
    """Yahoo Finance (gratuit, non officiel, données différées ~15 min)."""
    last = None
    for host in ("query1", "query2"):
        try:
            r = _get(
                f"https://{host}.finance.yahoo.com/v8/finance/chart/{ticker}",
                {"range": rng, "interval": interval, "includePrePost": "false"},
                retries=2,
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
