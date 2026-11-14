import type { ReactNode } from "react";
import { Link } from "react-router";

import { legacyUrl } from "../lib/format";

/**
 * Direcciones con la forma de las antiguas pantallas de Django («/empresas/3/») y su ruta en
 * React. Así un enlace guardado o escrito con la forma vieja sigue abriendo la pantalla correcta.
 */
const ROUTES: readonly [RegExp, (match: RegExpMatchArray) => string][] = [
  [/^\/$/, () => "/"],
  [/^\/empresas\/$/, () => "/empresas"],
  [/^\/empresas\/(\d+)\/$/, (m) => `/empresas/${m[1] ?? ""}`],
  [/^\/usuarios\/$/, () => "/usuarios"],
  [/^\/usuarios\/nuevo\/$/, () => "/usuarios?crear=1"],
  [/^\/contratos\/$/, () => "/contratos"],
  [/^\/contratos\/nuevo\/$/, () => "/contratos/nuevo"],
  [/^\/contratos\/(\d+)\/$/, (m) => `/contratos/${m[1] ?? ""}`],
  [/^\/visitas\/$/, () => "/visitas"],
  [/^\/visitas\/agenda\/$/, () => "/visitas/agenda"],
  [/^\/visitas\/(\d+)\/$/, (m) => `/visitas/${m[1] ?? ""}`],
  [/^\/evaluaciones\/$/, () => "/evaluaciones"],
  [/^\/indicadores\/$/, () => "/indicadores"],
  [/^\/tareas\/$/, () => "/tareas"],
  [/^\/evaluaciones\/nueva\/$/, () => "/evaluaciones"],
  [/^\/evaluaciones\/(\d+)\/$/, (m) => `/evaluaciones/${m[1] ?? ""}`],
  [/^\/evaluaciones\/(\d+)\/informe\/$/, (m) => `/evaluaciones/${m[1] ?? ""}/informe`],
];

/** Ruta de React para una dirección con la forma antigua, o null si no corresponde a ninguna. */
export function appRoute(href: string): string | null {
  const [path = "", query] = href.split("?");
  for (const [pattern, build] of ROUTES) {
    const match = path.match(pattern);
    if (match) {
      const route = build(match);
      if (!query) return route;
      return route.includes("?") ? `${route}&${query}` : `${route}?${query}`;
    }
  }
  return null;
}

export function AppLink({ href, className, children, title }: { href: string; className?: string; children: ReactNode; title?: string }) {
  // El panel técnico (/admin/) es la única página que sirve el servidor.
  if (href.startsWith("/admin/")) return <a href={legacyUrl(href)} className={className} title={title}>{children}</a>;
  return <Link to={appRoute(href) ?? href} className={className} title={title}>{children}</Link>;
}
