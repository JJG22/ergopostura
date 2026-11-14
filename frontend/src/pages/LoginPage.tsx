import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router";

import { toApiError, type ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Field, FormError, FullPageSpinner, Icon } from "../components/ui";

/** Solo se aceptan destinos internos, para que nadie use el login como redirección a otro sitio. */
function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/";
}

export function LoginPage() {
  const { state, login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [sending, setSending] = useState(false);
  const next = safeNext(params.get("next"));

  if (state.status === "loading") return <FullPageSpinner />;
  if (state.status === "authenticated") return <Navigate to={next} replace />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSending(true);
    setError(null);
    try {
      const session = await login({ email, password, remember });
      navigate(session.user.must_change_password ? "/cambiar-contrasena" : next, { replace: true });
    } catch (cause) {
      setError(toApiError(cause));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-2">
      <section className="hidden flex-col justify-between bg-gradient-to-br from-teal-700 to-teal-900 p-12 text-white lg:flex">
        <div className="flex items-center gap-2.5 text-lg font-bold">
          <span className="grid size-9 place-items-center rounded-lg bg-white/15"><Icon name="activity" /></span>ErgoPostura
        </div>
        <div>
          <h1 className="mb-3 text-4xl font-bold leading-tight">Evaluaciones ergonómicas, más claras.</h1>
          <p className="max-w-md text-teal-50/80">Registra, analiza y comunica los riesgos posturales de cada puesto de trabajo.</p>
        </div>
      </section>
      <section className="flex items-center justify-center p-6">
        <form onSubmit={handleSubmit} noValidate className="w-full max-w-sm">
          <h1 className="mb-1 text-2xl font-bold">Te damos la bienvenida</h1>
          <p className="mb-6 text-sm text-slate-500">Ingresa tus datos para acceder a tu espacio de trabajo.</p>
          {/* Los errores de un campo van debajo de él; los demás, arriba del formulario. */}
          {error && !error.field("username") && !error.field("password") ? <FormError error={error} /> : null}
          <Field id="email" label="Correo electrónico" type="email" autoComplete="email" autoFocus placeholder="nombre@empresa.com"
            value={email} onChange={(e) => setEmail(e.target.value)} error={error?.field("username")} />
          <Field id="password" label="Contraseña" type="password" autoComplete="current-password"
            value={password} onChange={(e) => setPassword(e.target.value)} error={error?.field("password")} />
          <label className="mb-5 flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" className="size-4 accent-teal-700" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
            Recordarme
          </label>
          <Button type="submit" className="w-full" disabled={sending}>{sending ? "Ingresando…" : "Ingresar"}</Button>
          <p className="mt-4 text-xs text-slate-500">
            Acceso exclusivo para usuarios autorizados. Si olvidaste tu contraseña, pide una temporal a quien te dio el acceso.
          </p>
        </form>
      </section>
    </div>
  );
}
