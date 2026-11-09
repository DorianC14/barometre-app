"use client";

import Link from "next/link";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Bar, Delta, Gauge, Live, Loading, ZoneBadge } from "@/components/ui";
import {
  ASSET_COLORS, colorOf, dateFr, fmt, PILLAR_COLORS, REGION_COLORS, REGION_LABELS, REGIONS, signed, useData, useRegion, zoneOf, ZONES,
  type Region,
} from "@/lib/data";

/** Courbe intraday : nouveau format { keys, points } ou ancien tableau [t, monde, europe]. */
function intradayRows(raw: any): any[] {
  if (!raw) return [];
  const keys: string[] = Array.isArray(raw) ? ["world", "europe"] : raw.keys || [];
  const pts: any[] = Array.isArray(raw) ? raw : raw.points || [];
  return pts.map((p) => {
    const row: any = { t: p[0] };
    keys.forEach((k, i) => (row[k] = p[i + 1]));
    return row;
  });
}

export default function Dashboard() {
  const { region, setRegion } = useRegion();
  const { data: scores, error } = useData("scores.json");
  const { data: intraday } = useData<any>("intraday.json");
  const { data: news } = useData("news.json");
  if (!scores) return <Loading error={error} />;
  const R = scores.regions[region] || scores.regions.world;
  const order: Region[] = (scores.order || REGIONS).filter((r: string) => scores.regions[r]);
  const intra = intradayRows(intraday);
  const signal: string[] = Array.isArray(R.signal) ? R.signal : [R.signal];

  return (
    <div className="space-y-5">
      {/* --------- les 6 zones : un clic affiche la zone en grand */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
        {order.map((r) => {
          const s = scores.regions[r];
          const active = r === region;
          return (
            <button
              key={r}
              onClick={() => setRegion(r)}
              aria-pressed={active}
              className={`card flex flex-col gap-1 !p-3 text-left transition ${active ? "ring-2 ring-accent" : "hover:ring-1 hover:ring-line"}`}
            >
              <span className="text-xs font-semibold muted">{REGION_LABELS[r]}</span>
              <span className="flex items-baseline gap-1.5">
                <span className="num text-2xl font-semibold" style={{ color: colorOf(s.score) }}>{fmt(s.score, 0)}</span>
                <Delta now={s.score} before={s.score_24h} label="24 h" />
              </span>
              <ZoneBadge score={s.score} />
            </button>
          );
        })}
      </div>

      {/* --------- zone sélectionnée, en grand */}
      <div className="card grid gap-5 lg:grid-cols-5">
        <div className="flex flex-col items-center gap-4 sm:flex-row lg:col-span-2">
          <Gauge value={R.score} />
          <div className="flex-1 space-y-1.5 self-stretch sm:self-center">
            <div className="text-sm font-semibold muted">{R.label}</div>
            <div className="flex items-baseline gap-2">
              <Live value={R.score}>
                <span className="num text-5xl font-semibold tracking-tight" style={{ color: colorOf(R.score) }}>{fmt(R.score, 0)}</span>
              </Live>
              <span className="muted">/ 100</span>
            </div>
            <ZoneBadge score={R.score} big />
            <div className="flex flex-wrap gap-x-4 gap-y-1 pt-1">
              <Delta now={R.score} before={R.score_24h} label="sur 24 h" />
              <Delta now={R.score} before={R.score_7d} label="sur 7 jours" />
              <Delta now={R.score} before={R.score_30d} label="sur 30 jours" />
            </div>
            <div className="text-xs muted">{R.available_indicators} indicateurs sur {R.total_indicators} disponibles</div>
          </div>
        </div>
        <div className="space-y-2 lg:col-span-3">
          <span className="text-xs font-semibold uppercase tracking-wide text-accent">Signal du jour · {R.label}</span>
          <ul className="space-y-1.5 text-sm leading-relaxed sm:text-[15px]">
            {signal.map((l, i) => (
              <li key={i} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />{l}</li>
            ))}
          </ul>
        </div>
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
        <div className="min-w-0 lg:col-span-3"><ScoreBuild R={R} /></div>

        {/* --------- évolution récente + news */}
        <div className="min-w-0 space-y-4 lg:col-span-2">
          <div className="card">
            <h2 className="card-title">Évolution sur 7 jours (toutes les 15 min)</h2>
            <div className="h-[150px]">
              {intra.length > 1 ? (
                <ResponsiveContainer>
                  <LineChart data={intra} margin={{ top: 8, right: 8, left: -20 }}>
                    <XAxis dataKey="t" tickFormatter={(t) => {
                      const d = new Date(t);
                      const span = new Date(intra[intra.length - 1].t).getTime() - new Date(intra[0].t).getTime();
                      return span < 2 * 86400000
                        ? d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Paris" })
                        : d.toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", timeZone: "Europe/Paris" });
                    }} tick={{ fontSize: 10, fill: "rgb(var(--ink-soft))" }} stroke="rgb(var(--line))" minTickGap={30} />
                    <YAxis domain={[0, 100]} ticks={[0, 20, 40, 60, 80, 100]} tick={{ fontSize: 10, fill: "rgb(var(--ink-soft))" }} stroke="rgb(var(--line))" />
                    <Tooltip labelFormatter={(t) => dateFr(t, true)} formatter={(v: number, n: string) => [fmt(v), REGION_LABELS[n as Region] || n]} />
                    {order.map((r) => (
                      <Line key={r} dataKey={r} stroke={REGION_COLORS[r]} dot={false} strokeWidth={region === r ? 2.5 : 1} strokeOpacity={region === r ? 1 : 0.45} isAnimationActive={false} />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="pt-10 text-center text-xs muted">La courbe se construit à chaque mise à jour (toutes les 15 minutes).</p>
              )}
            </div>
            <div className="mt-1 flex flex-wrap gap-x-3 text-[11px] muted">
              {order.map((r) => (
                <span key={r} className="flex items-center gap-1"><span className="h-0.5 w-3" style={{ background: REGION_COLORS[r] }} />{REGION_LABELS[r]}</span>
              ))}
            </div>
          </div>
          <div className="card space-y-3">
            <div className="flex items-baseline justify-between">
              <h2 className="card-title">L'essentiel des news du jour</h2>
              <Link href="/news/" className="text-xs text-accent">Tout lire</Link>
            </div>
            {news?.synthese?.lines?.length ? (
              <>
                <ul className="space-y-2">
                  {news.synthese.lines.slice(0, 4).map((l: any, i: number) => (
                    <li key={i} className="text-sm leading-snug">
                      <span className="num mr-1.5 text-xs font-semibold text-accent">{l.time}</span>
                      <a href={l.link} target="_blank" rel="noreferrer" className="hover:text-accent">{l.text}</a>
                      <span className="ml-1 text-xs muted">· {l.media}</span>
                    </li>
                  ))}
                </ul>
                <p className="text-xs muted">{news.synthese.conclusion}</p>
              </>
            ) : (
              <p className="text-sm muted">La synthèse se remplit à chaque édition : 8 h 30, 9 h 30, 17 h et 21 h.</p>
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
            {Object.entries(R.advice.allocation).map(([k, v]: any) => (
              <div key={k} title={`${k} ${v} %`} style={{ width: `${v}%`, background: ASSET_COLORS[k] }} className="flex items-center justify-center overflow-hidden whitespace-nowrap">
                {v >= 25 ? `${k} ${v} %` : v >= 8 ? `${v} %` : ""}
              </div>
            ))}
          </div>
          <div className="mt-1.5 flex flex-wrap gap-x-3 text-[11px] muted">
            {Object.entries(R.advice.allocation).map(([k, v]: any) => (
              <span key={k} className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm" style={{ background: ASSET_COLORS[k] }} />{k} {v} %</span>
            ))}
          </div>
        </div>
      </Link>
    </div>
  );
}

/** « Comment on arrive au score du jour » : cascade de 50 (situation normale) jusqu'au score,
 *  pilier par pilier, sur la même échelle de 0 à 100 que la jauge. */
function ScoreBuild({ R }: { R: any }) {
  const steps: { label: string; color?: string; from: number; to: number; pts: number }[] = [];
  let cum = 50;
  for (const p of R.pillars) {
    const pts = p.points ?? 0;
    steps.push({ label: p.label, color: PILLAR_COLORS[p.id], from: cum, to: cum + pts, pts });
    cum += pts;
  }
  const adj = R.score - cum;
  if (Math.abs(adj) >= 0.5) {
    steps.push({ label: "Ajustement de l'échelle", from: cum, to: R.score, pts: adj });
  }
  const pos = (x: number) => `${Math.max(0, Math.min(100, x))}%`;
  const top = R.contributions.slice(0, 6);
  const maxAbs = Math.max(1, ...top.map((c: any) => Math.abs(c.contribution)));

  const Track = ({ children }: { children: React.ReactNode }) => (
    <div className="relative h-6 flex-1">
      <div className="absolute inset-0 flex overflow-hidden rounded">
        {ZONES.map((z) => <div key={z.name} className="h-full flex-1" style={{ background: z.color, opacity: 0.1 }} />)}
      </div>
      <div className="absolute inset-y-0 w-px bg-ink-soft/50" style={{ left: "50%" }} />
      {children}
    </div>
  );

  return (
    <div className="card h-full">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="card-title">Comment on arrive au score du jour</h2>
        <span className="text-xs muted">échelle 0 (euphorie) → 100 (stress)</span>
      </div>
      <p className="mt-1 text-xs muted">
        On part de 50, la situation normale des dix dernières années. Chaque pilier ajoute des points de tension (rouge) ou en retire (vert).
      </p>
      <div className="mt-4 space-y-2">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-sm sm:flex-nowrap">
          <span className="w-full shrink-0 truncate muted sm:w-44">Situation normale</span>
          <Track><div className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-ink bg-surface-raised" style={{ left: "50%" }} /></Track>
          <span className="num w-12 shrink-0 text-right sm:w-16 text-sm font-semibold">50</span>
        </div>
        {steps.map((s) => {
          const lo = Math.min(s.from, s.to), hi = Math.max(s.from, s.to);
          const up = s.pts > 0;
          return (
            <div key={s.label} className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-sm sm:flex-nowrap">
              <span className="flex w-full shrink-0 items-center gap-1.5 truncate sm:w-44">
                {s.color && <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: s.color }} />}
                {s.label}
              </span>
              <Track>
                <div className="absolute inset-y-1 rounded-sm" style={{ left: pos(lo), width: `max(3px, calc(${pos(hi)} - ${pos(lo)}))`, background: up ? "#ef4444" : "#22c55e" }} />
              </Track>
              <span className="num w-12 shrink-0 text-right sm:w-16 text-sm font-semibold" style={{ color: Math.abs(s.pts) < 0.5 ? "rgb(var(--ink-soft))" : up ? "#ef4444" : "#22c55e" }}>
                {signed(s.pts, 1)}
              </span>
            </div>
          );
        })}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 border-t border-line pt-2 text-sm sm:flex-nowrap">
          <span className="w-full shrink-0 font-semibold sm:w-44">Score du jour</span>
          <Track>
            <div className="absolute inset-y-0.5 left-0 rounded-sm" style={{ width: pos(R.score), background: colorOf(R.score), opacity: 0.85 }} />
          </Track>
          <span className="num w-12 shrink-0 text-right sm:w-16 text-base font-semibold" style={{ color: colorOf(R.score) }}>{fmt(R.score, 0)}</span>
        </div>
        <div className="flex gap-3">
          <span className="hidden shrink-0 sm:block sm:w-44" />
          <div className="flex flex-1 text-[10px] muted">
            {ZONES.map((z, i) => (
              <span key={z.name} className="flex-1 text-center" style={{ color: z.color }}>
                <span className="hidden sm:inline">{z.name}<br /></span><span className="muted">{i * 20}-{Math.min(100, (i + 1) * 20)}</span>
              </span>
            ))}
          </div>
          <span className="w-12 shrink-0 sm:w-16" />
        </div>
      </div>
      <details className="mt-4 text-sm">
        <summary className="cursor-pointer text-xs text-accent">Les 6 indicateurs qui pèsent le plus</summary>
        <ul className="mt-2 space-y-1.5">
          {top.map((c: any) => (
            <li key={c.id} className="flex items-center gap-3">
              <span className="w-28 shrink-0 truncate text-xs sm:w-44" title={c.label}>{c.label.split(" (")[0]}</span>
              <div className="relative h-2.5 flex-1">
                <div className="absolute inset-y-0 w-px bg-ink-soft/50" style={{ left: "50%" }} />
                <div className="absolute inset-y-0 rounded-sm" style={{
                  left: c.contribution >= 0 ? "50%" : `${50 - (Math.abs(c.contribution) / maxAbs) * 50}%`,
                  width: `${(Math.abs(c.contribution) / maxAbs) * 50}%`,
                  background: c.contribution > 0 ? "#ef4444" : "#22c55e",
                }} />
              </div>
              <span className="num w-12 shrink-0 text-right sm:w-16 text-xs" style={{ color: c.contribution > 0 ? "#ef4444" : "#22c55e" }}>{signed(c.contribution, 1)} pt</span>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-[11px] muted">En points de score : écart de l'indicateur à sa normale × son poids réel du jour.</p>
      </details>
    </div>
  );
}
