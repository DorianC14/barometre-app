"use client";

import { useMemo, useState } from "react";

/** Quantile de la loi normale (approximation d'Acklam, précision ~1e-9). */
function normInv(p: number) {
  const a = [-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.357751867269, -30.66479806614716, 2.506628277459239];
  const b = [-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572];
  const c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
  const d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416];
  const pl = 0.02425;
  if (p < pl) { const q = Math.sqrt(-2 * Math.log(p)); return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
  if (p > 1 - pl) { const q = Math.sqrt(-2 * Math.log(1 - p)); return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
  const q = p - 0.5, r = q * q;
  return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
}

/** Même calage que le score officiel : rang parmi les 10 années précédentes, puis 50 + 20 × Φ⁻¹(rang). */
function calibrate(values: (number | null)[], perYear: number) {
  const win = 10 * perYear, min = 3 * perYear;
  return values.map((x, i) => {
    if (x == null) return null;
    const hist = values.slice(Math.max(0, i - win + 1), i + 1).filter((v): v is number => v != null);
    if (hist.length < min) return null;
    let below = 0, eq = 0;
    for (const v of hist) { if (v < x) below++; else if (v === x) eq++; }
    const p = Math.min(0.999, Math.max(0.001, (below + eq / 2) / hist.length));
    return Math.max(0, Math.min(100, 50 + 20 * normInv(p)));
  });
}
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { Loading, PageTitle, ZoneBadge } from "@/components/ui";
import { colorOf, fmt, PILLAR_COLORS, useData, useRegion } from "@/lib/data";

const SOURCES = [
  ["FRED (Fed de Saint-Louis)", "Macro, taux, spreads de crédit (États-Unis, Europe, Asie), NFCI, crédit BRI, VIX, Brent, yen et yuan, indices US et Nikkei en secours", "https://fred.stlouisfed.org"],
  ["Banque des règlements internationaux (BRI)", "Taux directeurs de la Banque du Japon et de la Chine, inflation au Japon et en Chine", "https://data.bis.org"],
  ["Economic Policy Uncertainty (Baker, Bloom, Davis)", "Incertitude politique États-Unis, Europe, France et Japon", "https://www.policyuncertainty.com"],
  ["BCE Data Portal", "Courbe des taux zone euro, taux de dépôt, indicateur de stress CISS", "https://data.ecb.europa.eu"],
  ["Eurostat", "Chômage, sentiment économique", "https://ec.europa.eu/eurostat"],
  ["INSEE", "Climat des affaires, PIB et prix France", "https://www.insee.fr"],
  ["OCDE", "Indicateurs composites avancés (États-Unis, Chine, Japon, zone euro, France), PIB chinois, confiance des ménages et des entreprises", "https://data-explorer.oecd.org"],
  ["Twelve Data (API officielle, clé gratuite)", "Cours toutes les 15 min : S&P 500, Nasdaq, Euro Stoxx 50, CAC 40, Shanghai, or", "https://twelvedata.com"],
  ["STOXX (fichiers officiels)", "Euro Stoxx 50 et VSTOXX", "https://www.stoxx.com"],
  ["Yahoo Finance (secours)", "Indices, VIX, Brent, EUR/USD, dollar, or, taux 10 ans US quand il répond", "https://finance.yahoo.com"],
  ["multpl (données Robert Shiller)", "PER et CAPE du S&P 500", "https://www.multpl.com"],
  ["Caldara et Iacoviello", "Indice de risque géopolitique (GPR), mondial et par pays", "https://www.matteoiacoviello.com/gpr.htm"],
  ["Presse (RSS)", "Zonebourse, Les Echos, BFM Bourse, Le Figaro Bourse, CNBC, MarketWatch, Nikkei Asia, SCMP, Reuters (titres et résumés publics uniquement)", ""],
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
    const raw: (number | null)[] = [];
    for (let i = h.dates.length - 1; i >= 0; i -= 7) {   // pas de 7 jours, en partant d'aujourd'hui
      let num = 0, den = 0;
      for (const k of keys) {
        const v = H[k][i];
        if (v != null) { num += w[k] * v; den += w[k]; }
      }
      raw.unshift(den ? num / den : null);
      out.unshift({ date: h.dates[i], custom: null as number | null, official: H.global[i] });
    }
    // l'historique publié commence en 2007 : le calage du simulateur démarre donc 3 ans plus tard
    const cal = calibrate(raw, 52);
    out.forEach((o, i) => (o.custom = cal[i]));
    return out.filter((o) => o.custom != null);
  }, [h, region, w]);

  if (!scores || !inds) return <Loading error={error} />;
  const R = scores.regions[region];
  const pill = R.pillars;
  const tot = pill.reduce((a: number, p: any) => a + (w[p.id] || 0), 0);
  const simScore = custom.length ? custom[custom.length - 1].custom : null;

  return (
    <div className="space-y-5">
      <PageTitle title="Méthodologie">
        Comment le baromètre est construit, de la collecte des données au score final. La même méthode est appliquée aux six
        zones : Monde, Europe (zone euro), France, États-Unis, Chine et Japon, chacune avec ses propres données (sa banque
        centrale, ses taux, sa Bourse, sa devise).
      </PageTitle>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          ["1. Collecte", "Des scripts Python interrogent automatiquement les sources ouvertes : marchés toutes les 15 minutes, données macro chaque jour, presse à 8 h 30, 9 h 30, 17 h et 21 h. Si une source tombe, la dernière valeur connue est gardée et signalée."],
          ["2. Normalisation", "Chaque série est comparée à ses 10 dernières années : z-score glissant (3 ans minimum), borné à ±3, converti en note de 0 à 100 par la loi normale. Les indicateurs de risque sont inversés ; l'inflation est notée selon son écart à la cible de 2 % (100 − 25 × |π − 2|)."],
          ["3. Agrégation", "Note d'indicateur = moyenne de ses composantes (pondérée par le PIB pour le Monde). Note de pilier = moyenne de ses indicateurs (taux anticipé ×2, poids relevé jusqu'à ×1,5 après un choc). Score brut = moyenne pondérée des piliers, retournée : 0 = euphorie, 100 = stress."],
          ["4. Calage de l'échelle", "Une moyenne de 20 notes reste toujours proche de 50 : le score brut n'était jamais sorti de 27-77 depuis 2007. Il est donc classé parmi les scores des 10 années précédentes, puis converti : 1 écart-type = 20 points. Euphorie et stress représentent chacun environ 7 % des jours, le neutre environ 38 %."],
          ["5. Poids variables", "Selon la zone : chaque zone a ses propres indicateurs (une décision de la BCE pèse sur l'Europe et la France, pas sur le Japon). Selon la période : un indicateur dont la note bouge de plus de 10 points en 5 jours voit son poids augmenter, jusqu'à +50 % pour 25 points, puis revenir à la normale en 2 à 3 semaines."],
          ["6. Textes", "Le signal du jour, l'explication des piliers et l'analyse des périodes sont rédigés automatiquement à partir des chiffres, avec des tournures variées. Aucune IA : chaque phrase reprend une donnée vérifiable."],
        ].map(([t, d]) => (
          <div key={t} className="card"><h2 className="card-title">{t}</h2><p className="mt-2 text-sm muted">{d}</p></div>
        ))}
      </div>

      <div className="card">
        <h2 className="card-title">Formules</h2>
        <div className="mt-3 grid gap-3 font-mono text-sm sm:grid-cols-3">
          <div className="rounded-lg bg-surface p-3">z = (x − moyenne 10 ans) / écart-type 10 ans<br />note = 100 × Φ(z)</div>
          <div className="rounded-lg bg-surface p-3">Pilier = Σ vᵢ × noteᵢ<br />Global favorable = Σ Wₚ × Pilierₚ</div>
          <div className="rounded-lg bg-surface p-3">Brut = 100 − global favorable<br />Score = 50 + 20 × Φ⁻¹(rang du brut sur 10 ans)</div>
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
          Robustesse : variante à poids égaux {fmt(R.variants.equal)} · variante pondérée par ACP {fmt(R.variants.pca)} · score officiel {fmt(R.score)}
          (score brut avant calage : {fmt(R.variants.raw)}). Si les trois restent proches, le signal ne dépend pas d'un choix arbitraire de poids.
          Le simulateur applique le même calage, sur des points hebdomadaires.
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
          <li>Les cours en continu viennent de l'offre gratuite de Twelve Data (800 requêtes par jour) ; si elle ne répond pas, Yahoo, STOXX et FRED prennent le relais avec un jour de décalage.</li>
          <li>Le PER européen, japonais et chinois et les flux de capitaux détaillés sont payants : la valorisation hors États-Unis utilise un proxy (cours / moyenne 10 ans).</li>
          <li>Chine : pas de chômage fiable, pas de taux à 10 ans ni de VIX gratuits. Le score chinois repose sur moins d'indicateurs ; la volatilité y est mesurée sur les cours (volatilité réalisée 1 mois), comme au Japon.</li>
          <li>La France partage la politique monétaire et le taux 2 ans de la zone euro ; ses données propres sont le PIB, l'inflation, le chômage, le climat des affaires, l'OAT, l'écart avec le Bund, le CAC 40, le crédit et le stress financier (CISS France).</li>
          <li>Le calage compare chaque jour aux 10 années précédentes : une période durablement tendue (taux élevés depuis 2022, par exemple) finit par devenir la nouvelle normale.</li>
          <li>Le sentiment des news démarre avec l'application : sa note utilise un Min-Max sur l'historique disponible tant qu'il est court.</li>
          <li>Le test historique utilise des rendements approximés (indices de prix, duration obligataire de 8 ans).</li>
        </ul>
      </div>
    </div>
  );
}
