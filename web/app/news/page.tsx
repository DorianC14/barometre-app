"use client";

import { Loading, PageTitle } from "@/components/ui";
import { dateFr, fmt, useData, useRegion } from "@/lib/data";

const toneColor = (s: number) => (s > 0.05 ? "#22c55e" : s < -0.05 ? "#ef4444" : "#94a3b8");

function SentimentMeter({ value }: { value: number }) {
  const pct = ((value + 1) / 2) * 100;
  return (
    <div>
      <div className="relative h-2.5 rounded-full" style={{ background: "linear-gradient(90deg,#ef4444,#94a3b8,#22c55e)" }}>
        <div className="absolute -top-1 h-4.5 w-1.5 -translate-x-1/2 rounded bg-ink" style={{ left: `${pct}%`, height: 18 }} />
      </div>
      <div className="mt-1 flex justify-between text-[10px] muted">
        <span>négatif</span>
        <span>neutre</span>
        <span>positif</span>
      </div>
    </div>
  );
}

export default function News() {
  const { region } = useRegion();
  const { data: news, error } = useData("news.json");
  if (error && !news)
    return (
      <div className="space-y-4">
        <PageTitle title="Revue de presse" />
        <div className="card text-sm muted">La première revue de presse sera publiée à la prochaine édition (8 h 30, 9 h 30, 17 h ou 21 h, heure de Paris).</div>
      </div>
    );
  if (!news) return <Loading />;
  const order = region === "europe" || region === "france" ? ["europe", "international"] : ["international", "europe"];
  const syn = news.synthese;

  return (
    <div className="space-y-5">
      <PageTitle title="Revue de presse économique et financière">
        Mise à jour quatre fois par jour, week-end compris (heure de Paris) : 8 h 30 juste avant l'ouverture de la Bourse de Paris,
        9 h 30 après l'ouverture, 17 h pour les news de la journée et 21 h pour le bilan. Les sujets sont classés selon le nombre de médias
        qui en parlent. Le ton est mesuré par dictionnaire de mots (Loughran-McDonald en anglais, dictionnaire maison en français).
      </PageTitle>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span className="rounded-full bg-accent/15 px-3 py-1 font-medium">Édition de {news.edition_label || news.edition}</span>
        <span className="muted">{dateFr(news.generated_at, true)}</span>
        <a href={news.aktionnaire} target="_blank" rel="noreferrer" className="ml-auto rounded-full border border-line px-3 py-1 text-xs hover:border-accent">
          Suivre Aktionnaire sur Instagram ↗
        </a>
        <a href="https://www.zonebourse.com" target="_blank" rel="noreferrer" className="rounded-full border border-line px-3 py-1 text-xs hover:border-accent">
          Zonebourse ↗
        </a>
      </div>

      {syn?.lines?.length > 0 && (
        <section className="card border-accent/40">
          <h2 className="text-base font-semibold">L'essentiel de la journée</h2>
          <ul className="mt-2 space-y-1.5 text-sm">
            {syn.lines.map((l: any, i: number) => (
              <li key={i} className="flex gap-3">
                <span className="num w-12 shrink-0 font-semibold text-accent">{l.time}</span>
                <span>
                  <a href={l.link} target="_blank" rel="noreferrer" className="font-medium hover:text-accent">{l.text}</a>
                  <span className="ml-1 text-xs muted">· {l.media}</span>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-sm muted">{syn.conclusion}</p>
        </section>
      )}
      <div className="grid gap-5 lg:grid-cols-2">
        {order.map((key) => {
          const s = news.sections[key];
          if (!s) return null;
          return (
            <section key={key} className="card space-y-4">
              <div>
                <h2 className="text-base font-semibold">{s.label}</h2>
                <p className="text-xs muted">{s.articles} articles analysés</p>
              </div>
              <div className="rounded-lg bg-surface p-3">
                <div className="mb-2 flex items-baseline justify-between text-sm">
                  <span className="font-medium">Avis du jour</span>
                  <span className="num text-xs" style={{ color: toneColor(s.sentiment) }}>sentiment {fmt(s.sentiment, 2)}</span>
                </div>
                <p className="mb-3 text-sm">{s.avis}</p>
                <SentimentMeter value={s.sentiment} />
              </div>
              <ol className="space-y-3">
                {s.topics.map((t: any, i: number) => (
                  <li key={t.link + i} className="flex gap-3 border-t border-line pt-3">
                    <span className="num w-5 shrink-0 text-sm font-semibold muted">{i + 1}</span>
                    <div className="min-w-0 flex-1">
                      <a href={t.link} target="_blank" rel="noreferrer" className="font-medium leading-snug hover:text-accent">{t.title}</a>
                      {t.summary && <p className="mt-1 text-sm muted">{t.summary}</p>}
                      <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs muted">
                        <span className="rounded px-1.5 py-0.5" style={{ background: `${toneColor(t.sentiment)}22`, color: toneColor(t.sentiment) }}>{t.tone}</span>
                        <span>{t.sources.join(", ")}</span>
                        <span>· {dateFr(t.published, true)}</span>
                      </div>
                      {t.others?.length > 0 && (
                        <details className="mt-1 text-xs">
                          <summary className="cursor-pointer muted">Voir aussi ({t.others.length})</summary>
                          <ul className="mt-1 space-y-0.5">
                            {t.others.map((o: any) => (
                              <li key={o.link}><a className="hover:text-accent" href={o.link} target="_blank" rel="noreferrer">{o.title}</a> <span className="muted">· {o.source}</span></li>
                            ))}
                          </ul>
                        </details>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          );
        })}
      </div>
      <p className="text-xs muted">
        Les articles proviennent de flux publics (RSS) ; seuls les titres et résumés librement accessibles sont utilisés. Le contenu
        réservé aux abonnés de Zonebourse n'est pas collecté. Instagram ne permettant pas la lecture automatique, le compte Aktionnaire est proposé en lien.
      </p>
    </div>
  );
}
