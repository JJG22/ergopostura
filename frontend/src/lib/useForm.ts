import { useState } from "react";

import { toApiError, type ApiError } from "../api/client";

/**
 * Estado de un formulario que se envía a la API. La validación real la hace el servidor:
 * su error llega con los mensajes por campo y se muestra debajo de cada entrada.
 */
export function useForm<T extends object>(initial: T) {
  const [values, setValues] = useState<T>(initial);
  const [error, setError] = useState<ApiError | null>(null);
  const [sending, setSending] = useState(false);

  function set<K extends keyof T>(name: K, value: T[K]) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  /** Ejecuta la acción; devuelve su resultado o `undefined` si falló (el error queda en `error`). */
  async function submit<R>(action: (values: T) => Promise<R>): Promise<R | undefined> {
    setSending(true);
    setError(null);
    try {
      return await action(values);
    } catch (cause) {
      setError(toApiError(cause));
      return undefined;
    } finally {
      setSending(false);
    }
  }

  const fieldError = (name: keyof T & string) => error?.field(name);

  return { values, set, setValues, error, sending, submit, fieldError };
}
