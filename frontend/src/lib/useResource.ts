import { useCallback, useEffect, useState } from "react";

import { ApiError, toApiError } from "../api/client";

export type Resource<T> =
  | { state: "loading" }
  | { state: "error"; error: ApiError }
  | { state: "ready"; data: T };

/** Pide datos a la API al montar el componente y cancela la petición si se desmonta. */
export function useResource<T>(load: (signal: AbortSignal) => Promise<T>): [Resource<T>, () => void] {
  const [resource, setResource] = useState<Resource<T>>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setResource({ state: "loading" });
    load(controller.signal)
      .then((data) => setResource({ state: "ready", data }))
      .catch((cause: unknown) => {
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setResource({ state: "error", error: toApiError(cause) });
      });
    return () => controller.abort();
    // `load` se define en cada render; solo se vuelve a pedir al reintentar.
  }, [attempt]);

  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  return [resource, retry];
}
