import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Header } from "@/components/ui";
import { RegionProvider } from "@/lib/data";

export const metadata: Metadata = {
  title: "Baromètre 2026 · Santé financière mondiale",
  description:
    "Score de tension financière de 0 (euphorie) à 100 (stress), Monde et Europe / France, calculé à partir de 22 indicateurs actualisés automatiquement.",
};
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#090d16" };

// Applique le thème avant l'affichage pour éviter un flash (sombre par défaut)
const themeScript = `try{var t=localStorage.getItem('theme');if(t!=='light')document.documentElement.classList.add('dark')}catch(e){document.documentElement.classList.add('dark')}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
        <style dangerouslySetInnerHTML={{ __html: ":root{--font-inter:'Inter'}" }} />
      </head>
      <body className="min-h-screen font-sans antialiased">
        <RegionProvider>
          <Header />
          <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
          <footer className="mx-auto max-w-7xl px-4 pb-10 pt-4 text-xs muted">
            Projet pédagogique KEDGE BS, Gestion d'actifs 2025-2026. Sources : FRED, BCE, Eurostat, INSEE, OCDE, STOXX,
            Twelve Data, Yahoo Finance, multpl, Caldara et Iacoviello, Baker-Bloom-Davis (EPU), presse financière. Ne constitue pas un conseil en investissement.
          </footer>
        </RegionProvider>
      </body>
    </html>
  );
}
