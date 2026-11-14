import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { onApiError, toApiError, type ApiError } from "../api/client";
import { authApi, type LoginInput, type PasswordInput } from "../api/endpoints";
import type { Session } from "../api/types";

type AuthState =
  | { status: "loading" }
  | { status: "anonymous"; reason?: ApiError }
  | { status: "authenticated"; session: Session };

interface AuthValue {
  state: AuthState;
  login: (input: LoginInput) => Promise<Session>;
  logout: () => Promise<void>;
  changePassword: (input: PasswordInput) => Promise<Session>;
  can: (capability: string) => boolean;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    authApi
      .session(controller.signal)
      .then((session) => setState({ status: "authenticated", session }))
      .catch((cause: unknown) => {
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        const error = toApiError(cause);
        setState(error.code === "not_authenticated" ? { status: "anonymous" } : { status: "anonymous", reason: error });
      });
    return () => controller.abort();
  }, []);

  // Si cualquier petición descubre que la sesión venció, la interfaz vuelve al login.
  useEffect(
    () =>
      onApiError((error) => {
        if (error.code === "not_authenticated") setState({ status: "anonymous", reason: error });
        if (error.code === "password_change_required") {
          setState((current) =>
            current.status === "authenticated"
              ? { status: "authenticated", session: { ...current.session, user: { ...current.session.user, must_change_password: true } } }
              : current,
          );
        }
      }),
    [],
  );

  const login = useCallback(async (input: LoginInput) => {
    const session = await authApi.login(input);
    setState({ status: "authenticated", session });
    return session;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setState({ status: "anonymous" });
    }
  }, []);

  const changePassword = useCallback(async (input: PasswordInput) => {
    const session = await authApi.changePassword(input);
    setState({ status: "authenticated", session });
    return session;
  }, []);

  const value = useMemo<AuthValue>(
    () => ({
      state,
      login,
      logout,
      changePassword,
      can: (capability) => state.status === "authenticated" && state.session.capabilities.includes(capability),
    }),
    [state, login, logout, changePassword],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth debe usarse dentro de <AuthProvider>.");
  return value;
}

/** Sesión garantizada: solo se usa dentro de rutas protegidas. */
export function useSession(): Session {
  const { state } = useAuth();
  if (state.status !== "authenticated") throw new Error("No hay sesión activa.");
  return state.session;
}
