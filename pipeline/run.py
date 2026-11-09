"""Point d'entrée de l'actualisation automatique.

    python run.py --mode markets   # toutes les 15 min : cours de marché + recalcul des scores
    python run.py --mode full      # chaque jour : toutes les séries (macro, taux, crédit…) + recalcul
    python run.py --mode news      # 8 h 30, 9 h 30, 17 h et 21 h (Paris) : revue de presse + sentiment + recalcul

Les séries brutes sont gardées en cache dans data/raw/ : si une source ne répond pas,
la dernière valeur connue est conservée et signalée « en retard » dans l'application.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import advice
import config as cfg
import events as ev
import scoring as sc
import sources as src
import texts as tx

PARIS = ZoneInfo("Europe/Paris")

ROOT = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
RAW = ROOT / "raw"

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
            elif kind == "oecd_gdp":
                ser = src.oecd_gdp(ident)
            elif kind == "oecd_cpi":
                ser = src.oecd_cpi(ident)
            elif kind == "bis":
                ser = src.bis(ident)
            elif kind == "gpr_country":
                ser = src.gpr_country(ident)
            elif kind == "epu_japan":
                ser = src.epu_japan()
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


def pick_edition(now: datetime, done_today: set, scheduled: bool) -> dict | None:
    """Choisit l'édition à publier. Les tâches GitHub partent ~20 min avant l'heure prévue
    (elles sont souvent retardées) et en double, pour couvrir l'heure d'été et l'heure d'hiver :
    on retient l'édition la plus proche, si elle n'a pas déjà été publiée aujourd'hui."""
    local = now.astimezone(PARIS)
    best, best_gap = None, None
    for e in cfg.EDITIONS:
        h, m = map(int, e["time"].split(":"))
        target = local.replace(hour=h, minute=m, second=0, microsecond=0)
        gap = (local - target).total_seconds() / 60
        if -45 <= gap <= 90 and (best_gap is None or abs(gap) < abs(best_gap)):
            best, best_gap = e, gap
    if best is None and not scheduled:   # lancement manuel hors créneau : dernière édition passée
        past = [e for e in cfg.EDITIONS if e["time"] <= local.strftime("%H:%M")]
        best = past[-1] if past else cfg.EDITIONS[-1]
        return best
    if best is None or (scheduled and best["id"] in done_today):
        return None
    return best


def update_news(edition_id: str | None, force: bool = False) -> bool:
    import news
    news.EDITION_ORDER[:] = cfg.EDITIONS
    now = datetime.now(timezone.utc)
    paris_date = now.astimezone(PARIS).strftime("%Y-%m-%d")
    day_p = ROOT / "news_day.json"
    day = json.loads(day_p.read_text()) if day_p.exists() else {}
    done = {e["id"] for e in day.get("editions", [])} if day.get("date") == paris_date else set()
    if edition_id:
        edition = next((e for e in cfg.EDITIONS if e["id"] == edition_id), cfg.EDITIONS[0])
    else:
        edition = pick_edition(now, done, scheduled=os.environ.get("GITHUB_EVENT_NAME") == "schedule" and not force)
    if edition is None:
        print("  → hors créneau ou édition déjà publiée : rien à faire")
        return False
    review = news.daily_review(edition["id"], edition["label"])
    day = news.update_day(day, review, edition["id"], paris_date)
    review["synthese"] = day["synthese"]
    review["date"] = paris_date
    write_json("news.json", review)
    write_json("news_day.json", day)
    p = ROOT / "news_history.json"
    hist = json.loads(p.read_text()) if p.exists() else []
    secs = review["sections"]
    hist.append({
        "date": review["generated_at"],
        "edition": edition["id"],
        "world": secs["international"]["sentiment"] if secs["international"]["articles"] else None,
        "europe": secs["europe"]["sentiment"] if secs["europe"]["articles"] else None,
    })
    write_json("news_history.json", hist[-4000:])
    print(f"  ✓ revue de presse ({edition['label']}) : {secs['europe']['articles']} articles Europe, "
          f"{secs['international']['articles']} articles International")
    return True


# --------------------------------------------------------------------------- calcul et export
def write_json(name: str, obj):
    ROOT.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / f".{name}.tmp"
    tmp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False, default=str))
    tmp.replace(ROOT / name)


