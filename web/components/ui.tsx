"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ago, colorOf, dateFr, fmt, REGION_LABELS, REGIONS, signed, useData, useRegion, zoneOf, ZONES } from "@/lib/data";

// ------------------------------------------------------------------ navigation
const NAV = [
  { href: "/", label: "Tableau de bord" },
  { href: "/piliers/", label: "Piliers" },
  { href: "/donnees/", label: "Données" },
  { href: "/historique/", label: "Historique" },
  { href: "/news/", label: "News" },
  { href: "/conseils/", label: "Conseils" },
  { href: "/methodologie/", label: "Méthodologie" },
];

export function Header() {
  const path = usePathname();
  const { region, setRegion } = useRegion();
  const { data: scores, error } = useData("scores.json");
  const [dark, setDark] = useState(true);
  const [, tick] = useState(0);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
    const t = setInterval(() => tick((x) => x + 1), 30000); // rafraîchit « il y a x min »
    return () => clearInterval(t);
  }, []);
  const toggleTheme = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {}
  };

  const updated = scores?.updated_at;
  const minutes = updated ? (Date.now() - new Date(updated).getTime()) / 60000 : Infinity;
  const fresh = minutes < 45 ? "#22c55e" : minutes < 180 ? "#f59e0b" : "#ef4444";

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden>
            <path d="M3 18a9 9 0 0 1 18 0" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
            <path d="M12 18l4.5-6" stroke="#3b82f6" strokeWidth="2.2" strokeLinecap="round" />
          </svg>
          Baromètre 2026
        </Link>
        <div className="order-3 flex w-full gap-0.5 overflow-x-auto rounded-full border border-line p-0.5 text-sm lg:order-none lg:ml-6 lg:w-auto">
          {REGIONS.map((r) => (
            <button
              key={r}
              onClick={() => setRegion(r)}
              className={`shrink-0 grow whitespace-nowrap rounded-full px-3 py-1.5 transition lg:grow-0 ${
                region === r ? "bg-accent/15 font-semibold text-ink ring-1 ring-accent" : "muted hover:text-ink"
              }`}
            >
              {REGION_LABELS[r]}
            </button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1.5 muted" title={updated ? dateFr(updated, true) : ""}>
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60" style={{ background: fresh }} />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full" style={{ background: fresh }} />
            </span>
            {error && !scores ? "Données indisponibles" : `Mis à jour ${ago(updated)}`}
          </span>
          <button onClick={toggleTheme} className="rounded-md border border-line px-2 py-1 muted hover:text-ink" aria-label="Changer de thème">
            {dark ? "Clair" : "Sombre"}
          </button>
        </div>
      </div>
      <nav className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-4 pb-2 text-sm">
        {NAV.map((n) => {
          const active = n.href === "/" ? path === "/" : path?.startsWith(n.href);
          return (
            <Link
              key={n.href}
              href={n.href}
              className={`whitespace-nowrap rounded-md px-3 py-1.5 transition ${
                active ? "bg-surface-raised font-medium text-ink ring-1 ring-line" : "muted hover:text-ink"
              }`}
            >
              {n.label}
            </Link>
          );
        })}
      </nav>
      {scores?.demo && (
        <div className="bg-amber-500/15 px-4 py-1.5 text-center text-xs text-amber-600 dark:text-amber-300">
          Données de démonstration (synthétiques) : la collecte automatique réelle n'a pas encore tourné.
        </div>
      )}
    </header>
  );
}

// ------------------------------------------------------------------ jauge demi-cercle
const pt = (cx: number, cy: number, r: number, t: number) => ({
  x: cx - r * Math.cos(t * Math.PI),
  y: cy - r * Math.sin(t * Math.PI),
});
const arc = (cx: number, cy: number, r: number, a: number, b: number) => {
  const p = pt(cx, cy, r, a);
  const q = pt(cx, cy, r, b);
  return `M${p.x} ${p.y}A${r} ${r} 0 0 1 ${q.x} ${q.y}`;
};

export function Gauge({ value, size = 220 }: { value: number | null; size?: number }) {
  const [shown, setShown] = useState(value ?? 50);
  useEffect(() => {
    if (value == null) return;
    let raf = 0;
    const start = shown;
    const t0 = performance.now();
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / 900);
      setShown(start + (value - start) * (1 - Math.pow(1 - k, 3)));
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);
  const cx = 110, cy = 110, r = 88;
  const p = pt(cx, cy, r, Math.max(0, Math.min(100, shown)) / 100);
  return (
    <svg viewBox="0 0 220 132" width={size} height={(size * 132) / 220} role="img" aria-label={`Score ${fmt(value, 0)} sur 100`}>
      {ZONES.map((z, i) => (
        <path key={z.name} d={arc(cx, cy, r, i * 0.2 + 0.008, (i + 1) * 0.2 - 0.008)} stroke={z.color} strokeWidth="16" fill="none" opacity={0.9} />
      ))}
      <line x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="rgb(var(--ink))" strokeWidth="3" strokeLinecap="round" />
      <circle cx={cx} cy={cy} r="6" fill="rgb(var(--ink))" />
      <circle cx={p.x} cy={p.y} r="7" fill="rgb(var(--surface-raised))" stroke="rgb(var(--ink))" strokeWidth="3" />
      <text x="16" y="130" fontSize="10" fill="rgb(var(--ink-soft))">0 · euphorie</text>
      <text x="204" y="130" fontSize="10" textAnchor="end" fill="rgb(var(--ink-soft))">stress · 100</text>
    </svg>
  );
}

// ------------------------------------------------------------------ petits éléments
export function ZoneBadge({ score, big = false }: { score: number | null; big?: boolean }) {
  const z = zoneOf(score);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${big ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs"}`}
      style={{ background: `${z.color}22`, color: z.color }}
    >
      <span className="h-2 w-2 rounded-full" style={{ background: z.color }} />
      {z.name}
    </span>
  );
}

export function Delta({ now, before, label }: { now?: number | null; before?: number | null; label: string }) {
  if (now == null || before == null) return <span className="muted text-xs">{label} : —</span>;
  const d = now - before;
  // hausse du score = plus de tension -> rouge
  const c = Math.abs(d) < 0.5 ? "rgb(var(--ink-soft))" : d > 0 ? "#ef4444" : "#22c55e";
  return (
    <span className="text-xs num" style={{ color: c }}>
      {signed(d)} pt <span className="muted">{label}</span>
    </span>
  );
}

/** Valeur qui clignote brièvement quand elle change (mise à jour en direct). */
export function Live({ value, children }: { value: unknown; children: ReactNode }) {
  const prev = useRef(value);
  const [k, setK] = useState(0);
  useEffect(() => {
    if (prev.current !== value) {
      prev.current = value;
      setK((x) => x + 1);
    }
  }, [value]);
  return (
    <span key={k} className={k ? "flash rounded" : ""}>
      {children}
    </span>
  );
}

export function Spark({ data, color = "rgb(var(--accent))", w = 110, h = 28 }: { data: [string, number][]; color?: string; w?: number; h?: number }) {
  const vals = (data || []).map((d) => d[1]).filter((v) => v != null);
  if (vals.length < 2) return <span className="muted text-xs">—</span>;
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const pts = vals.map((v, i) => `${(i / (vals.length - 1)) * w},${h - 2 - ((v - lo) / (hi - lo || 1)) * (h - 4)}`);
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden>
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth="1.5" />
    </svg>
  );
}

export function Bar({ value, color }: { value: number | null; color?: string }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-line/60">
      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${value ?? 0}%`, background: color || colorOf(value) }} />
    </div>
  );
}

export function Disclaimer({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`rounded-xl border border-amber-500/40 bg-amber-500/10 ${compact ? "p-3 text-xs" : "p-4 text-sm"}`}>
      <strong className="text-amber-600 dark:text-amber-300">Avertissement.</strong>{" "}
      Ces pistes sont des suppositions déduites d'un modèle pédagogique. Elles ne constituent ni une preuve, ni un conseil
      en investissement personnalisé au sens de la directive MIF. Les performances passées ne préjugent pas des performances futures.
    </div>
  );
}

export function PageTitle({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="mb-5">
      <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">{title}</h1>
      {children && <p className="mt-1 max-w-3xl text-sm muted">{children}</p>}
    </div>
  );
}

export function Loading({ error }: { error?: any }) {
  return (
    <div className="card text-sm muted">
      {error ? `Impossible de charger les données (${String(error.message || error)}). Nouvel essai automatique dans 2 minutes.` : "Chargement des données…"}
    </div>
  );
}
