import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router";

import { toApiError, type ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import handlingTraining from "../assets/capacitacion-cargas.jpg";
import { Button, Field, FormError, FullPageSpinner, Icon, Logo } from "../components/ui";
import { legacyUrl } from "../lib/format";

/** Solo se aceptan destinos internos, para que nadie use el login como redirección a otro sitio. */
function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/";
}

/** El panel técnico (/admin/) lo sirve el servidor: se abre con una navegación completa. */
const isServerPage = (path: string) => path.startsWith("/admin/");

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
  if (state.status === "authenticated") {
    if (isServerPage(next)) {
      window.location.replace(legacyUrl(next));
      return <FullPageSpinner />;
    }
    return <Navigate to={next} replace />;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSending(true);
    setError(null);
    try {
      const session = await login({ email, password, remember });
      if (!session.user.must_change_password && isServerPage(next)) window.location.replace(legacyUrl(next));
      else navigate(session.user.must_change_password ? "/cambiar-contrasena" : next, { replace: true });
    } catch (cause) {
      setError(toApiError(cause));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-[1fr_minmax(440px,0.8fr)]">
      {/* El cartel: la foto en blanco y negro impresa sobre el campo azul, con el nombre del servicio. */}
      <section className="print-blue relative hidden overflow-hidden lg:block" aria-hidden="true">
        <img src={handlingTraining} alt="" className="absolute inset-0 size-full object-cover object-[30%_60%]" />
        <div className="relative flex h-full flex-col justify-between p-12 text-white">
          <Logo tone="light" />
          <p className="max-w-xl font-display text-6xl leading-[0.98] xl:text-7xl">Evaluación ergonómica para empresas</p>
        </div>
      </section>
      <section className="print-blue relative overflow-hidden lg:hidden" aria-hidden="true">
        <img src={handlingTraining} alt="" className="absolute inset-0 size-full object-cover object-[30%_60%]" />
        <div className="relative flex min-h-56 flex-col justify-between gap-8 p-6 text-white">
          <Logo tone="light" />
          <p className="max-w-xs font-display text-[2.4rem] leading-[0.98]">Evaluación ergonómica para empresas</p>
        </div>
      </section>
      <section className="flex flex-col px-6 py-8 sm:px-12">
        <div className="flex items-center justify-between">
          <a href="/" className="ml-auto inline-flex items-center gap-2 text-sm font-medium text-ink-700 underline decoration-ink-300 underline-offset-4 hover:decoration-ink-950">
            <Icon name="arrow-left" className="size-4" />Volver a la portada
          </a>
        </div>
        <div className="flex flex-1 items-center py-12">
          <form onSubmit={handleSubmit} noValidate className="w-full max-w-sm">
            <h1 className="font-display text-5xl leading-none">Ingresar</h1>
            <p className="mb-10 mt-4 text-[15px] text-ink-600">Usa el correo y la contraseña de tu cuenta de ErgoPostura.</p>
            {/* Los errores de un campo van debajo de él; los demás, arriba del formulario. */}
            {error && !error.field("username") && !error.field("password") ? <FormError error={error} /> : null}
            <Field id="email" label="Correo electrónico" type="email" autoComplete="email" autoFocus placeholder="nombre@empresa.com"
              value={email} onChange={(e) => setEmail(e.target.value)} error={error?.field("username")} />
            <Field id="password" label="Contraseña" type="password" autoComplete="current-password"
              value={password} onChange={(e) => setPassword(e.target.value)} error={error?.field("password")} />
            <label className="mb-8 flex items-center gap-2.5 text-sm text-ink-700">
              <input type="checkbox" className="size-4 accent-brand-700" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
              Mantener la sesión iniciada
            </label>
            <Button type="submit" className="h-12 w-full text-[15px]" disabled={sending}>{sending ? "Ingresando…" : "Ingresar"}</Button>
            <p className="mt-8 border-t border-ink-200 pt-6 text-sm leading-relaxed text-ink-600">
              Acceso solo para usuarios autorizados. Si olvidaste tu contraseña, pide una temporal a quien te dio el acceso.
            </p>
          </form>
        </div>
      </section>
    </div>
  );
}