CALC_VERSION = 2   # change quand l'échelle du score change (remet à zéro la courbe intraday)


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
    today_s = today.strftime("%Y-%m-%d")
    index = pd.date_range(cfg.CALC_START, today, freq="D")
    pub = index >= pd.Timestamp(cfg.HISTORY_START)   # partie publiée de l'historique
    pub_index = index[pub]

    regions, indicators, hist = {}, {}, {"dates": [d.strftime("%Y-%m-%d") for d in pub_index]}
    results = {}
    for region in cfg.REGIONS:
        results[region] = sc.compute_region(R, region, index, used, today)

    events = ev.all_events(R, {r: results[r]["T"] for r in cfg.REGIONS}, today)

    for region, res in results.items():
        T = res["T"]
        score = float(T.iloc[-1])
        zone, ztext = cfg.zone_of(score)
        pillars = []
        for p in cfg.PILLAR_ORDER:
            if p in res["T_pillars"].columns:
                col = res["T_pillars"][p]
                recent = col[col.index > index[-1] - pd.Timedelta(days=cfg.CALIB_WINDOW_DAYS)].dropna()
                pillars.append({"id": p, "label": cfg.PILLARS[p]["label"],
                                "weight": round(cfg.PILLARS[p]["weight"] * 100),
                                "score": sc.r1(col.iloc[-1]), "score_7d": sc.r1(col.iloc[-8]),
                                "normal": sc.r1(recent.mean()) if len(recent) else None,
                                "points": res["pillar_points"].get(p)})
        for p in pillars:
            p["text"] = tx.pillar_text(p, p["normal"], res["indicators"], R, region, today_s)
        reg = sc.regime(res["composites"])
        signal = tx.signal(region, score, sc.r1(T.iloc[-8]), res["contributions"], res["indicators"],
                           res["boosts"], R, today_s)
        regions[region] = {
            "label": cfg.REGIONS[region],
            "score": sc.r1(score), "zone": zone, "zone_text": ztext,
            "percentile": tx.percentile(score),
            "score_7d": sc.r1(T.iloc[-8]), "score_30d": sc.r1(T.iloc[-31]),
            "signal": signal,
            "pillars": pillars,
            "contributions": res["contributions"],
            "boosts": res["boosts"],
            "calibration": res["calib"],
            "variants": {"equal": sc.r1(res["eq_T"].iloc[-1]),
                         "pca": sc.r1(res["pca_T"].iloc[-1]) if res["pca_T"] is not None else None,
                         "raw": res["calib"]["raw"]},
            "pca_weights": res["pca_w"],
            "regime": reg,
            "advice": {"allocation": cfg.ALLOCATION[zone], "zone": zone,
                       "rules": advice.advice_rules(res, region, zone, reg)},
            "backtest": sc.backtest(T, R, region),
            "available_indicators": sum(1 for i in res["indicators"] if i.get("available")),
            "total_indicators": len(res["indicators"]),
        }
        indicators[region] = res["indicators"]
        hist[region] = {
            "global": [sc.r1(x) for x in T[pub].values],
            "equal": [sc.r1(x) for x in res["eq_T"][pub].values],
            "pca": [sc.r1(x) for x in res["pca_T"][pub].values] if res["pca_T"] is not None else [],
            **{p: [sc.r1(x) for x in res["T_pillars"][p][pub].values] for p in res["T_pillars"].columns},
        }
        hist.setdefault("periods", {})[region] = tx.period_texts(
            region, T, res["T_pillars"], res["ind_F"], R, events, cfg.HISTORY_START)

    # écarts entre zones -> piste de surpondération géographique
    for region, r in regions.items():
        others = sorted(((k, v["score"]) for k, v in regions.items() if k not in ("world", region)), key=lambda x: x[1])
        calm_k, calm_v = others[0]
        if r["score"] - calm_v >= 10:
            r["advice"]["rules"].append(advice.rule(
                "Écart entre zones",
                f"La zone {cfg.REGIONS[calm_k]} affiche {tx.n(r['score'] - calm_v, 0)} points de tension de moins "
                f"({tx.n(calm_v, 0)} contre {tx.n(r['score'], 0)}).",
                f"Dans la poche actions, surpondérer la zone {cfg.REGIONS[calm_k]} par rapport à un indice mondial, "
                "sans dépasser un tiers de cette poche.",
                advice.sup(advice.REGION_ETF[calm_k]), importance=1, category="Allocation"))

    # point intraday (pour la variation sur 24 h et la courbe des 7 jours)
    intr_p = ROOT / "intraday.json"
    intraday = json.loads(intr_p.read_text()) if intr_p.exists() else []
    if isinstance(intraday, dict):
        intraday = intraday.get("points", [])
    if meta.get("calc_version") != CALC_VERSION:
        intraday = []           # nouvelle échelle : on repart d'une courbe vierge
        meta["calc_version"] = CALC_VERSION
    now = sc.now_utc()
    keys = list(cfg.REGIONS)
    intraday.append([now, *[regions[k]["score"] for k in keys]])
    cutoff = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
    intraday = [p for p in intraday if p[0] >= cutoff]
    target = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    past = [p for p in intraday if p[0] <= target]
    for i, region in enumerate(keys, start=1):
        regions[region]["score_24h"] = past[-1][i] if past and len(past[-1]) > i else sc.r1(results[region]["T"].iloc[-2])

    scores = {"updated_at": now, "order": keys, "regions": regions,
              "demo": bool(os.environ.get("BAROMETRE_DEMO"))}
    write_json("scores.json", scores)
    write_json("indicators.json", {"updated_at": now, **indicators})
    write_json("history.json", {"updated_at": now, "events": events, **hist})
    write_json("intraday.json", {"keys": keys, "points": intraday})
    meta["computed_at"] = now
    write_json("meta.json", meta)
    print("  → " + " · ".join(f"{regions[k]['label']} {regions[k]['score']} ({regions[k]['zone']})" for k in keys))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["markets", "full", "news", "compute"], default="full")
    ap.add_argument("--edition", default=None, help="preouverture / ouverture / journee / soir (revue de presse)")
    ap.add_argument("--force", action="store_true", help="publie l'édition même si elle existe déjà")
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
        if not update_news(a.edition, force=a.force):
            return
        meta["last_news"] = sc.now_utc()
    compute(meta)


if __name__ == "__main__":
    main()
