"use client";

import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts";
import { Bar, Delta, Loading, PageTitle, ZoneBadge } from "@/components/ui";
import { colorOf, dateFr, fmt, PILLAR_COLORS, useData, useRegion } from "@/lib/data";

export default function Piliers() {
  const { region } = useRegion();
  const { data: scores, error } = useData("scores.json");
  const { data: inds } = useData("indicators.json");
  if (!scores || !inds) return <Loading error={error} />;
  const R = scores.regions[region];
  const list: any[] = inds[region];
  const radar = R.pillars.map((p: any) => ({ pillar: p.label, score: p.score, before: p.score_7d }));

  return (
    <div className="space-y-5">
      <PageTitle title={`Piliers et contributions · ${R.label}`}>
        Le score global est la moyenne pondérée des 5 piliers, comparée ensuite aux dix dernières années. Chaque pilier est la
        moyenne de ses indicateurs (le taux anticipé compte double, et un indicateur qui bouge brutalement pèse temporairement
        plus lourd). Toutes les notes sont des notes de tension : 0 = euphorie, 100 = stress.
      </PageTitle>

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="card lg:col-span-2">
          <h2 className="card-title">Profil des piliers</h2>
          <div className="h-[300px]">
            <ResponsiveContainer>
              <RadarChart data={radar} outerRadius="72%">
                <PolarGrid stroke="rgb(var(--line))" />
                <PolarAngleAxis dataKey="pillar" tick={{ fontSize: 11, fill: "rgb(var(--ink))" }} />
                <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9, fill: "rgb(var(--ink-soft))" }} stroke="rgb(var(--line))" />
                <Radar name="Il y a 7 jours" dataKey="before" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.1} strokeDasharray="4 3" />
                <Radar name="Aujourd'hui" dataKey="score" stroke="rgb(var(--accent))" fill="rgb(var(--accent))" fillOpacity={0.25} />
                <Tooltip formatter={(v: number) => fmt(v)} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs muted">Trait plein : aujourd'hui. Pointillés : il y a 7 jours. Plus la surface est grande, plus la tension est forte.</p>
        </div>
        <div className="card lg:col-span-3">
          <h2 className="card-title mb-3">Poids réels dans le score du jour</h2>
          <table className="w-full text-sm">
            <thead className="text-left text-xs muted">
              <tr>
                <th className="pb-2 font-medium">Pilier</th>
                <th className="pb-2 font-medium">Poids</th>
                <th className="pb-2 font-medium">Note</th>
                <th className="pb-2 font-medium">Normale 10 ans</th>
                <th className="pb-2 font-medium">Apport au score</th>
              </tr>
            </thead>
            <tbody>
              {R.pillars.map((p: any) => {
                const apport = p.points ?? R.contributions.filter((c: any) => c.pillar === p.id).reduce((a: number, c: any) => a + c.contribution, 0);
                return (
                  <tr key={p.id} className="border-t border-line">
                    <td className="py-2">
                      <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full" style={{ background: PILLAR_COLORS[p.id] }} />
                      {p.label}
                    </td>
                    <td className="num">{p.weight} %</td>
                    <td className="num font-semibold" style={{ color: colorOf(p.score) }}>{fmt(p.score, 0)}</td>
                    <td className="num muted">{fmt(p.normal, 0)}</td>
                    <td className="num" style={{ color: apport > 0 ? "#ef4444" : "#22c55e" }}>
                      {apport > 0 ? "+" : "−"}
                      {fmt(Math.abs(apport), 2)} pt
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="mt-3 text-xs muted">
            Apport = points de score ajoutés (ou retirés) parce que le pilier est au-dessus (ou en dessous) de sa normale des dix
            dernières années, compte tenu de son poids. 50 + la somme des apports = score du jour ({fmt(R.score)}).
          </p>
          {R.boosts?.length > 0 && (
            <div className="mt-3 rounded-lg bg-amber-500/10 p-3 text-xs">
              <div className="mb-1 font-semibold text-amber-600 dark:text-amber-300">Poids temporairement relevés</div>
              <ul className="space-y-0.5">
                {R.boosts.map((b: any) => (
                  <li key={b.id}>
                    {b.label.split(" (")[0]} : poids ×{fmt(b.multiplier, 2)} après un mouvement de {fmt(Math.abs(b.change ?? 0), 0)} points le {dateFr(b.date)}
                  </li>
                ))}
              </ul>
              <p className="mt-1 muted">Un indicateur qui bouge brutalement pèse jusqu'à 50 % de plus, puis revient à son poids normal en 2 à 3 semaines.</p>
            </div>
          )}
        </div>
      </div>

      {R.pillars.map((p: any) => (
        <section key={p.id} id={p.id} className="card scroll-mt-32">
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <h2 className="text-base font-semibold">{p.label}</h2>
            <span className="text-xs muted">poids {p.weight} %</span>
            <ZoneBadge score={p.score} />
            <span className="num ml-auto text-lg font-semibold" style={{ color: colorOf(p.score) }}>{fmt(p.score, 0)} / 100</span>
            <Delta now={p.score} before={p.score_7d} label="sur 7 jours" />
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {list.filter((i) => i.pillar === p.id).map((i) => {
              const c = R.contributions.find((x: any) => x.id === i.id);
              const boost = R.boosts?.find((x: any) => x.id === i.id);
              return (
                <div key={i.id} className="rounded-lg border border-line p-3">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-sm font-medium leading-snug">{i.label}</span>
                    <span className="num text-sm font-semibold" style={{ color: colorOf(i.tension) }}>{i.available ? fmt(i.tension, 0) : "—"}</span>
                  </div>
                  <div className="my-2"><Bar value={i.tension} /></div>
                  <div className="flex flex-wrap justify-between gap-1 text-xs muted">
                    <span>Sens : {i.direction}{i.weight_in_pillar > 1 ? " · poids double" : ""}</span>
                    {c && <span className="num">poids réel {fmt(c.weight)} %{boost && <span className="text-amber-500"> · ×{fmt(boost.multiplier, 2)}</span>}</span>}
                  </div>
                  {!i.available && <p className="mt-1 text-xs text-amber-500">Source momentanément indisponible.</p>}
                </div>
              );
            })}
          </div>
          {p.text?.length > 0 && (
            <div className="mt-3 space-y-1 rounded-lg bg-surface p-3 text-sm leading-relaxed">
              {p.text.map((l: string, k: number) => (
                <p key={k} className={k === p.text.length - 1 ? "font-medium" : ""}>{l}</p>
              ))}
            </div>
          )}
        </section>
      ))}
    </div>
  );
}
