"use client";

import { useMemo, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { Loading, PageTitle, ZoneBadge } from "@/components/ui";
import { colorOf, fmt, PILLAR_COLORS, useData, useRegion } from "@/lib/data";

const SOURCES = [
  ["FRED (Fed de Saint-Louis)", "Macro US, taux, spreads haut rendement, NFCI, crédit BIS, incertitude EPU", "https://fred.stlouisfed.org"],
  ["BCE Data Portal", "Courbe des taux zone euro, taux de dépôt, indicateur de stress CISS", "https://data.ecb.europa.eu"],
  ["Eurostat", "Chômage, sentiment économique", "https://ec.europa.eu/eurostat"],
  ["INSEE", "Climat des affaires, PIB et prix France", "https://www.insee.fr"],
  ["OCDE", "Indicateurs composites avancés (États-Unis, Chine, Japon, zone euro, France)", "https://data-explorer.oecd.org"],
  ["Yahoo Finance (Stooq en secours)", "Indices, VIX, VSTOXX, Brent, EUR/USD, dollar, or, taux 10 ans US", "https://finance.yahoo.com"],
  ["multpl (données Robert Shiller)", "PER et CAPE du S&P 500", "https://www.multpl.com"],
  ["Caldara et Iacoviello", "Indice de risque géopolitique (GPR)", "https://www.matteoiacoviello.com/gpr.htm"],
  ["Presse (RSS)", "Zonebourse, Les Echos, Boursorama, CNBC, MarketWatch, Nikkei Asia, SCMP, Reuters", ""],
];

export default function Methodologie() {
  const { region } = useRegion();
  const { data: scores, error } = useData("scores.json");
  const { data: inds } = useData("indicators.json");
  const { data: h } = useData("history.json");
  const [w, setW] = useState<Record<string, number>>({ macro: 20, bc: 25, marches: 20, risque: 20, flux: 15 });

  const custom = useMemo(() => {
    if (!h) return [];
    const H = h[region];
    const keys = Object.keys(w).filter((k) => H[k]);
    const out = [];
    for (let i = 0; i < h.dates.length; i += 7) {
      let num = 0, den = 0;
      for (const k of keys) {
        const v = H[k][i];
        if (v != null) { num += w[k] * v; den += w[k]; }
      }
      out.push({ date: h.dates[i], custom: den ? num / den : null, official: H.global[i] });
    }
    return out;
  }, [h, region, w]);

  if (!scores || !inds) return <Loading error={error} />;
  const R = scores.regions[region];
  const pill = R.pillars;
  const tot = pill.reduce((a: number, p: any) => a + (w[p.id] || 0), 0);
  const simScore = tot ? pill.reduce((a: number, p: any) => a + (w[p.id] || 0) * p.score, 0) / tot : null;

  return (
    <div className="space-y-5">
      <PageTitle title="Méthodologie">
        Comment le baromètre est construit, de la collecte des données au score final. Toute la méthode est appliquée de la même
        façon aux deux zones, Monde et Europe / France.
      </PageTitle>

      <div className="grid gap-4 lg:grid-cols-3">
        {[
          ["1. Collecte", "Des scripts Python interrogent automatiquement les sources ouvertes : marchés toutes les 15 minutes, données macro chaque jour, presse à 7 h et 18 h. Si une source tombe, la dernière valeur connue est gardée et signalée."],
          ["2. Normalisation", "Chaque série est comparée à ses 10 dernières années : z-score glissant (3 ans minimum), borné à ±3, converti en note de 0 à 100 par la loi normale. Les indicateurs de risque sont inversés ; l'inflation est notée selon son écart à la cible de 2 % (100 − 25 × |π − 2|)."],
          ["3. Agrégation", "Note d'indicateur = moyenne de ses composantes (pondérée par le PIB pour le Monde). Note de pilier = moyenne de ses indicateurs (taux anticipé ×2). Score = moyenne pondérée des piliers, puis retourné : 0 = euphorie, 100 = stress."],
        ].map(([t, d]) => (
          <div key={t} className="card"><h2 className="card-title">{t}</h2><p className="mt-2 text-sm muted">{d}</p></div>
        ))}
      </div>

      <div className="card">
        <h2 className="card-title">Formules</h2>
        <div className="mt-3 grid gap-3 font-mono text-sm sm:grid-cols-3">
          <div className="rounded-lg bg-surface p-3">z = (x − moyenne 10 ans) / écart-type 10 ans<br />note = 100 × Φ(z)</div>
          <div className="rounded-lg bg-surface p-3">Pilier = Σ vᵢ × noteᵢ<br />Global favorable = Σ Wₚ × Pilierₚ</div>
          <div className="rounded-lg bg-surface p-3">Score de tension = 100 − global favorable<br />Contribution = Wₚ × vᵢ × (Tᵢ − 50)</div>
        </div>
      </div>

      {/* simulateur */}
      <div className="card">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="card-title">Simulateur de pondérations · {R.label}</h2>
          <button onClick={() => setW({ macro: 20, bc: 25, marches: 20, risque: 20, flux: 15 })} className="text-xs text-accent">Revenir aux poids officiels</button>
        </div>
        <div className="mt-4 grid gap-6 lg:grid-cols-5">
          <div className="space-y-4 lg:col-span-2">
            {pill.map((p: any) => (
              <label key={p.id} className="block">
                <div className="flex justify-between text-sm">
                  <span><span className="mr-2 inline-block h-2.5 w-2.5 rounded-full" style={{ background: PILLAR_COLORS[p.id] }} />{p.label} <span className="muted">(note {fmt(p.score, 0)})</span></span>
                  <span className="num font-medium">{tot ? fmt(((w[p.id] || 0) / tot) * 100, 0) : 0} %</span>
                </div>
                <input type="range" min={0} max={50} value={w[p.id] || 0} onChange={(e) => setW({ ...w, [p.id]: Number(e.target.value) })} className="w-full" />
              </label>
            ))}
            <div className="flex items-center gap-3 rounded-lg bg-surface p-3">
              <span className="text-sm">Score avec vos poids :</span>
              <span className="num text-2xl font-semibold" style={{ color: colorOf(simScore) }}>{fmt(simScore, 1)}</span>
              <ZoneBadge score={simScore} />
              <span className="ml-auto text-xs muted">officiel : {fmt(R.score)}</span>
            </div>
          </div>
          <div className="h-[280px] lg:col-span-3">
            <ResponsiveContainer>
              <LineChart data={custom} margin={{ left: -16, right: 8 }}>
                <CartesianGrid stroke="rgb(var(--line))" strokeOpacity={0.4} vertical={false} />
                <XAxis dataKey="date" tickFormatter={(d) => d.slice(0, 4)} minTickGap={40} tick={{ fontSize: 10, fill: "rgb(var(--ink-soft))" }} stroke="rgb(var(--line))" />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "rgb(var(--ink-soft))" }} stroke="rgb(var(--line))" />
                <Tooltip formatter={(v: number, n: string) => [fmt(v), n === "custom" ? "Vos poids" : "Officiel"]} />
                <Line dataKey="official" stroke="#94a3b8" dot={false} strokeWidth={1.2} isAnimationActive={false} />
                <Line dataKey="custom" stroke="rgb(var(--accent))" dot={false} strokeWidth={2} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <p className="mt-3 text-xs muted">
          Robustesse : variante à poids égaux {fmt(R.variants.equal)} · variante pondérée par ACP {fmt(R.variants.pca)} · score officiel {fmt(R.score)}.
          Si les trois restent proches, le signal ne dépend pas d'un choix arbitraire de poids.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="card-title mb-3">Pourquoi ces poids ?</h2>
          <ul className="space-y-2 text-sm">
            <li><b>Banques centrales, 25 %</b> : le prix de l'argent conditionne tout. Quand les taux montent, les obligations baissent et les actions se dévalorisent. Le taux anticipé compte double.</li>
            <li><b>Risque et géopolitique, 20 %</b> : VIX et spreads réagissent les premiers aux chocs.</li>
            <li><b>Marchés, 20 %</b> : ils agrègent les anticipations de tous les acteurs, avec la valorisation en contrepoids.</li>
            <li><b>Macro, 20 %</b> : la base fondamentale, mais publiée avec retard.</li>
            <li><b>Flux et sentiment, 15 %</b> : utile pour la dynamique, mais plus bruité.</li>
          </ul>
        </div>
        <div className="card">
          <h2 className="card-title mb-3">Poids issus de l'ACP (1re composante)</h2>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            {Object.entries(R.pca_weights || {}).sort((a: any, b: any) => b[1] - a[1]).map(([k, v]: any) => (
              <div key={k} className="flex justify-between border-b border-line py-1"><span className="truncate pr-2">{inds[region].find((i: any) => i.id === k)?.label.split(" (")[0] || k}</span><span className="num">{fmt(v)} %</span></div>
            ))}
          </div>
        </div>
      </div>

      <div className="card overflow-x-auto">
        <h2 className="card-title mb-3">Les indicateurs ({inds[region].length} pour cette zone, 22 au total)</h2>
        <table className="w-full min-w-[640px] text-sm">
          <thead className="text-left text-xs muted"><tr><th className="pb-2 font-medium">Indicateur</th><th className="pb-2 font-medium">Pilier</th><th className="pb-2 font-medium">Sens</th><th className="pb-2 font-medium">Fréquence</th><th className="pb-2 font-medium">Composantes</th></tr></thead>
          <tbody>
            {inds[region].map((i: any) => (
              <tr key={i.id} className="border-t border-line align-top">
                <td className="py-2 pr-3 font-medium">{i.label}</td>
                <td className="py-2 pr-3">{i.pillar_label}</td>
                <td className="py-2 pr-3">{i.direction}</td>
                <td className="py-2 pr-3">{i.freq}</td>
                <td className="py-2 text-xs muted">{i.components.map((c: any) => c.name).join(" · ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs muted">Sens « + » : une hausse est favorable aux marchés (fait baisser la tension). « − » : défavorable. « cible 2 % » : écart à l'objectif des banques centrales.</p>
      </div>

      <div className="card">
        <h2 className="card-title mb-3">Sources</h2>
        <ul className="grid gap-2 text-sm sm:grid-cols-2">
          {SOURCES.map(([n, d, u]) => (
            <li key={n} className="rounded-lg border border-line p-3">
              {u ? <a href={u} target="_blank" rel="noreferrer" className="font-medium hover:text-accent">{n} ↗</a> : <span className="font-medium">{n}</span>}
              <p className="text-xs muted">{d}</p>
            </li>
          ))}
        </ul>
      </div>

      <div className="card text-sm">
        <h2 className="card-title mb-2">Limites</h2>
        <ul className="list-disc space-y-1 pl-5 muted">
          <li>Données de marché gratuites différées d'environ 15 minutes : suffisant pour un baromètre de fond.</li>
          <li>Yahoo Finance n'est pas une API officielle ; Stooq et FRED servent de secours.</li>
          <li>Le PER européen et les flux de capitaux détaillés sont payants : la valorisation européenne utilise un proxy (cours / moyenne 10 ans).</li>
          <li>Le sentiment des news démarre avec l'application : sa note utilise un Min-Max sur l'historique disponible tant qu'il est court.</li>
          <li>Le test historique utilise des rendements approximés (indices de prix, duration obligataire de 8 ans).</li>
        </ul>
      </div>
    </div>
  );
}
