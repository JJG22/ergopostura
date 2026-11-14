import { Component, type ErrorInfo, type ReactNode } from "react";
import { isRouteErrorResponse, Link, useRouteError } from "react-router";

function Crash({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="grid min-h-screen place-items-center bg-slate-50 p-6">
      <div className="max-w-md rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <h1 className="mb-2 text-xl font-bold">{title}</h1>
        <p className="mb-6 text-sm text-slate-500">{detail}</p>
        <a href="/app/" className="font-semibold text-teal-700 hover:underline">Volver al panel principal</a>
      </div>
    </div>
  );
}

/** Error al dibujar una ruta: se muestra un mensaje en vez de dejar la pantalla en blanco. */
export function RouteError() {
  const error = useRouteError();
  if (isRouteErrorResponse(error) && error.status === 404) {
    return <Crash title="Página no encontrada" detail="La dirección no existe o cambió." />;
  }
  if (import.meta.env.DEV) console.error(error);
  return <Crash title="Algo salió mal" detail="La pantalla tuvo un error inesperado. Recarga la página o vuelve al inicio." />;
}

export function NotFound() {
  return (
    <div className="grid min-h-screen place-items-center bg-slate-50 p-6 text-center">
      <div>
        <p className="text-sm font-semibold text-teal-700">404</p>
        <h1 className="mb-2 text-2xl font-bold">Página no encontrada</h1>
        <Link to="/" className="font-semibold text-teal-700 hover:underline">Volver al panel principal</Link>
      </div>
    </div>
  );
}

/** Último recurso: atrapa errores fuera del enrutador (por ejemplo, en el proveedor de sesión). */
export class AppErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  override state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    if (import.meta.env.DEV) console.error(error, info.componentStack);
  }

  override render() {
    if (this.state.failed) return <Crash title="Algo salió mal" detail="Recarga la página. Si el problema sigue, avisa a soporte técnico." />;
    return this.props.children;
  }
}
