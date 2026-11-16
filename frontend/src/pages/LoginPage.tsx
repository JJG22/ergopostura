import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router";

import { toApiError, type ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Field, FormError, FullPageSpinner, Logo } from "../components/ui";
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
    <div className="grid min-h-screen bg-white lg:grid-cols-[1.15fr_1fr]">
      <section className="relative hidden overflow-hidden bg-ink-950 p-12 text-white lg:flex lg:flex-col">
        <Logo tone="light" />
        <PostureSketch />
        <div className="relative max-w-md">
          <h1 className="font-display text-[2.6rem] font-bold leading-[1.05]">Cada puesto de trabajo, medido con el mismo método.</h1>
          <p className="mt-4 text-[15px] leading-relaxed text-ink-300">
            Visitas, análisis RULA, recomendaciones e informes para las empresas que acompañas.
          </p>
        </div>
      </section>
      <section className="flex flex-col p-6 sm:p-10">
        <div className="lg:hidden"><Logo /></div>
        <div className="flex flex-1 items-center justify-center py-10">
          <form onSubmit={handleSubmit} noValidate className="w-full max-w-sm">
            <h2 className="font-display text-[1.9rem] font-bold leading-tight text-ink-950">Ingresar</h2>
            <p className="mb-8 mt-2 text-sm text-ink-500">Usa el correo y la contraseña de tu cuenta.</p>
            {/* Los errores de un campo van debajo de él; los demás, arriba del formulario. */}
            {error && !error.field("username") && !error.field("password") ? <FormError error={error} /> : null}
            <Field id="email" label="Correo electrónico" type="email" autoComplete="email" autoFocus placeholder="nombre@empresa.com"
              value={email} onChange={(e) => setEmail(e.target.value)} error={error?.field("username")} />
            <Field id="password" label="Contraseña" type="password" autoComplete="current-password"
              value={password} onChange={(e) => setPassword(e.target.value)} error={error?.field("password")} />
            <label className="mb-6 flex items-center gap-2.5 text-sm text-ink-700">
              <input type="checkbox" className="size-4 accent-brand-700" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
              Mantener la sesión iniciada
            </label>
            <Button type="submit" className="h-11 w-full" disabled={sending}>{sending ? "Ingresando…" : "Ingresar"}</Button>
            <p className="mt-6 border-t border-ink-100 pt-5 text-xs leading-relaxed text-ink-500">
              Acceso solo para usuarios autorizados. Si olvidaste tu contraseña, pide una temporal a quien te dio el acceso.
            </p>
          </form>
        </div>
      </section>
    </div>
  );
}

/**
 * Boceto técnico de una postura de trabajo con los ángulos que mide RULA: flexión del tronco
 * y del brazo, y el ángulo del codo. Se dibuja una sola vez al abrir la página.
 */
function PostureSketch() {
  const seg = "fill-none stroke-white [stroke-dasharray:1] [stroke-dashoffset:1] motion-safe:animate-[draw_700ms_cubic-bezier(0.3,0.7,0.2,1)_forwards] motion-reduce:[stroke-dashoffset:0]";
  const arc = "fill-none stroke-brand-300 [stroke-dasharray:1] [stroke-dashoffset:1] motion-safe:animate-[draw_600ms_ease-out_forwards] motion-reduce:[stroke-dashoffset:0]";
  const guide = "stroke-ink-500 opacity-0 motion-safe:animate-[appear_500ms_ease-out_forwards] motion-reduce:opacity-100";
  const label = "fill-brand-200 text-[13px] font-semibold opacity-0 motion-safe:animate-[appear_400ms_ease-out_forwards] motion-reduce:opacity-100";
  const delay = (ms: number) => ({ animationDelay: `${ms}ms` });
  return (
    <div className="relative my-6 flex flex-1 items-center justify-center">
      <svg viewBox="0 0 400 440" aria-hidden="true" className="h-full max-h-[440px] w-full max-w-[400px]">
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="1" className="fill-ink-800" />
          </pattern>
        </defs>
        <rect width="400" height="440" fill="url(#grid)" />
        {/* Puesto: mesa de trabajo y caja. */}
        <path d="M270 268h130M300 268v172" className={guide} strokeWidth="2" style={delay(100)} />
        <rect x="318" y="228" width="56" height="40" rx="2" className={`fill-none ${guide}`} strokeWidth="2" style={delay(150)} />
        {/* Referencias verticales desde las que se miden los ángulos. */}
        <path d="M140 300V170M184.5 177.8V290" className={guide} strokeWidth="1.2" strokeDasharray="4 5" style={delay(900)} />
        {/* Cuerpo: piernas, tronco, cuello, cabeza, brazo y antebrazo. */}
        <g strokeWidth="5" strokeLinecap="round" strokeLinejoin="round">
          <path pathLength={1} d="M146 430h22M142 428v-63l-2-65" className={seg} style={delay(200)} />
          <path pathLength={1} d="M140 300l44.5-122.2" className={seg} style={delay(450)} />
          <path pathLength={1} d="M184.5 177.8l17.2-24.6" className={seg} style={delay(650)} />
          <circle pathLength={1} cx="214.3" cy="135.2" r="18" className={seg} style={delay(700)} />
          <path pathLength={1} d="M184.5 177.8l67.2 67.2 83.7 14.8" className={seg} style={delay(800)} />
        </g>
        {/* Articulaciones. */}
        <g className="fill-brand-400 opacity-0 motion-safe:animate-[appear_300ms_ease-out_forwards] motion-reduce:opacity-100" style={delay(1300)}>
          <circle cx="140" cy="300" r="6" /><circle cx="184.5" cy="177.8" r="6" /><circle cx="251.7" cy="245" r="6" />
        </g>
        {/* Ángulos: tronco 20°, brazo 45°, codo. */}
        <g strokeWidth="2" strokeLinecap="round">
          <path pathLength={1} d="M140 240A60 60 0 0 1 160.5 243.6" className={arc} style={delay(1400)} />
          <path pathLength={1} d="M184.5 222.8A45 45 0 0 0 216.3 209.6" className={arc} style={delay(1550)} />
          <path pathLength={1} d="M233.3 226.6A26 26 0 0 1 277.3 249.5" className={arc} style={delay(1700)} />
        </g>
        <text x="143" y="223" className={label} style={delay(1700)}>20°</text>
        <text x="191" y="243" className={label} style={delay(1850)}>45°</text>
        <text x="244" y="208" className={label} style={delay(2000)}>145°</text>
      </svg>
    </div>
  );
}
