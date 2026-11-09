"use client";

import { useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Loading, PageTitle } from "@/components/ui";
import { dateFr, eventInRegion, fmt, PILLAR_COLORS, REGION_LABELS, useData, useRegion, ZONES } from "@/lib/data";

const RANGES = [
  { k: "1M", d: 31 },
  { k: "6M", d: 183 },
  { k: "1A", d: 366 },
  { k: "3A", d: 1096 },
  { k: "10A", d: 3653 },
  { k: "Tout", d: 99999 },
];
const PILLARS = [
  ["macro", "Macro"],
  ["bc", "Banques centrales"],
  ["marches", "Marchés"],
  ["risque", "Risque"],
  ["flux", "Flux et sentiment"],
];

export default function Historique() {
  const { region } = useRegion();
  const { data: h, error } = useData("history.json");
  const [range, setRange] = useState("10A");
  const [show, setShow] = useState<Record<string, boolean>>({ global: true, equal: false, pca: false });

  const data = useMemo(() => {
    if (!h) return [];
    const days = RANGES.find((r) => r.k === range)!.d;
    const H = h[region];
    const n = h.dates.length;
    const start = Math.max(0, n - days);
    const step = n - start > 1500 ? 7 : n - start > 400 ? 2 : 1;
    const out = [];
    for (let i = start; i < n; i += step) {
      const row: any = { date: h.dates[i], ts: Date.parse(h.dates[i]) };
      for (const k of Object.keys(H)) row[k] = H[k][i];
      out.push(row);
    }
    if (out.length && out[out.length - 1].date !== h.dates[n - 1]) {
      const row: any = { date: h.dates[n - 1], ts: Date.parse(h.dates[n - 1]) };
      for (const k of Object.keys(H)) row[k] = H[k][n - 1];
      out.push(row);
    }
    return out;
  }, [h, region, range]);

  if (!h) return <Loading error={error} />;
  const yearTicks = (() => {
    if (!data.length || ["1M", "6M", "1A"].includes(range)) return undefined;
    const y0 = new Date(data[0].ts).getFullYear() + 1, y1 = new Date(data[data.length - 1].ts).getFullYear();
    const every = y1 - y0 > 12 ? 2 : 1;
    const out = [];
    for (let y = y0; y <= y1; y += every) out.push(Date.UTC(y, 0, 1));
    return out;
  })();
  const first = data[0]?.date;
  const events = h.events
    .filter((e: any) => e.date >= first && eventInRegion(e, region))
    .map((e: any) => ({ ...e, level: e.level || "major" }));
  const short = ["1M", "6M", "1A"].includes(range);
  // sur longue période, seuls les grands événements de la liste historique sont tracés (lisibilité)
  const lines = events.filter((e: any) => short || (e.level === "major" && !e.auto));
  const period: string | undefined = h.periods?.[region]?.[range];
  const toggle = (k: string) => setShow((s) => ({ ...s, [k]: !s[k] }));
  const valid = data.filter((d) => d.global != null);
  const maxP = valid.reduce((a, d) => (d.global > a.global ? d : a), valid[0] || {});
  const minP = valid.reduce((a, d) => (d.global < a.global ? d : a), valid[0] || {});

  return (
    <div className="space-y-5">
      <PageTitle title={`Historique du score · ${REGION_LABELS[region]}`}>
        Score recalculé jour par jour depuis 2007 avec exactement la même méthode, sans utiliser d'information future : chaque jour
        est comparé aux dix années qui le précèdent. On vérifie ainsi qu'il réagit aux grands chocs (2008, 2020, 2022, droits de
        douane de 2025).
      </PageTitle>

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <div className="flex rounded-lg border border-line p-0.5">
          {RANGES.map((r) => (
            <button key={r.k} onClick={() => setRange(r.k)} className={`rounded-md px-3 py-1 ${range === r.k ? "bg-accent/15 font-semibold" : "muted"}`}>{r.k}</button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {[["global", "Score officiel", "rgb(var(--ink))"], ["equal", "Variante poids égaux", "#a3a3a3"], ["pca", "Variante ACP", "#e879f9"], ...PILLARS.map(([k, l]) => [k, l, PILLAR_COLORS[k]])].map(([k, l, c]) => (
            <button key={k} onClick={() => toggle(k)} className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${show[k] ? "border-accent" : "border-line muted"}`}>
              <span className="h-2 w-2 rounded-full" style={{ background: c }} />
              {l}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="h-[440px]">
          <ResponsiveContainer>
            <LineChart data={data} margin={{ top: 16, right: 16, left: -16, bottom: 0 }}>
              {ZONES.map((z, i) => (
                <ReferenceArea key={z.name} y1={i * 20} y2={(i + 1) * 20} fill={z.color} fillOpacity={0.07} ifOverflow="hidden" />
              ))}
              <CartesianGrid stroke="rgb(var(--line))" strokeOpacity={0.4} vertical={false} />
              <XAxis dataKey="ts" type="number" scale="time" domain={["dataMin", "dataMax"]} ticks={yearTicks} tickFormatter={(t) => (range === "1M" || range === "6M" ? new Date(t).toLocaleDateString("fr-FR", { day: "numeric", month: "short" }) : range === "1A" ? new Date(t).toLocaleDateString("fr-FR", { month: "short", year: "2-digit" }) : String(new Date(t).getFullYear()))} minTickGap={40} tick={{ fontSize: 11, fill: "rgb(var(--ink-soft))" }} stroke="rgb(var(--line))" />
              <YAxis domain={[0, 100]} ticks={[0, 20, 40, 60, 80, 100]} tick={{ fontSize: 11, fill: "rgb(var(--ink-soft))" }} stroke="rgb(var(--line))" />
              <Tooltip labelFormatter={(t) => dateFr(new Date(t).toISOString())} formatter={(v: number, n: string) => [fmt(v), ({ global: "Score", equal: "Poids égaux", pca: "ACP" } as any)[n] || PILLARS.find((p) => p[0] === n)?.[1] || n]} />
              {lines.map((e: any) => (
                <ReferenceLine key={e.date + e.label} x={Date.parse(e.date)} stroke={e.level === "major" ? "#ef4444" : "rgb(var(--ink-soft))"} strokeOpacity={e.level === "major" ? 0.55 : 0.35} strokeDasharray="3 4"
                  label={e.level === "major" && !short ? { value: e.label.split(/[,:(]/)[0].replace(/[«»]/g, "").trim().slice(0, 24), position: "insideTopLeft", fontSize: 10, fill: "rgb(var(--ink-soft))", angle: -90, dx: 10, dy: 90 } : undefined} />
              ))}
              {PILLARS.map(([k]) => show[k] && <Line key={k} dataKey={k} stroke={PILLAR_COLORS[k]} dot={false} strokeWidth={1.2} isAnimationActive={false} />)}
              {show.equal && <Line dataKey="equal" stroke="#a3a3a3" dot={false} strokeWidth={1.2} strokeDasharray="5 3" isAnimationActive={false} />}
              {show.pca && <Line dataKey="pca" stroke="#e879f9" dot={false} strokeWidth={1.2} strokeDasharray="2 2" isAnimationActive={false} />}
              {show.global && <Line dataKey="global" stroke="rgb(var(--ink))" dot={false} strokeWidth={2} isAnimationActive={false} />}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-xs muted">Bandes de couleur : zones du score (bleu euphorie → rouge stress). Lignes pointillées verticales : événements (rouge = majeur ; les mineurs apparaissent en gris sur 1 an ou moins).</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="card">
          <div className="text-xs muted">Plus forte tension sur la période</div>
          <div className="num text-2xl font-semibold text-red-500">{fmt(maxP?.global, 0)}</div>
          <div className="text-xs muted">{dateFr(maxP?.date)}</div>
        </div>
        <div className="card">
          <div className="text-xs muted">Plus faible tension sur la période</div>
          <div className="num text-2xl font-semibold text-blue-500">{fmt(minP?.global, 0)}</div>
          <div className="text-xs muted">{dateFr(minP?.date)}</div>
        </div>
      </div>
      {period && (
        <div className="card">
          <h2 className="card-title">Ce qui a changé sur la période ({range === "Tout" ? "depuis 2007" : range}) : causes et conséquences</h2>
          <p className="mt-2 text-sm leading-relaxed">{period}</p>
        </div>
      )}
      <div className="card">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="card-title">Événements repérés sur la période</h2>
          <span className="flex items-center gap-3 text-xs muted">
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-red-500" />majeur</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-ink" />mineur</span>
          </span>
        </div>
        {events.length ? (
          <ul className="mt-2 max-h-80 space-y-1 overflow-y-auto pr-1 text-sm">
            {[...events].reverse().map((e: any) => (
              <li key={e.date + e.label} className={`flex gap-3 ${e.level === "major" ? "font-medium text-red-600 dark:text-red-400" : "text-ink"}`}>
                <span className="num w-24 shrink-0 text-xs leading-5 muted">{dateFr(e.date)}</span>
                <span className={e.level === "major" ? "" : "text-[13px]"}>{e.label}{e.auto && <span className="ml-1 text-[10px] font-normal muted">(détecté automatiquement)</span>}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm muted">Aucun événement repéré sur cette période.</p>
        )}
        <p className="mt-2 text-[11px] muted">
          Liste historique sélectionnée à la main jusqu'à l'automne 2025, puis détection automatique : décisions de taux, séances
          à plus de 3 % sur les indices, variations du pétrole de plus de 8 % en une séance, poussées du VIX au-dessus de 30 et bonds du score.
        </p>
      </div>
    </div>
  );
}
