"""Revue de presse biquotidienne et sentiment des news par dictionnaire (sans IA)."""
from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import feedparser
import requests

import lexicon as lx
from sources import UA

GN = "https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"


def gnews(q: str, lang: str = "fr") -> str:
    if lang == "fr":
        return GN.format(q=quote_plus(q), hl="fr", gl="FR", ceid="FR:fr")
    return GN.format(q=quote_plus(q), hl="en-US", gl="US", ceid="US:en")


# Rubrique -> liste de (nom de la source, URL du flux, langue)
FEEDS = {
    "europe": [
        ("Zonebourse", gnews("site:zonebourse.com when:1d"), "fr"),
        ("Zonebourse", "https://www.zonebourse.com/rss/", "fr"),
        ("Les Echos", "https://syndication.lesechos.fr/rss/rss_finance-marches.xml", "fr"),
        ("Les Echos", "https://syndication.lesechos.fr/rss/rss_economie.xml", "fr"),
        ("BFM Bourse", gnews("site:tradingsat.com OR site:bfmtv.com bourse when:1d"), "fr"),
        ("Le Figaro Bourse", "https://www.lefigaro.fr/rss/figaro_bourse.xml", "fr"),
        ("Google Actualités", gnews("bourse OR CAC 40 OR BCE OR économie zone euro when:1d"), "fr"),
    ],
    "international": [
        ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html", "en"),
        ("CNBC", "https://www.cnbc.com/id/20910258/device/rss/rss.html", "en"),
        ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories", "en"),
        ("Nikkei Asia", gnews("site:asia.nikkei.com markets when:1d", "en"), "en"),
        ("South China Morning Post", "https://www.scmp.com/rss/92/feed", "en"),
        ("Reuters", gnews("site:reuters.com markets when:1d", "en"), "en"),
        ("Google News", gnews("stock market OR Fed OR China economy OR Japan economy when:1d", "en"), "en"),
    ],
}
AKTIONNAIRE = "https://www.instagram.com/aktionnaire/"

TAG_RE = re.compile(r"<[^>]+>")
WORD_RE = re.compile(r"[a-zA-ZÀ-ÿœŒ'\-]+")
STOP = set("""le la les un une des de du d l et en à au aux pour par sur dans avec est sont the a an of to in on for
and is are at by with from as its it that this be has have after over new says said vs""".split())


def latin(text: str) -> bool:
    """Écarte les titres en écriture non latine (le dictionnaire est français / anglais)."""
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum(c <= "ɏ" for c in letters) / len(letters) >= 0.8


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", text or ""))).strip()


def tokens(text: str) -> list[str]:
    toks = [t.strip("'-").lower() for t in WORD_RE.findall(text.replace("’", "'"))]
    out = []
    for t in toks:
        if "'" in t:  # l'inflation -> inflation ; doesn't -> n't
            a, b = t.split("'", 1)
            if b == "t":
                out.extend([a[:-1], "n't"] if a.endswith("n") else [t])
                continue
            t = b
        if t:
            out.append(t)
    return out


def _match_fr(tok: str, stems: list[str]) -> bool:
    return any(tok.startswith(s) if len(s) >= 4 else tok == s for s in stems)


def _match_en(tok: str, words: set[str]) -> bool:
    return tok in words or (tok.endswith("s") and tok[:-1] in words)


def sentiment(text: str, lang: str) -> tuple[float, int, int]:
    """(score de −1 à +1, nb de mots positifs, nb de mots négatifs), négations gérées."""
    toks = tokens(text)
    if lang == "fr":
        pos_s = [w for w in lx.FR_POS if "_" not in w]
        neg_s = [w for w in lx.FR_NEG if "_" not in w]
        pos_m = {w for w in lx.FR_POS if "_" in w}
        neg_m = {w for w in lx.FR_NEG if "_" in w}
        negs = lx.NEGATIONS_FR
        is_pos = lambda t: _match_fr(t, pos_s)  # noqa: E731
        is_neg = lambda t: _match_fr(t, neg_s)  # noqa: E731
    else:
        pos_set = {w for w in lx.EN_POS if "_" not in w}
        neg_set = {w for w in lx.EN_NEG if "_" not in w}
        pos_m = {w for w in lx.EN_POS if "_" in w}
        neg_m = {w for w in lx.EN_NEG if "_" in w}
        negs = lx.NEGATIONS_EN
        is_pos = lambda t: _match_en(t, pos_set)  # noqa: E731
        is_neg = lambda t: _match_en(t, neg_set)  # noqa: E731
    pos = neg = 0
    skip = set()
    # expressions de plusieurs mots d'abord (« baisse des taux » est positif, pas « baisse »)
    for n in (3, 2):
        for i in range(len(toks) - n + 1):
            g = "_".join(toks[i:i + n])
            if g in pos_m or g in neg_m:
                negated = any(t in negs for t in toks[max(0, i - 3):i])
                good = (g in pos_m) != negated
                pos, neg = (pos + 1, neg) if good else (pos, neg + 1)
                skip.update(range(i, i + n))
    for i, t in enumerate(toks):
        if i in skip or t in STOP or len(t) < 3:
            continue
        p, q = is_pos(t), is_neg(t)
        if p == q:
            continue
        negated = any(x in negs for x in toks[max(0, i - 3):i])
        if p != negated:
            pos += 1
        else:
            neg += 1
    tot = pos + neg
    return ((pos - neg) / tot if tot else 0.0), pos, neg


