import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";

import type { NavItem } from "../api/types";
import { useAuth, useSession } from "../auth/AuthContext";
import { legacyUrl } from "../lib/format";
import { Notice, PageProvider, useCrumb } from "./Page";
import { Icon, Logo, LogoGlyph } from "./ui";

export function Layout() {
  return (
    <PageProvider>
      <Shell />
      <Notice />
    </PageProvider>
  );
}

/** Nombres cortos para la franja superior; el menú del teléfono muestra el nombre completo. */
const SHORT: Record<string, string> = {
  "Panel principal": "Inicio",
  "Tareas pendientes": "Tareas",
  "Accesos de empresas": "Accesos",
};

/**
 * Entrada del menú. En la franja azul, la sección activa se marca con una barra blanca bajo la
 * palabra; en el menú del teléfono, con la fila entera en azul.
 */
function NavEntry({ item, compact, onNavigate }: { item: NavItem; compact: boolean; onNavigate?: () => void }) {
  const label = compact ? (SHORT[item.label] ?? item.label) : item.label;
  const base = compact
    ? "relative flex h-16 items-center px-3 text-[15px] font-medium transition-colors after:absolute after:inset-x-3 after:bottom-0 after:h-1 after:transition-colors"
    : "flex items-center gap-3 px-4 py-3.5 text-base font-medium transition-colors";
  const idle = compact ? "text-white/80 hover:text-white after:bg-transparent" : "text-ink-800 hover:bg-ink-50";
  const active = compact ? "text-white after:bg-white" : "bg-brand-700 text-white";
  const content = (
    <>
      {compact ? null : <Icon name={item.icon} className="size-5 opacity-70" />}
      {label}
    </>
  );
  if (item.to === null) {
    // Módulo servido por el servidor: se abre con una navegación completa y la misma sesión.
    return <a href={legacyUrl(item.href ?? "/")} className={`${base} ${idle}`}>{content}</a>;
  }
  return (
    <NavLink to={item.to} end={item.to === "/"} onClick={onNavigate} className={({ isActive }) => `${base} ${isActive ? active : idle}`}>
      {content}
    </NavLink>
  );
}

