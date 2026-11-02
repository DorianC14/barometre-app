"use client";

import { useState } from "react";
import { Loading, PageTitle, Spark } from "@/components/ui";
import { colorOf, dateFr, fmt, useData, useRegion } from "@/lib/data";

export default function Donnees() {
  const { region } = useRegion();
  const { data: inds, error } = useData("indicators.json");
  const { data: meta } = useData("meta.json");
  const [pillar, setPillar] = useState("all");
  if (!inds) return <Loading error={error} />;
  const list: any[] = inds[region].filter((i: any) => pillar === "all" || i.pillar === pillar);
  const pillars = Array.from(new Map(inds[region].map((i: any) => [i.pillar, i.pillar_label])).entries()) as [string, string][];
  const rows = list.flatMap((i) => i.components.map((c: any, k: number) => ({ ind: i, c, first: k === 0, span: i.components.length })));
  const series = Object.entries(meta?.series || {}) as [string, any][];
  const ok = series.filter(([, s]) => s.ok).length;

  return (
    <div className="space-y-5">
      <PageTitle title="Données collectées">
        Valeurs brutes récupérées automatiquement, avec leur date, leur source et leur note de tension (0 = euphorie,
        100 = stress). Les marchés sont relus toutes les 15 minutes, les données macro chaque jour.
      </PageTitle>

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <button onClick={() => setPillar("all")} className={`rounded-full border px-3 py-1 ${pillar === "all" ? "border-accent bg-accent/10" : "border-line muted"}`}>Tous</button>
        {pillars.map(([id, label]) => (
          <button key={id} onClick={() => setPillar(id)} className={`rounded-full border px-3 py-1 ${pillar === id ? "border-accent bg-accent/10" : "border-line muted"}`}>{label}</button>
        ))}
        <span className="ml-auto text-xs muted">
          {meta && series.length > 0 && `${ok} séries sur ${series.length} à jour · collecte complète ${dateFr(meta.last_full, true)} · marchés ${dateFr(meta.last_markets, true)}`}
        </span>
      </div>

      <div className="card overflow-x-auto p-0 sm:p-0">
        <table className="w-full min-w-[860px] text-sm">
          <thead className="bg-surface text-left text-xs muted">
            <tr>
              <th className="px-4 py-3 font-medium">Indicateur</th>
              <th className="px-3 py-3 font-medium">Composante</th>
              <th className="px-3 py-3 text-right font-medium">Valeur</th>
              <th className="px-3 py-3 font-medium">Date</th>
              <th className="px-3 py-3 font-medium">1 an</th>
              <th className="px-3 py-3 text-right font-medium">Tension</th>
              <th className="px-3 py-3 font-medium">Statut</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ ind, c, first, span }) => (
              <tr key={ind.id + c.name} className={first ? "border-t border-line" : ""}>
                {first && (
                  <td rowSpan={span} className="px-4 py-2.5 align-top">
                    <div className="font-medium leading-snug">{ind.label}</div>
                    <div className="mt-0.5 text-xs muted">
                      {ind.pillar_label} · sens {ind.direction} · {ind.freq}
                    </div>
                    <div className="mt-0.5 text-[11px] muted">{(ind.sources || []).join(", ")}</div>
                    {ind.available && (
                      <div className="mt-1 text-xs">
                        Note de l'indicateur : <span className="num font-semibold" style={{ color: colorOf(ind.tension) }}>{fmt(ind.tension, 0)}</span>
                      </div>
                    )}
                  </td>
                )}
                <td className="px-3 py-2.5">{c.name}</td>
                <td className="num px-3 py-2.5 text-right font-medium">
                  {c.available ? <>{fmt(c.value, 2)} <span className="text-xs font-normal muted">{c.unit}</span></> : "—"}
                </td>
                <td className="px-3 py-2.5 text-xs muted">{c.available ? dateFr(c.date) : ""}</td>
                <td className="px-3 py-2.5">{c.available && <Spark data={c.spark} color={colorOf(c.tension)} />}</td>
                <td className="num px-3 py-2.5 text-right font-semibold" style={{ color: colorOf(c.tension) }}>{c.available ? fmt(c.tension, 0) : "—"}</td>
                <td className="px-3 py-2.5 text-xs">
                  {!c.available ? (
                    ind.id === "sentiment" ? <span className="muted">● en attente de la 1re revue</span> : <span className="text-red-500">● indisponible</span>
                  ) : c.fresh ? (
                    <span className="text-green-500">● à jour</span>
                  ) : (
                    <span className="text-amber-500">● en retard</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs muted">
        « En retard » signifie que la source n'a pas publié depuis plus longtemps que prévu pour sa fréquence ; la dernière valeur
        connue reste utilisée. Les données trimestrielles (PIB, crédit) sont naturellement publiées avec plusieurs semaines de délai.
      </p>
    </div>
  );
}
