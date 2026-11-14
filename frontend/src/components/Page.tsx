import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

/**
 * Lo que el diseño general necesita saber de la pantalla abierta: la miga de pan del
 * encabezado y los avisos breves ("Empresa registrada") que confirman una acción.
 */
interface PageValue {
  crumb: string;
  setCrumb: (crumb: string) => void;
  notice: string | null;
  notify: (text: string) => void;
}

const PageContext = createContext<PageValue | null>(null);

export function PageProvider({ children }: { children: ReactNode }) {
  const [crumb, setCrumb] = useState("Panel principal");
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 4000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const notify = useCallback((text: string) => setNotice(text), []);
  return <PageContext.Provider value={{ crumb, setCrumb, notice, notify }}>{children}</PageContext.Provider>;
}

function usePage(): PageValue {
  const value = useContext(PageContext);
  if (!value) throw new Error("usePage debe usarse dentro de PageProvider");
  return value;
}

/** Título de la pestaña y miga de pan de la pantalla. */
export function usePageTitle(title: string) {
  const { setCrumb } = usePage();
  useEffect(() => {
    setCrumb(title);
    document.title = `${title} · ErgoPostura`;
  }, [title, setCrumb]);
}

export function useNotify() {
  return usePage().notify;
}

export function useCrumb() {
  return usePage().crumb;
}

export function Notice() {
  const { notice } = usePage();
  return (
    <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex justify-center px-4">
      {notice ? (
        <div className="rounded-lg bg-slate-900 px-4 py-3 text-sm font-medium text-white shadow-lg">{notice}</div>
      ) : null}
    </div>
  );
}
