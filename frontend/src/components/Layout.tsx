import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router";

import { useAuth, useSession } from "../auth/AuthContext";
import { legacyUrl } from "../lib/format";
import { Notice, PageProvider, useCrumb } from "./Page";
import { Icon } from "./ui";

const itemClass = "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition";

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
    <div className="min-h-screen bg-slate-50 text-slate-900 lg:flex">
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center gap-2.5 border-b border-slate-200 px-5 font-bold">
          <span className="grid size-8 place-items-center rounded-lg bg-teal-700 text-white"><Icon name="activity" /></span>
          ErgoPostura
        </div>
        <nav aria-label="Navegación principal" className="flex-1 overflow-y-auto p-3">
          <p className="px-3 pb-2 pt-1 text-[11px] font-bold tracking-wider text-slate-400">ESPACIO DE TRABAJO</p>
          {session.navigation.map((item) =>
            item.to !== null ? (
              <NavLink
                key={item.label}
                to={item.to}
                end={item.to === "/"}
                onClick={() => setOpen(false)}
                className={({ isActive }) => `${itemClass} ${isActive ? "bg-teal-100 font-semibold text-teal-800" : "text-slate-600 hover:bg-slate-100"}`}
              >
                <Icon name={item.icon} />
                {item.label}
              </NavLink>
            ) : (
              // Módulo aún no migrado: se abre la pantalla actual, con la misma sesión.
              <a key={item.label} href={legacyUrl(item.href ?? "/")} className={`${itemClass} text-slate-600 hover:bg-slate-100`}>
                <Icon name={item.icon} />
                {item.label}
              </a>
            ),
          )}
        </nav>
        <div className="border-t border-slate-200 p-3">
          <div className="mb-2 flex items-center gap-3 px-2">
            <span className="grid size-9 place-items-center rounded-full bg-teal-100 text-xs font-bold text-teal-800">{user.initials}</span>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{user.full_name}</p>
              <p className="truncate text-xs text-slate-500">{user.role_label}</p>
            </div>
          </div>
          <NavLink to="/cambiar-contrasena" className={`${itemClass} text-slate-600 hover:bg-slate-100`}>
            <Icon name="key-round" />Cambiar contraseña
          </NavLink>
          {session.admin_url ? (
            <a href={legacyUrl(session.admin_url)} className={`${itemClass} text-slate-600 hover:bg-slate-100`}>
              <Icon name="settings" />Panel técnico
            </a>
          ) : null}
          <button type="button" onClick={handleLogout} className={`${itemClass} w-full text-slate-600 hover:bg-slate-100`}>
            <Icon name="log-out" />Cerrar sesión
          </button>
        </div>
      </aside>
      {open ? <div className="fixed inset-0 z-20 bg-slate-900/30 lg:hidden" onClick={() => setOpen(false)} /> : null}

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-10 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur lg:px-8">
          <button type="button" className="rounded-lg p-2 hover:bg-slate-100 lg:hidden" aria-label="Abrir menú" onClick={() => setOpen(true)}>
            <Icon name="menu" />
          </button>
          <span className="text-sm text-slate-500">ErgoPostura</span>
          <Icon name="chevron-right" className="size-4 text-slate-400" />
          <span className="truncate text-sm font-semibold">{crumb}</span>
        </header>
        <main className="mx-auto w-full max-w-6xl px-4 py-8 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
