"""Revue de presse SYNTHÉTIQUE pour tester l'affichage hors ligne (titres d'exemple, jamais publiés comme réels)."""
import json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import news  # noqa: E402

now = datetime.now(timezone.utc)
def item(t, src, lang, h):
    s, p, n = news.sentiment(t, lang)
    return {"title": t, "summary": "Résumé d'exemple pour tester l'affichage.", "link": f"https://example.com/{abs(hash(t))}",
            "source": src, "lang": lang, "published": (now - timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"), "sentiment": s}
eu = [item("[Exemple] La BCE maintient ses taux directeurs inchangés", "Les Echos", "fr", 1),
      item("[Exemple] Taux directeurs : la BCE maintient le statu quo", "Zonebourse", "fr", 2),
      item("[Exemple] Le CAC 40 rebondit, porté par le luxe", "Boursorama", "fr", 3),
      item("[Exemple] Craintes sur la dette française, l'OAT se tend", "Les Echos", "fr", 4)]
intl = [item("[Example] Stocks rally to record high on strong earnings", "CNBC", "en", 1),
        item("[Example] Oil prices tumble as OPEC output rises", "MarketWatch", "en", 2),
        item("[Example] China economy shows signs of slowdown", "Nikkei Asia", "en", 3)]
review = {"edition": "matin", "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "aktionnaire": news.AKTIONNAIRE, "sections": {}}
for key, items in (("europe", eu), ("international", intl)):
    avg = sum(i["sentiment"] for i in items) / len(items)
    review["sections"][key] = {"label": "Europe / France" if key == "europe" else "International (États-Unis, Chine, Japon…)",
        "articles": len(items), "sentiment": round(avg, 3), "tone": news.tone(avg), "theme": news.dominant_theme(items),
        "avis": f"Ton {news.tone(avg)}, dominé par {news.dominant_theme(items)}.", "topics": news.cluster(items)}
out = Path(sys.argv[1]); (out / "news.json").write_text(json.dumps(review, ensure_ascii=False))
print("ok", review["sections"]["europe"]["avis"])
