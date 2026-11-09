"use client";

import { useEffect, useRef, useState } from "react";
import { Loading, PageTitle, Spark } from "@/components/ui";
import { colorOf, dateFr, fmt, useData, useRegion } from "@/lib/data";

export default function Donnees() {
  const { region } = useRegion();
  const { data: inds, error } = useData("indicators.json");
  const { data: meta } = useData("meta.json");
  const [pillar, setPillar] = useState("all");
  const [picked, setPicked] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const menuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    const hide = (e?: Event) => {
      if (e && menuRef.current && e.target instanceof Node && menuRef.current.contains(e.target)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    window.addEventListener("resize", hide);
    window.addEventListener("scroll", hide, true);
    return () => {
      window.removeEventListener("scroll", hide, true);
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
      window.removeEventListener("resize", hide);
    };
  }, [open]);
  if (!inds) return <Loading error={error} />;
  const all: any[] = inds[region];
  const sel = picked.filter((id) => all.some((i) => i.id === id));   // la zone peut ne pas avoir l'indicateur
  const list: any[] = sel.length
    ? all.filter((i) => sel.includes(i.id))
    : all.filter((i: any) => pillar === "all" || i.pillar === pillar);
  const toggle = (id: string) =>
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : p.length >= 5 ? p : [...p, id]));
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
        <button onClick={() => { setPillar("all"); setPicked([]); }} className={`rounded-full border px-3 py-1 ${pillar === "all" && !sel.length ? "border-accent bg-accent/10" : "border-line muted"}`}>Tous</button>
        {pillars.map(([id, label]) => (
          <button key={id} onClick={() => { setPillar(id); setPicked([]); }} className={`rounded-full border px-3 py-1 ${pillar === id && !sel.length ? "border-accent bg-accent/10" : "border-line muted"}`}>{label}</button>
        ))}
        {sel.length > 0 && (
          <span className="flex items-center gap-2 rounded-full border border-accent bg-accent/10 px-3 py-1">
            {sel.length} indicateur{sel.length > 1 ? "s" : ""} choisi{sel.length > 1 ? "s" : ""}
            <button onClick={() => setPicked([])} className="text-xs text-accent" aria-label="Effacer la sélection">✕</button>
          </span>
        )}
        <span className="ml-auto text-xs muted">
          {meta && series.length > 0 && `${ok} séries sur ${series.length} à jour · collecte complète ${dateFr(meta.last_full, true)} · marchés ${dateFr(meta.last_markets, true)}`}
        </span>
      </div>

      <div className="card overflow-x-auto p-0 sm:p-0">
        <table className="w-full min-w-[860px] text-sm">
          <thead className="bg-surface text-left text-xs muted">
            <tr>
              <th className="relative px-4 py-3 font-medium">
                <div ref={menuRef} className="inline-block">
                  <button onClick={(e) => {
                    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
                    setPos({ top: r.bottom + 4, left: Math.max(8, Math.min(r.left, window.innerWidth - 328)) });
                    setOpen((o) => !o);
                  }} aria-expanded={open} className="flex items-center gap-1 rounded px-1 -mx-1 hover:text-ink">
                    Indicateur
                    <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden className={`transition ${open ? "rotate-180" : ""}`}><path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
                  </button>
                  {open && (
                    <div style={{ position: "fixed", top: pos.top, left: pos.left, maxHeight: `min(420px, calc(100vh - ${pos.top + 12}px))` }} className="z-40 w-80 overflow-y-auto rounded-lg border border-line bg-surface-raised p-2 text-left text-sm font-normal text-ink shadow-xl">
                      <div className="mb-1 flex items-center justify-between px-1 text-xs muted">
                        <span>Choisissez jusqu'à 5 indicateurs ({sel.length}/5)</span>
                        {sel.length > 0 && <button onClick={() => setPicked([])} className="text-accent">Tout afficher</button>}
                      </div>
                      {pillars.map(([pid, plabel]) => (
                        <div key={pid} className="mt-1">
                          <div className="px-1 py-1 text-[11px] font-semibold uppercase tracking-wide muted">{plabel}</div>
                          {all.filter((i) => i.pillar === pid).map((i) => {
                            const on = sel.includes(i.id);
                            const full = !on && sel.length >= 5;
                            return (
                              <label key={i.id} className={`flex cursor-pointer items-start gap-2 rounded px-1 py-1 ${full ? "opacity-40" : "hover:bg-surface"}`}>
                                <input type="checkbox" checked={on} disabled={full} onChange={() => toggle(i.id)} className="mt-0.5 accent-[rgb(var(--accent))]" />
                                <span className="leading-snug">{i.label}</span>
                              </label>
                            );
                          })}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </th>
              <th className="px-3 py-3 font-medium">Composante</th>
              <th className="px-3 py-3 text-right font-medium">Valeur</th>
              <th className="px-3 py-3 font-medium">Date</th>
              <th className="px-3 py-3 font-medium">1 an</th>
              <th className="px-3 py-3 text-right font-medium">Tension</th>
              <th className="px-3 py-3 font-medium">Statut</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-sm muted">Aucun indicateur sélectionné pour cette zone.</td></tr>
            )}
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
