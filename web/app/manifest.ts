import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Barolys · Santé financière mondiale",
    short_name: "Barolys",
    description: "Score de tension financière de 0 (euphorie) à 100 (stress), actualisé en continu.",
    start_url: "/",
    display: "standalone",
    background_color: "#090d16",
    theme_color: "#090d16",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
