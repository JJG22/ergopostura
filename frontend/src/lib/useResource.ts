import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, toApiError } from "../api/client";

export type Resource<T> =
  | { state: "loading" }
  | { state: "error"; error: ApiError }
  | { state: "ready"; data: T };

/**
 * Pide datos a la API al montar el componente y cada vez que cambian `deps`; cancela la
 * petición anterior si llega otra. Devuelve [recurso, reintentar, recargar]:
 * - reintentar muestra la carga de nuevo (para después de un error);
 * - recargar actualiza sin borrar lo que ya se ve (para después de guardar un cambio).
 */
export function useResource<T>(
  load: (signal: AbortSignal) => Promise<T>,
  deps: readonly unknown[] = [],
): [Resource<T>, () => void, () => void] {
  const [resource, setResource] = useState<Resource<T>>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  const silent = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    if (!silent.current) setResource({ state: "loading" });
    silent.current = false;
    load(controller.signal)
      .then((data) => setResource({ state: "ready", data }))
      .catch((cause: unknown) => {
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setResource({ state: "error", error: toApiError(cause) });
      });
    return () => controller.abort();
    // `load` se define en cada render; se vuelve a pedir solo al cambiar `deps` o al reintentar.
  }, [attempt, ...deps]);

  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  const refresh = useCallback(() => {
    silent.current = true;
    setAttempt((value) => value + 1);
  }, []);
  return [resource, retry, refresh];
}