def tone(score: float) -> str:
    if score > 0.25:
        return "positif"
    if score > 0.05:
        return "plutôt positif"
    if score >= -0.05:
        return "neutre"
    if score >= -0.25:
        return "prudent"
    return "négatif"


def fetch_feed(url: str) -> list:
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    return feedparser.parse(r.content).entries


def collect(hours: int = 36) -> dict:
    now = datetime.now(timezone.utc)
    out = {}
    for section, feeds in FEEDS.items():
        seen, items = set(), []
        for source, url, lang in feeds:
            try:
                entries = fetch_feed(url)
            except Exception as e:  # noqa: BLE001
                print(f"  [news] {source} indisponible : {e}")
                continue
            for e in entries[:60]:
                title = clean(e.get("title", ""))
                src = source
                # Google Actualités : « Titre - Média »
                if "news.google.com" in url and " - " in title:
                    title, src_name = title.rsplit(" - ", 1)
                    src = src_name.strip() if source.startswith("Google") else source
                key = re.sub(r"\W+", "", title.lower())[:80]
                if not title or key in seen or not latin(title):
                    continue
                seen.add(key)
                pub = e.get("published_parsed") or e.get("updated_parsed")
                dt = datetime(*pub[:6], tzinfo=timezone.utc) if pub else now
                if now - dt > timedelta(hours=hours):
                    continue
                summary = clean(e.get("summary", ""))
                if summary.lower().startswith(title.lower()[:40].lower()) or "news.google.com" in url:
                    summary = ""
                summary = re.split(r"(?<=[.!?])\s", summary)[0][:280] if summary else ""
                s, p, n = sentiment(f"{title}. {summary}", lang)
                items.append({
                    "title": title, "summary": summary, "link": e.get("link", ""), "source": src,
                    "lang": lang, "published": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "sentiment": round(s, 3), "pos": p, "neg": n,
                })
        out[section] = items
    return out


def _content_words(title: str) -> set[str]:
    return {t for t in tokens(title) if t not in STOP and len(t) > 3}


def cluster(items: list, top: int = 8) -> list:
    """Regroupe les articles qui parlent du même sujet et classe les sujets par nombre de sources."""
    groups: list[dict] = []
    for it in sorted(items, key=lambda x: x["published"], reverse=True):
        w = _content_words(it["title"])
        best, best_sim = None, 0.0
        for g in groups:
            inter = len(w & g["words"])
            sim = inter / max(1, min(len(w), len(g["words"])))
            if inter >= 2 and sim > best_sim:
                best, best_sim = g, sim
        if best and best_sim >= 0.34:
            best["items"].append(it)
            best["words"] |= w
        else:
            groups.append({"words": set(w), "items": [it]})
    topics = []
    for g in groups:
        lead = g["items"][0]
        sources = sorted({i["source"] for i in g["items"]})
        avg = sum(i["sentiment"] for i in g["items"]) / len(g["items"])
        recency = max(i["published"] for i in g["items"])
        topics.append({
            "title": lead["title"], "summary": lead["summary"] or next((i["summary"] for i in g["items"] if i["summary"]), ""),
            "link": lead["link"], "source": lead["source"], "sources": sources, "count": len(g["items"]),
            "sentiment": round(avg, 3), "tone": tone(avg), "published": recency,
            "others": [{"title": i["title"], "link": i["link"], "source": i["source"]} for i in g["items"][1:4]],
        })
    topics.sort(key=lambda t: (len(t["sources"]), t["count"], t["published"]), reverse=True)
    return topics[:top]


def dominant_theme(items: list) -> str | None:
    counts = {k: 0 for k in lx.THEMES}
    for it in items:
        toks = set(tokens(it["title"] + " " + it["summary"]))
        for theme, kws in lx.THEMES.items():
            if toks & set(kws):
                counts[theme] += 1
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else None


def daily_review(edition: str) -> dict:
    """Construit la revue de presse et les scores de sentiment du jour."""
    raw = collect()
    review = {"edition": edition, "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "aktionnaire": AKTIONNAIRE, "sections": {}}
    for section, items in raw.items():
        avg = sum(i["sentiment"] for i in items) / len(items) if items else 0.0
        theme = dominant_theme(items)
        avis = f"Ton {tone(avg)}" + (f", dominé par {theme}." if theme else ".")
        review["sections"][section] = {
            "label": "Europe / France" if section == "europe" else "International (États-Unis, Chine, Japon…)",
            "articles": len(items), "sentiment": round(avg, 3), "tone": tone(avg), "theme": theme,
            "avis": avis, "topics": cluster(items),
        }
    return review
