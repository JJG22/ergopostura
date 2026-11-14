import type { ReactNode } from "react";
import { Link } from "react-router";

import { legacyUrl } from "../lib/format";

/**
 * Rutas de Django que ya tienen pantalla en React. Un enlace a una de ellas se abre dentro de
 * la aplicación; uno a un módulo aún no migrado abre la pantalla actual con la misma sesión.
 * Al migrar un módulo se agrega aquí su ruta (y en apps/api/presenters.py, MIGRATED).
 */
const ROUTES: readonly [RegExp, (match: RegExpMatchArray) => string][] = [
  [/^\/$/, () => "/"],
  [/^\/empresas\/$/, () => "/empresas"],
  [/^\/empresas\/(\d+)\/$/, (m) => `/empresas/${m[1] ?? ""}`],
  [/^\/usuarios\/$/, () => "/usuarios"],
  [/^\/usuarios\/nuevo\/$/, () => "/usuarios?crear=1"],
];

/** Ruta de React para una dirección de Django, o null si ese módulo aún no está migrado. */
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
  const route = appRoute(href);
  if (route !== null) return <Link to={route} className={className} title={title}>{children}</Link>;
  return <a href={legacyUrl(href)} className={className} title={title}>{children}</a>;
}
