"""Point d'entrée de l'actualisation automatique.

    python run.py --mode markets   # toutes les 15 min : cours de marché + recalcul des scores
    python run.py --mode full      # chaque jour : toutes les séries (macro, taux, crédit…) + recalcul
    python run.py --mode news      # 7 h et 18 h : revue de presse + sentiment + recalcul

Les séries brutes sont gardées en cache dans data/raw/ : si une source ne répond pas,
la dernière valeur connue est conservée et signalée « en retard » dans l'application.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import config as cfg
import scoring as sc
import sources as src

ROOT = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
RAW = ROOT / "raw"

EVENTS = [
    ("2008-09-15", "Faillite de Lehman Brothers"),
    ("2010-05-06", "Crise grecque, flash crash"),
    ("2011-08-08", "Crise de la dette en zone euro, dégradation des États-Unis"),
    ("2015-08-24", "Krach chinois"),
    ("2016-06-24", "Vote du Brexit"),
    ("2018-12-24", "Chute de fin 2018 (Fed, guerre commerciale)"),
    ("2020-03-16", "Covid-19 : krach de mars 2020"),
    ("2022-02-24", "Invasion de l'Ukraine"),
    ("2022-10-12", "Pic d'inflation et des hausses de taux"),
    ("2023-03-13", "Faillite de Silicon Valley Bank"),
    ("2025-04-07", "Choc des droits de douane américains"),
]


# --------------------------------------------------------------------------- cache
def save_raw(name: str, s: pd.Series, source: str):
    RAW.mkdir(parents=True, exist_ok=True)
    df = s.rename("value").to_frame()
    df.index.name = "date"
    df.to_csv(RAW / f"{name}.csv")
    (RAW / f"{name}.src").write_text(source)


def load_raw(name: str):
    p = RAW / f"{name}.csv"
    if not p.exists():
        return None, None
    df = pd.read_csv(p, parse_dates=["date"], index_col="date")
    srcf = RAW / f"{name}.src"
    return df["value"].dropna(), (srcf.read_text().strip() if srcf.exists() else "")


INCREMENTAL = {"stoxx"}


def fetch_one(name: str, spec: dict, quick: bool = False):
    """Essaie chaque source dans l'ordre ; renvoie (série, type de source) ou lève l'erreur."""
    errors = []
    for s in spec["src"]:
        kind, ident = s[0], s[1]
        try:
            if kind == "fred":
                ser = src.fred(ident)
            elif kind == "ecb":
                ser = src.ecb(ident)
            elif kind == "eurostat":
                ser = src.eurostat(ident, s[2])
            elif kind == "insee":
                ser = src.insee(ident)
            elif kind == "oecd":
                ser = src.oecd_cli(ident)
            elif kind == "yahoo":
                ser = src.yahoo(ident, rng="1mo" if quick else "max")
            elif kind == "stooq":
                ser = src.stooq(ident)
            elif kind == "twelvedata":
                ser = src.twelvedata(ident, quick=quick)
                # le symbole fait partie de la source : un indice et un ETF n'ont pas la même échelle
                return ser, f"twelvedata:{ident}"
            elif kind == "epu":
                ser = src.epu_europe(ident)
            elif kind == "stoxx":
                ser = src.stoxx(ident)
            elif kind == "multpl":
                ser = src.multpl(ident)
            elif kind == "gpr":
                ser = src.gpr_daily()
            else:
                raise ValueError(kind)
            return ser, kind
        except Exception as e:  # noqa: BLE001
            errors.append(f"{kind}:{ident} → {e}")
    raise RuntimeError(" | ".join(errors))


def refresh(names: list[str], quick: bool, status: dict):
    for name in names:
        spec = cfg.SERIES[name]
        t0 = time.time()
        try:
            ser, kind = fetch_one(name, spec, quick=quick)
            old, old_kind = load_raw(name)
            if quick and (old is None or old_kind != kind) and kind not in INCREMENTAL:
                # changement de source : on reprend l'historique complet pour ne pas mélanger
                ser, kind = fetch_one(name, spec, quick=False)
            if old is not None and ((quick and old_kind == kind) or kind in INCREMENTAL):
                # mise à jour incrémentale : on garde l'historique, on remplace la fin
                # (les fichiers STOXX ne couvrent que 3 mois : on prolonge toujours le cache)
                ser = pd.concat([old[old.index < ser.index[0]], ser])
            save_raw(name, ser, kind)
            status[name] = {"ok": True, "source": kind, "last": ser.index[-1].strftime("%Y-%m-%d"),
                            "checked": sc.now_utc()}
            print(f"  ✓ {name:12s} {kind:8s} {ser.index[-1].date()}  ({time.time() - t0:.1f}s)")
        except Exception as e:  # noqa: BLE001
            prev = status.get(name, {})
            status[name] = {**prev, "ok": False, "error": str(e)[:300], "checked": sc.now_utc()}
            print(f"  ✗ {name:12s} {str(e)[:160]}")


# --------------------------------------------------------------------------- sentiment
def news_series() -> dict:
    p = ROOT / "news_history.json"
    if not p.exists():
        return {}
    hist = json.loads(p.read_text())
    out = {}
    for key, region in (("world", "news_world"), ("europe", "news_europe")):
        pts = [(h["date"], h[key]) for h in hist if h.get(key) is not None]
        if pts:
            s = pd.Series({pd.to_datetime(d, utc=True).tz_localize(None): v for d, v in pts}).sort_index()
            s = s.groupby(s.index.normalize()).mean()
            out[region] = s.rolling("7D").mean()
    return out


def update_news(edition: str):
    import news
    review = news.daily_review(edition)
    write_json("news.json", review)
    p = ROOT / "news_history.json"
    hist = json.loads(p.read_text()) if p.exists() else []
    secs = review["sections"]
    hist.append({
        "date": review["generated_at"],
        "edition": edition,
        "world": secs["international"]["sentiment"] if secs["international"]["articles"] else None,
        "europe": secs["europe"]["sentiment"] if secs["europe"]["articles"] else None,
    })
    write_json("news_history.json", hist[-2000:])
    print(f"  ✓ revue de presse : {secs['europe']['articles']} articles Europe, "
          f"{secs['international']['articles']} articles International")


# --------------------------------------------------------------------------- calcul et export
def write_json(name: str, obj):
    ROOT.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / f".{name}.tmp"
    tmp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False, default=str))
    tmp.replace(ROOT / name)


def compute(meta: dict):
    R, used = {}, {}
    for name in cfg.SERIES:
        s, kind = load_raw(name)
        if s is not None and not s.empty:
            R[name] = s
            used[name] = kind
    if "eurusd" in R:
        fx = R["eurusd"]
        for name, kind in used.items():
            if kind in cfg.ETF_EN_EUROS:
                R[name] = (R[name] / fx.reindex(R[name].index, method="ffill")).dropna()
    for k, v in news_series().items():
        R[k] = v
        used[k] = "news"
    if not R:
        print("Aucune donnée en cache : lancez d'abord --mode full.")
        sys.exit(1)

    today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    index = pd.date_range(cfg.HISTORY_START, today, freq="D")

    regions, indicators, hist = {}, {}, {"dates": [d.strftime("%Y-%m-%d") for d in index]}
    results = {}
    for region in cfg.REGIONS:
        res = sc.compute_region(R, region, index, used, today)
        results[region] = res
        T = res["T"]
        score = float(T.iloc[-1])
        zone, ztext = cfg.zone_of(score)
        pillars = []
        for p in cfg.PILLAR_ORDER:
            if p in res["T_pillars"].columns:
                col = res["T_pillars"][p]
                pillars.append({"id": p, "label": cfg.PILLARS[p]["label"],
                                "weight": round(cfg.PILLARS[p]["weight"] * 100),
                                "score": sc.r1(col.iloc[-1]), "score_7d": sc.r1(col.iloc[-8])})
        regions[region] = {
            "label": cfg.REGIONS[region],
            "score": sc.r1(score), "zone": zone, "zone_text": ztext,
            "score_7d": sc.r1(T.iloc[-8]), "score_30d": sc.r1(T.iloc[-31]),
            "signal": sc.signal_sentence(score, res["contributions"]),
            "pillars": pillars,
            "contributions": res["contributions"],
            "variants": {"equal": sc.r1(res["eq_T"].iloc[-1]),
                         "pca": sc.r1(res["pca_T"].iloc[-1]) if res["pca_T"] is not None else None},
            "pca_weights": res["pca_w"],
            "regime": sc.regime(res["composites"]),
            "advice": {"allocation": cfg.ALLOCATION[zone], "zone": zone, "rules": sc.advice_rules(res)},
            "backtest": sc.backtest(T, R, region),
            "available_indicators": sum(1 for i in res["indicators"] if i.get("available")),
            "total_indicators": len(res["indicators"]),
        }
        indicators[region] = res["indicators"]
        hist[region] = {
            "global": [sc.r1(x) for x in T.values],
            "equal": [sc.r1(x) for x in res["eq_T"].values],
            "pca": [sc.r1(x) for x in res["pca_T"].values] if res["pca_T"] is not None else [],
            **{p: [sc.r1(x) for x in res["T_pillars"][p].values] for p in res["T_pillars"].columns},
        }

    # écart Monde / Europe -> piste de surpondération
    diff = regions["world"]["score"] - regions["europe"]["score"]
    if abs(diff) >= 10:
        calm = "europe" if diff > 0 else "world"
        rule = {"title": "Écart entre zones",
                "why": f"Le score {cfg.REGIONS[calm]} est plus bas de {abs(diff):.0f} points (moins de tension).",
                "idea": f"Surpondérer la zone {cfg.REGIONS[calm]} dans la poche actions."}
        for r in regions.values():
            r["advice"]["rules"].append(rule)

    # point intraday (pour la variation sur 24 h et la courbe du jour)
    intr_p = ROOT / "intraday.json"
    intraday = json.loads(intr_p.read_text()) if intr_p.exists() else []
    now = sc.now_utc()
    intraday.append([now, regions["world"]["score"], regions["europe"]["score"]])
    cutoff = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
    intraday = [p for p in intraday if p[0] >= cutoff]
    for i, region in enumerate(("world", "europe"), start=1):
        target = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        past = [p for p in intraday if p[0] <= target]
        regions[region]["score_24h"] = past[-1][i] if past else sc.r1(results[region]["T"].iloc[-2])

    scores = {"updated_at": now, "regions": regions, "demo": bool(os.environ.get("BAROMETRE_DEMO"))}
    write_json("scores.json", scores)
    write_json("indicators.json", {"updated_at": now, **indicators})
    write_json("history.json", {"updated_at": now, "events": [{"date": d, "label": l} for d, l in EVENTS], **hist})
    write_json("intraday.json", intraday)
    meta["computed_at"] = now
    write_json("meta.json", meta)
    print(f"  → Monde {regions['world']['score']} ({regions['world']['zone']}) · "
          f"Europe/France {regions['europe']['score']} ({regions['europe']['zone']})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["markets", "full", "news", "compute"], default="full")
    ap.add_argument("--edition", default=None, help="matin / soir (revue de presse)")
    a = ap.parse_args()

    meta_p = ROOT / "meta.json"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    meta.setdefault("series", {})
    print(f"[{sc.now_utc()}] mode {a.mode}")

    if a.mode == "full":
        refresh(list(cfg.SERIES), quick=False, status=meta["series"])
        meta["last_full"] = sc.now_utc()
    elif a.mode == "markets":
        names = cfg.market_series()
        missing = [n for n in cfg.SERIES if load_raw(n)[0] is None]
        refresh(names, quick=True, status=meta["series"])
        if missing:  # premier lancement : on complète tout
            refresh([n for n in missing if n not in names], quick=False, status=meta["series"])
        meta["last_markets"] = sc.now_utc()
    elif a.mode == "news":
        hour = datetime.now(timezone.utc).hour
        update_news(a.edition or ("matin" if hour < 12 else "soir"))
        meta["last_news"] = sc.now_utc()
    compute(meta)


if __name__ == "__main__":
    main()
