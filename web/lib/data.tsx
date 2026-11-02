"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import useSWR from "swr";

/** Adresse des données. En production : la branche `data` du dépôt GitHub, mise à jour par GitHub Actions. */
export const DATA_URL = (process.env.NEXT_PUBLIC_DATA_URL || "/data").replace(/\/$/, "");
/** Fréquence de rechargement automatique dans le navigateur. */
export const REFRESH_MS = 2 * 60 * 1000;

const fetcher = async (path: string) => {
  // anti-cache : une nouvelle URL par minute
  const bust = Math.floor(Date.now() / 60000);
  const r = await fetch(`${DATA_URL}/${path}?t=${bust}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path} : HTTP ${r.status}`);
  return r.json();
};

export function useData<T = any>(file: string) {
  return useSWR<T>(file, fetcher, {
    refreshInterval: REFRESH_MS,
    revalidateOnFocus: true,
    keepPreviousData: true,
  });
}

// ------------------------------------------------------------------ région (Monde / Europe-France)
export type Region = "world" | "europe";
const RegionCtx = createContext<{ region: Region; setRegion: (r: Region) => void }>({
  region: "world",
  setRegion: () => {},
});

export function RegionProvider({ children }: { children: ReactNode }) {
  const [region, setRegionState] = useState<Region>("world");
  useEffect(() => {
    try {
      const r = localStorage.getItem("region");
      if (r === "world" || r === "europe") setRegionState(r);
    } catch {}
  }, []);
  const setRegion = (r: Region) => {
    setRegionState(r);
    try {
      localStorage.setItem("region", r);
    } catch {}
  };
  return <RegionCtx.Provider value={{ region, setRegion }}>{children}</RegionCtx.Provider>;
}
export const useRegion = () => useContext(RegionCtx);

// ------------------------------------------------------------------ zones et couleurs
export const ZONES = [
  { max: 20, name: "Euphorie", color: "#3b82f6" },
  { max: 40, name: "Favorable", color: "#22c55e" },
  { max: 60, name: "Neutre", color: "#94a3b8" },
  { max: 80, name: "Prudence", color: "#f59e0b" },
  { max: 101, name: "Stress", color: "#ef4444" },
];
export const zoneOf = (s: number | null | undefined) =>
  s == null ? { name: "—", color: "#64748b", max: 0 } : ZONES.find((z) => s < z.max) || ZONES[4];
export const colorOf = (s: number | null | undefined) => zoneOf(s).color;

export const PILLAR_COLORS: Record<string, string> = {
  macro: "#a78bfa",
  bc: "#38bdf8",
  marches: "#34d399",
  risque: "#fb923c",
  flux: "#f472b6",
};

// ------------------------------------------------------------------ formats
export const fmt = (x: number | null | undefined, nd = 1) =>
  x == null || Number.isNaN(x) ? "—" : x.toLocaleString("fr-FR", { minimumFractionDigits: nd, maximumFractionDigits: nd });

export const signed = (x: number | null | undefined, nd = 1) =>
  x == null ? "—" : `${x > 0 ? "+" : x < 0 ? "−" : ""}${fmt(Math.abs(x), nd)}`;

export function ago(iso?: string) {
  if (!iso) return "—";
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (min < 1) return "à l'instant";
  if (min < 60) return `il y a ${min} min`;
  const h = Math.round(min / 60);
  if (h < 48) return `il y a ${h} h`;
  return `il y a ${Math.round(h / 24)} jours`;
}

export const dateFr = (iso?: string, withTime = false) =>
  iso
    ? new Date(iso).toLocaleString("fr-FR", {
        day: "numeric",
        month: "short",
        year: withTime ? undefined : "numeric",
        ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
        timeZone: "Europe/Paris",
      })
    : "—";