/** Menú de la cuenta: se cierra con Escape, al hacer clic fuera o al elegir una opción. */
function AccountMenu({ onLogout }: { onLogout: () => void }) {
  const { user, admin_url } = useSession();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (event: MouseEvent) => { if (!ref.current?.contains(event.target as Node)) setOpen(false); };
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open]);

  const item = "flex w-full items-center gap-3 px-4 py-3 text-sm font-medium text-ink-800 transition-colors hover:bg-ink-50 hover:text-ink-950";
  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-haspopup="menu"
        className="flex h-16 items-center gap-3 pl-3 text-white">
        <span className="grid size-9 place-items-center bg-white text-xs font-bold text-brand-700">{user.initials}</span>
        <span className="hidden text-left leading-tight 2xl:block">
          <span className="block text-sm font-semibold">{user.first_name}</span>
          <span className="block text-xs text-white/70">{user.role_label}</span>
        </span>
        <Icon name="chevron-down" className={`size-4 text-white/80 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </button>
      {open ? (
        <div role="menu" className="absolute right-0 top-full z-40 w-72 border border-ink-950 bg-white shadow-float motion-safe:animate-[pop-in_160ms_cubic-bezier(0.2,0.9,0.3,1)]">
          <div className="border-b border-ink-200 px-4 py-4">
            <p className="font-semibold text-ink-950">{user.full_name}</p>
            <p className="truncate text-sm text-ink-500">{user.email}</p>
            <p className="mt-2 text-sm text-brand-700">{user.company ? `${user.role_label}, ${user.company.name}` : user.role_label}</p>
          </div>
          <NavLink role="menuitem" to="/cambiar-contrasena" onClick={() => setOpen(false)} className={item}><Icon name="key-round" />Cambiar contraseña</NavLink>
          {admin_url ? <a role="menuitem" href={legacyUrl(admin_url)} className={item}><Icon name="settings" />Panel técnico</a> : null}
          <button role="menuitem" type="button" onClick={onLogout} className={`${item} border-t border-ink-200`}><Icon name="log-out" />Cerrar sesión</button>
        </div>
      ) : null}
    </div>
  );
}

function Shell() {
  const crumb = useCrumb();
  const session = useSession();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sheet, setSheet] = useState(false);

  useEffect(() => setSheet(false), [location.pathname]);

  async function handleLogout() {
    await logout();
    navigate("/ingresar", { replace: true });
  }

  return (
    <div className="flex min-h-screen flex-col overflow-x-clip text-ink-950 print:bg-white">
      <a href="#contenido" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:bg-white focus:px-4 focus:py-2">Ir al contenido</a>
      <header className="sticky top-0 z-30 bg-brand-700 text-white print:hidden">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-6 px-4 sm:px-6 lg:px-8">
          <NavLink to="/" aria-label="Ir al inicio" className="shrink-0"><Logo tone="light" /></NavLink>
          <nav aria-label="Navegación principal" className="hidden items-stretch xl:flex">
            {session.navigation.map((item) => <NavEntry key={item.label} item={item} compact />)}
          </nav>
          <span className="ml-auto hidden min-w-0 truncate text-sm font-medium text-white/85 sm:block xl:hidden">{crumb}</span>
          <div className="ml-auto hidden xl:block"><AccountMenu onLogout={() => void handleLogout()} /></div>
          <button type="button" onClick={() => setSheet(true)} aria-label="Abrir menú" aria-expanded={sheet}
            className="ml-auto grid size-11 shrink-0 place-items-center text-white transition-colors hover:bg-white/10 sm:ml-0 xl:hidden">
            <Icon name="menu" />
          </button>
        </div>
      </header>

      {sheet ? (
        <div className="fixed inset-0 z-40 xl:hidden" role="dialog" aria-modal="true" aria-label="Menú">
          <div className="absolute inset-0 bg-ink-950/45 motion-safe:animate-[appear_200ms_ease-out_forwards] motion-safe:opacity-0" onClick={() => setSheet(false)} />
          <div className="absolute inset-y-0 right-0 flex w-full max-w-sm flex-col overflow-y-auto bg-white motion-safe:animate-[sheet-in_240ms_cubic-bezier(0.32,0.72,0,1)]">
            <div className="flex h-16 shrink-0 items-center justify-between bg-brand-700 px-4">
              <Logo tone="light" />
              <button type="button" onClick={() => setSheet(false)} aria-label="Cerrar menú" className="grid size-11 place-items-center text-white hover:bg-white/10">
                <Icon name="x" />
              </button>
            </div>
            <nav aria-label="Navegación principal" className="grid py-2">
              {session.navigation.map((item) => <NavEntry key={item.label} item={item} compact={false} onNavigate={() => setSheet(false)} />)}
            </nav>
            <div className="mt-auto border-t-2 border-ink-950">
              <div className="flex items-center gap-3 px-4 py-4">
                <span className="grid size-10 place-items-center bg-brand-700 text-sm font-bold text-white">{session.user.initials}</span>
                <div className="min-w-0">
                  <p className="truncate font-semibold">{session.user.full_name}</p>
                  <p className="truncate text-sm text-ink-500">{session.user.role_label}</p>
                </div>
              </div>
              <NavLink to="/cambiar-contrasena" className="flex items-center gap-3 px-4 py-3.5 font-medium text-ink-800 hover:bg-ink-50"><Icon name="key-round" />Cambiar contraseña</NavLink>
              {session.admin_url ? <a href={legacyUrl(session.admin_url)} className="flex items-center gap-3 px-4 py-3.5 font-medium text-ink-800 hover:bg-ink-50"><Icon name="settings" />Panel técnico</a> : null}
              <button type="button" onClick={() => void handleLogout()} className="flex w-full items-center gap-3 px-4 py-3.5 font-medium text-ink-800 hover:bg-ink-50"><Icon name="log-out" />Cerrar sesión</button>
            </div>
          </div>
        </div>
      ) : null}

      <main id="contenido" className="mx-auto w-full max-w-7xl flex-1 px-4 pb-20 pt-10 sm:px-6 sm:pt-14 lg:px-8 print:max-w-none print:p-0">
        <Outlet />
      </main>
      <footer className="border-t-2 border-ink-950 print:hidden">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-6 text-sm text-ink-600 sm:px-6 lg:px-8">
          <span className="flex items-center gap-2"><LogoGlyph className="size-5" />Evaluación ergonómica con el método RULA</span>
          <span className="hidden sm:inline">{session.user.company?.name ?? session.user.role_label}</span>
        </div>
      </footer>
    </div>
  );
}
