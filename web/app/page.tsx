"use client";

import Link from "next/link";
import { Bar as RBar, BarChart, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Bar, Delta, Gauge, Live, Loading, ZoneBadge } from "@/components/ui";
import { colorOf, dateFr, fmt, PILLAR_COLORS, signed, useData, useRegion } from "@/lib/data";

export default function Dashboard() {
  const { region, setRegion } = useRegion();
  const { data: scores, error } = useData("scores.json");
  const { data: intraday } = useData<any[]>("intraday.json");
  const { data: news } = useData("news.json");
  if (!scores) return <Loading error={error} />;
  const R = scores.regions[region];

  const contrib = [...R.contributions].slice(0, 10);
  const intra = (intraday || []).map((p: any[]) => ({ t: p[0], world: p[1], europe: p[2] }));
  const section = news?.sections?.[region === "world" ? "international" : "europe"];

  return (
    <div className="space-y-5">
      {/* --------- les deux jauges */}
      <div className="grid gap-4 md:grid-cols-2">
        {(["world", "europe"] as const).map((r) => {
          const s = scores.regions[r];
          const active = r === region;
          return (
            <button
              key={r}
              onClick={() => setRegion(r)}
              className={`card flex flex-col items-center gap-4 text-left transition sm:flex-row ${active ? "ring-2 ring-accent" : "hover:ring-1 hover:ring-line"}`}
            >
              <Gauge value={s.score} />
              <div className="flex-1 space-y-1.5 self-stretch sm:self-center">
                <div className="text-sm font-semibold muted">{s.label}</div>
                <div className="flex items-baseline gap-2">
                  <Live value={s.score}>
                    <span className="num text-5xl font-semibold tracking-tight" style={{ color: colorOf(s.score) }}>
                      {fmt(s.score, 0)}
                    </span>
                  </Live>
                  <span className="muted">/ 100</span>
                </div>
                <ZoneBadge score={s.score} big />
                <div className="flex flex-wrap gap-x-4 gap-y-1 pt-1">
                  <Delta now={s.score} before={s.score_24h} label="sur 24 h" />
                  <Delta now={s.score} before={s.score_7d} label="sur 7 jours" />
                  <Delta now={s.score} before={s.score_30d} label="sur 30 jours" />
                </div>
                <div className="text-xs muted">
                  {s.available_indicators} indicateurs sur {s.total_indicators} disponibles
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* --------- signal du jour */}
      <div className="card flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-accent">Signal du jour · {R.label}</span>
        <p className="text-sm sm:text-base">{R.signal}</p>
      </div>

      {/* --------- piliers */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {R.pillars.map((p: any) => (
          <Link key={p.id} href={`/piliers/#${p.id}`} className="card space-y-2 transition hover:ring-1 hover:ring-accent">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold leading-tight">{p.label}</span>
              <span className="text-[11px] muted">{p.weight} %</span>
            </div>
            <Bar value={p.score} />
            <div className="flex items-baseline justify-between">
              <span className="num text-lg font-semibold" style={{ color: colorOf(p.score) }}>
                {fmt(p.score, 0)}
                <span className="text-xs font-normal muted"> / 100</span>
              </span>
              <Delta now={p.score} before={p.score_7d} label="7 j" />
            </div>
          </Link>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        {/* --------- contributions */}
        <div className="card lg:col-span-3">
          <div className="flex items-baseline justify-between">
            <h2 className="card-title">Ce qui pèse le plus sur le score</h2>
            <span className="text-xs muted">points ajoutés ou retirés à 50</span>
          </div>
          <div className="h-[340px]">
            <ResponsiveContainer>
              <BarChart data={contrib} layout="vertical" margin={{ left: 8, right: 24, top: 12 }}>
                <XAxis type="number" tick={{ fontSize: 11, fill: "rgb(var(--ink-soft))" }} stroke="rgb(var(--line))" />
                <YAxis type="category" dataKey="label" width={150} tick={{ fontSize: 11, fill: "rgb(var(--ink))" }} tickFormatter={(l: string) => { const t = l.split(" (")[0]; return t.length > 24 ? t.slice(0, 23) + "…" : t; }} stroke="rgb(var(--line))" />
                <ReferenceLine x={0} stroke="rgb(var(--ink-soft))" />
                <Tooltip formatter={(v: number) => [`${signed(v, 2)} pt`, "Contribution"]} cursor={{ fill: "rgb(var(--line) / 0.3)" }} />
                <RBar dataKey="contribution" radius={3}>
                  {contrib.map((c: any) => (
                    <Cell key={c.id} fill={c.contribution > 0 ? "#ef4444" : "#22c55e"} />
                  ))}
                </RBar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs muted">Rouge : l'indicateur ajoute de la tension. Vert : il en retire. Score = 50 + somme des contributions.</p>
        </div>

        {/* --------- évolution récente + news */}
        <div className="space-y-4 lg:col-span-2">
          <div className="card">
            <h2 className="card-title">Évolution sur 7 jours (toutes les 15 min)</h2>
            <div className="h-[140px]">
              {intra.length > 1 ? (
                <ResponsiveContainer>
                  <LineChart data={intra} margin={{ top: 8, right: 8, left: -20 }}>
                    <XAxis dataKey="t" tickFormatter={(t) => new Date(t).toLocaleDateString("fr-FR", { weekday: "short" })} tick={{ fontSize: 10, fill: "rgb(var(--ink-soft))" }} stroke="rgb(var(--line))" minTickGap={30} />
                    <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10, fill: "rgb(var(--ink-soft))" }} stroke="rgb(var(--line))" />
                    <Tooltip labelFormatter={(t) => dateFr(t, true)} formatter={(v: number, n: string) => [fmt(v), n === "world" ? "Monde" : "Europe / France"]} />
                    <Line dataKey="world" stroke="#60a5fa" dot={false} strokeWidth={region === "world" ? 2.5 : 1} />
                    <Line dataKey="europe" stroke="#a78bfa" dot={false} strokeWidth={region === "europe" ? 2.5 : 1} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="pt-10 text-center text-xs muted">La courbe se construit à chaque mise à jour.</p>
              )}
            </div>
          </div>
          <div className="card space-y-3">
            <div className="flex items-baseline justify-between">
              <h2 className="card-title">Revue de presse</h2>
              <Link href="/news/" className="text-xs text-accent">Tout lire</Link>
            </div>
            {section ? (
              <>
                <p className="text-sm">
                  <span className="font-medium">Avis du jour : </span>
                  {section.avis}
                </p>
                <ul className="space-y-2">
                  {section.topics.slice(0, 3).map((t: any) => (
                    <li key={t.link} className="text-sm leading-snug">
                      <a href={t.link} target="_blank" rel="noreferrer" className="hover:text-accent">{t.title}</a>
                      <span className="ml-1 text-xs muted">· {t.source}</span>
                    </li>
                  ))}
                </ul>
                <p className="text-xs muted">Édition du {news.edition}, {dateFr(news.generated_at, true)}</p>
              </>
            ) : (
              <p className="text-sm muted">La première revue sera publiée à la prochaine édition (7 h ou 18 h).</p>
            )}
          </div>
        </div>
      </div>

      {/* --------- régime + allocation */}
      <Link href="/conseils/" className="card grid gap-4 transition hover:ring-1 hover:ring-accent sm:grid-cols-3">
        <div>
          <div className="text-xs muted">Régime économique (All Weather)</div>
          <div className="font-semibold">{R.regime?.name || "—"}</div>
          <div className="text-xs muted">{R.regime?.description}</div>
        </div>
        <div className="sm:col-span-2">
          <div className="mb-1.5 text-xs muted">Allocation indicative en zone « {R.advice.zone} » (supposition, pas un conseil personnalisé)</div>
          <div className="flex h-6 overflow-hidden rounded-md text-[11px] font-medium text-white">
            {Object.entries(R.advice.allocation).map(([k, v]: any, i) => (
              <div key={k} title={`${k} ${v} %`} style={{ width: `${v}%`, background: ["#2563eb", "#0891b2", "#ca8a04", "#64748b"][i] }} className="flex items-center justify-center overflow-hidden whitespace-nowrap">
                {v >= 25 ? `${k} ${v} %` : `${v} %`}
              </div>
            ))}
          </div>
          <div className="mt-1.5 flex flex-wrap gap-x-3 text-[11px] muted">
            {Object.keys(R.advice.allocation).map((k, i) => (
              <span key={k} className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm" style={{ background: ["#2563eb", "#0891b2", "#ca8a04", "#64748b"][i] }} />{k}</span>
            ))}
          </div>
        </div>
      </Link>
    </div>
  );
}
