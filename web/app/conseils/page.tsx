"use client";

import { Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { Disclaimer, Loading, PageTitle, ZoneBadge } from "@/components/ui";
import { ASSET_COLORS, fmt, useData, useRegion, ZONES } from "@/lib/data";

const ASSETS = ["Actions", "Obligations", "Immobilier", "Or", "Liquidités"];
const ALLOC: Record<string, Record<string, number>> = {
  Euphorie: { Actions: 45, Obligations: 25, Immobilier: 5, Or: 10, Liquidités: 15 },
  Favorable: { Actions: 55, Obligations: 20, Immobilier: 10, Or: 5, Liquidités: 10 },
  Neutre: { Actions: 40, Obligations: 30, Immobilier: 10, Or: 10, Liquidités: 10 },
  Prudence: { Actions: 28, Obligations: 37, Immobilier: 5, Or: 15, Liquidités: 15 },
  Stress: { Actions: 15, Obligations: 42, Immobilier: 3, Or: 20, Liquidités: 20 },
};
const CAT_COLORS: Record<string, string> = {
  Obligations: "#0891b2", Actions: "#2563eb", Secteurs: "#0d9488", Protection: "#ca8a04", Immobilier: "#9333ea", Allocation: "#64748b", Marchés: "#64748b",
};
const QUADS = [
  { g: true, i: false, name: "Expansion désinflationniste", assets: "Actions, obligations d'entreprises" },
  { g: true, i: true, name: "Surchauffe", assets: "Matières premières, actions value, obligations indexées" },
  { g: false, i: false, name: "Ralentissement désinflationniste", assets: "Obligations d'État longues, défensives" },
  { g: false, i: true, name: "Stagflation", assets: "Or, obligations indexées, matières premières" },
];

export default function Conseils() {
  const { region } = useRegion();
  const { data: scores, error } = useData("scores.json");
  if (!scores) return <Loading error={error} />;
  const R = scores.regions[region];
  const alloc = Object.entries(R.advice.allocation).map(([name, value]) => ({ name, value }));
  const bt = R.backtest;

  return (
    <div className="space-y-5">
      <PageTitle title={`Conseils d'investissement · ${R.label}`}>
        Pistes générées automatiquement à partir du score et de règles simples et transparentes. Ce sont des hypothèses, pas des certitudes.
      </PageTitle>
      <Disclaimer />

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="card-title">Allocation indicative du moment</h2>
            <ZoneBadge score={R.score} />
          </div>
          <p className="mt-1 text-xs muted">Profil équilibré, score de tension {fmt(R.score, 0)} / 100.</p>
          <div className="h-[230px]">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={alloc} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="85%" paddingAngle={2}>
                  {alloc.map((a) => <Cell key={a.name} fill={ASSET_COLORS[a.name]} />)}
                </Pie>
                <Tooltip formatter={(v: number) => `${v} %`} />
                <Legend formatter={(n, e: any) => `${n} ${e.payload.value} %`} wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card overflow-x-auto lg:col-span-3">
          <h2 className="card-title mb-3">Grille d'allocation par zone</h2>
          <table className="w-full min-w-[480px] text-sm">
            <thead className="text-left text-xs muted">
              <tr><th className="pb-2 font-medium">Score de tension</th>{ASSETS.map((a) => <th key={a} className="pb-2 font-medium">{a}</th>)}</tr>
            </thead>
            <tbody>
              {ZONES.map((z, i) => {
                const a = ALLOC[z.name];
                const cur = z.name === R.advice.zone;
                return (
                  <tr key={z.name} className={`border-t border-line ${cur ? "bg-accent/10 font-semibold" : ""}`}>
                    <td className="py-2"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-full" style={{ background: z.color }} />{i * 20} à {Math.min(100, z.max)} · {z.name}{cur && " ← aujourd'hui"}</td>
                    {ASSETS.map((k) => <td key={k} className="num">{a[k]} %</td>)}
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="mt-3 text-xs muted">En euphorie, la part actions baisse légèrement : approche contrariante, car les excès précèdent souvent les corrections.</p>
          <p className="mt-2 text-xs muted">
            <b className="text-ink">Immobilier</b> : immobilier coté (foncières, SIIC, REIT), achetable et revendable chaque jour en Bourse.
            Il est très sensible aux taux : sa part baisse quand la tension monte. Les SCPI (immobilier non coté) restent une piste
            de long terme (8 ans et plus), mais leur prix n'étant publié qu'une fois par an, elles ne sont pas modélisées ici.
          </p>
        </div>
      </div>

      <div className="card">
        <h2 className="card-title">Pistes du jour, déduites des indicateurs</h2>
        <p className="mb-3 mt-1 text-xs muted">
          Chaque piste part d'un constat chiffré avec son seuil de déclenchement. Les supports sont des exemples d'ETF cotés en
          euros (code ISIN pour les retrouver chez votre courtier), pas une recommandation : lisez leur document d'information (DIC) avant
          d'investir et vérifiez s'ils sont éligibles au PEA.
        </p>
        {R.advice.rules.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {R.advice.rules.map((r: any) => (
              <div key={r.title} className="flex flex-col rounded-lg border border-line p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="font-medium">{r.title}</div>
                  {r.category && (
                    <span className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium" style={{ background: `${CAT_COLORS[r.category] || "#64748b"}22`, color: CAT_COLORS[r.category] || "#64748b" }}>{r.category}</span>
                  )}
                </div>
                <p className="mt-1 text-sm muted"><span className="font-medium text-ink">Constat : </span>{r.why}</p>
                <p className="mt-2 text-sm"><span className="font-medium text-accent">Piste : </span>{r.idea}</p>
                {r.supports?.length > 0 && (
                  <div className="mt-2 space-y-1">
                    <div className="text-[11px] font-medium uppercase tracking-wide muted">Exemples de supports</div>
                    {r.supports.map((x: any) => (
                      <div key={x.isin} className="flex flex-wrap items-baseline gap-x-2 rounded bg-surface px-2 py-1 text-xs">
                        <span className="font-medium">{x.name}</span>
                        <span className="num muted">{x.isin}</span>
                        <span className="muted">· {x.kind}</span>
                      </div>
                    ))}
                  </div>
                )}
                {(r.horizon || r.risk) && (
                  <div className="mt-auto flex flex-wrap gap-x-4 pt-2 text-[11px] muted">
                    {r.horizon && <span>Horizon : {r.horizon}</span>}
                    {r.risk && <span>Risque : {r.risk}</span>}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm muted">Aucun signal particulier aujourd'hui : les règles (taux anticipés, pétrole, courbe des taux, géopolitique, valorisation, volatilité, inflation, crédit, immobilier, or) restent dans leur zone normale.</p>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="card-title">Régime économique (logique All Weather de Bridgewater)</h2>
          <p className="mb-3 mt-1 text-xs muted">
            Croissance mesurée par l'indicateur avancé de l'OCDE (variation sur 3 mois), inflation par sa variation sur 6 mois.
          </p>
          <div className="grid grid-cols-[auto_1fr_1fr] gap-2 text-xs">
            <div />
            <div className="text-center muted">Inflation en baisse</div>
            <div className="text-center muted">Inflation en hausse</div>
            {[true, false].map((g) => (
              <div key={String(g)} className="contents">
                <div className="flex items-center muted [writing-mode:vertical-rl] rotate-180">{g ? "Croissance ↑" : "Croissance ↓"}</div>
                {QUADS.filter((q) => q.g === g).sort((a, b) => Number(a.i) - Number(b.i)).map((q) => {
                  const cur = R.regime && R.regime.growth_up === q.g && R.regime.inflation_up === q.i;
                  return (
                    <div key={q.name} className={`rounded-lg border p-3 ${cur ? "border-accent bg-accent/15" : "border-line"}`}>
                      <div className="font-semibold">{q.name}{cur && " · actuel"}</div>
                      <div className="mt-1 muted">{q.assets}</div>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
          {R.regime && (
            <p className="mt-3 text-xs muted">
              Croissance (indicateur OCDE) : {R.regime.growth_change > 0 ? "+" : ""}{fmt(R.regime.growth_change, 2)} pt sur 3 mois · inflation : {R.regime.inflation_change > 0 ? "+" : ""}{fmt(R.regime.inflation_change, 2)} pt sur 6 mois.
            </p>
          )}
        </div>

        <div className="card">
          <h2 className="card-title">Test historique indicatif</h2>
          {bt ? (
            <>
              <p className="mb-2 mt-1 text-xs muted">Allocation selon la zone du mois précédent, comparée à un portefeuille fixe 60 % actions / 40 % obligations (base 100). Rendements approximés, hors frais.</p>
              <div className="h-[220px]">
                <ResponsiveContainer>
                  <LineChart data={bt.series.map((s: any[]) => ({ m: s[0], strat: s[1], bench: s[2] }))} margin={{ left: -16, right: 8 }}>
                    <CartesianGrid stroke="rgb(var(--line))" strokeOpacity={0.4} vertical={false} />
                    <XAxis dataKey="m" tickFormatter={(m) => m.slice(0, 4)} minTickGap={40} tick={{ fontSize: 10, fill: "rgb(var(--ink-soft))" }} stroke="rgb(var(--line))" />
                    <YAxis tick={{ fontSize: 10, fill: "rgb(var(--ink-soft))" }} stroke="rgb(var(--line))" domain={["auto", "auto"]} />
                    <Tooltip formatter={(v: number, n: string) => [fmt(v), n === "strat" ? "Allocation du baromètre" : "60/40 fixe"]} />
                    <Legend formatter={(n) => (n === "strat" ? "Allocation du baromètre" : "60/40 fixe")} wrapperStyle={{ fontSize: 11 }} />
                    <Line dataKey="strat" stroke="rgb(var(--accent))" dot={false} strokeWidth={2} />
                    <Line dataKey="bench" stroke="#94a3b8" dot={false} strokeWidth={1.5} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <table className="mt-2 w-full text-xs">
                <thead className="muted"><tr><th className="text-left font-medium" /><th className="font-medium">Rendement annuel</th><th className="font-medium">Volatilité</th><th className="font-medium">Pire baisse</th></tr></thead>
                <tbody className="num text-center">
                  <tr><td className="text-left">Baromètre</td><td>{fmt(bt.strategy.annual_return)} %</td><td>{fmt(bt.strategy.volatility)} %</td><td>{fmt(bt.strategy.max_drawdown)} %</td></tr>
                  <tr><td className="text-left">60/40</td><td>{fmt(bt.benchmark.annual_return)} %</td><td>{fmt(bt.benchmark.volatility)} %</td><td>{fmt(bt.benchmark.max_drawdown)} %</td></tr>
                </tbody>
              </table>
              <p className="mt-2 text-[11px] muted">Simulation passée : elle ne prouve rien pour l'avenir.</p>
            </>
          ) : (
            <p className="text-sm muted">Historique insuffisant pour la simulation.</p>
          )}
        </div>
      </div>
    </div>
  );
}
