import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router";

import { useAuth, useSession } from "../auth/AuthContext";
import { legacyUrl } from "../lib/format";
import { Notice, PageProvider, useCrumb } from "./Page";
import { Icon, Logo, LogoMark } from "./ui";

const itemClass = "relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-150";
// El elemento activo lleva una barra de cobalto a la izquierda: se distingue sin depender solo del color de fondo.
const ACTIVE = "bg-white/8 text-white before:absolute before:inset-y-1.5 before:-left-3 before:w-[3px] before:rounded-r before:bg-brand-400";
const IDLE = "text-ink-300 hover:bg-white/5 hover:text-white";

export function Layout() {
  return (
    <PageProvider>
      <Shell />
      <Notice />
    </PageProvider>
  );
}

function Shell() {
  const crumb = useCrumb();
  const session = useSession();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const { user } = session;

  async function handleLogout() {
    await logout();
    navigate("/ingresar", { replace: true });
  }

  return (
    <div className="min-h-screen bg-ink-50 text-ink-950 lg:flex print:bg-white">
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-64 flex-col bg-ink-950 text-ink-300 transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 print:hidden ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center px-5">
          <Logo tone="light" />
        </div>
        <nav aria-label="Navegación principal" className="flex-1 overflow-y-auto px-3 py-4">
          {session.navigation.map((item) =>
            item.to !== null ? (
              <NavLink
                key={item.label}
                to={item.to}
                end={item.to === "/"}
                onClick={() => setOpen(false)}
                className={({ isActive }) => `${itemClass} ${isActive ? ACTIVE : IDLE}`}
              >
                <Icon name={item.icon} />
                {item.label}
              </NavLink>
            ) : (
              // Módulo aún no migrado: se abre la pantalla actual, con la misma sesión.
              <a key={item.label} href={legacyUrl(item.href ?? "/")} className={`${itemClass} ${IDLE}`}>
                <Icon name={item.icon} />
                {item.label}
              </a>
            ),
          )}
        </nav>
        <div className="border-t border-white/8 p-3">
          <div className="mb-2 flex items-center gap-3 px-2 py-1.5">
            <span className="grid size-9 place-items-center rounded-md bg-brand-700 text-xs font-bold text-white">{user.initials}</span>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-white">{user.full_name}</p>
              <p className="truncate text-xs text-ink-400">{user.role_label}</p>
            </div>
          </div>
          <NavLink to="/cambiar-contrasena" className={({ isActive }) => `${itemClass} ${isActive ? ACTIVE : IDLE}`}>
            <Icon name="key-round" />Cambiar contraseña
          </NavLink>
          {session.admin_url ? (
            <a href={legacyUrl(session.admin_url)} className={`${itemClass} ${IDLE}`}>
              <Icon name="settings" />Panel técnico
            </a>
          ) : null}
          <button type="button" onClick={handleLogout} className={`${itemClass} w-full ${IDLE}`}>
            <Icon name="log-out" />Cerrar sesión
          </button>
        </div>
      </aside>
      {open ? <div className="fixed inset-0 z-20 bg-ink-950/40 lg:hidden" onClick={() => setOpen(false)} /> : null}

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-10 flex h-16 items-center gap-2 border-b border-ink-200 bg-white/85 px-4 backdrop-blur-md lg:px-10 print:hidden">
          <button type="button" className="-ml-1 rounded-md p-2 text-ink-700 hover:bg-ink-100 lg:hidden" aria-label="Abrir menú" onClick={() => setOpen(true)}>
            <Icon name="menu" />
          </button>
          <span className="lg:hidden"><LogoMark className="size-7" /></span>
          <nav aria-label="Ubicación" className="flex min-w-0 items-center gap-2 text-sm">
            <span className="hidden text-ink-500 sm:inline">{user.company?.name ?? "ErgoPostura"}</span>
            <Icon name="chevron-right" className="hidden size-4 text-ink-300 sm:block" />
            <span className="truncate font-semibold text-ink-950">{crumb}</span>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-6xl px-4 py-8 lg:px-10 lg:py-10 print:max-w-none print:p-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
