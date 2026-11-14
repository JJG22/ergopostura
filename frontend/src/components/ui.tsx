import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

import type { ApiError } from "../api/client";
import type { ContractStatus, Risk, Tone } from "../api/types";
import { ICONS } from "./icons";

export function Icon({ name, className = "size-[18px]" }: { name: string; className?: string }) {
  const nodes = ICONS[name];
  if (!nodes) throw new Error(`Ícono desconocido: ${name}`);
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={`shrink-0 ${className}`}>
      {nodes.map(([tag, attributes], index) => {
        const Tag = tag as "path";
        const props = Object.fromEntries(
          Object.entries(attributes).map(([key, value]) => [key.replace(/-([a-z])/g, (_, c: string) => c.toUpperCase()), value]),
        );
        return <Tag key={index} {...props} />;
      })}
    </svg>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`min-w-0 rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>{children}</section>;
}

export function SectionHead({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-3 flex items-start justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        {subtitle ? <p className="text-sm text-slate-500">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

type Variant = "primary" | "secondary" | "ghost" | "danger";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-teal-700 text-white hover:bg-teal-800 disabled:bg-teal-700/60",
  secondary: "border border-slate-300 bg-white text-slate-800 hover:bg-slate-50",
  ghost: "text-teal-700 hover:bg-teal-50",
  danger: "bg-red-700 text-white hover:bg-red-800 disabled:bg-red-700/60",
};

export function Button({ variant = "primary", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={`inline-flex h-10 items-center justify-center gap-2 rounded-lg px-4 text-sm font-semibold transition disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}

export function linkButtonClass(variant: Variant = "ghost") {
  return `inline-flex h-9 items-center gap-1.5 rounded-lg px-3 text-sm font-semibold ${VARIANTS[variant]}`;
}

export function Field({ label, error, hint, id, ...input }: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string | undefined; hint?: string; id: string }) {
  return (
    <div className="mb-4">
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-slate-700">{label}</label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        className={`h-11 w-full rounded-lg border bg-white px-3 text-sm text-slate-900 outline-none transition focus:ring-2 focus:ring-teal-600/30 ${
          error ? "border-red-600" : "border-slate-300 focus:border-teal-600"
        }`}
        {...input}
      />
      {hint && !error ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
      {error ? <p id={`${id}-error`} role="alert" className="mt-1 text-xs font-medium text-red-700">{error}</p> : null}
    </div>
  );
}

export function Spinner({ label = "Cargando…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 text-sm text-slate-500">
      <span className="size-5 animate-spin rounded-full border-2 border-teal-600 border-t-transparent" />
      {label}
    </div>
  );
}

export function FullPageSpinner() {
  return (
    <div className="grid min-h-screen place-items-center bg-slate-50">
      <Spinner />
    </div>
  );
}

export function FormError({ error }: { error: ApiError | null }) {
  if (!error) return null;
  return <div role="alert" className="mb-4 rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-800">{error.message}</div>;
}

export function ErrorState({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  return (
    <Card className="flex flex-col items-center gap-3 py-10 text-center">
      <span className="grid size-12 place-items-center rounded-full bg-red-50 text-red-600"><Icon name="circle-exclamation-point" /></span>
      <div>
        <p className="font-semibold text-slate-900">No pudimos cargar esta información</p>
        <p className="text-sm text-slate-500">{error.message}</p>
      </div>
      {onRetry ? <Button variant="secondary" onClick={onRetry}>Intentar de nuevo</Button> : null}
    </Card>
  );
}

export function EmptyText({ children }: { children: ReactNode }) {
  return <p className="py-2 text-sm text-slate-500">{children}</p>;
}

const TONES: Record<Tone, string> = {
  blue: "bg-blue-100 text-blue-800",
  amber: "bg-amber-100 text-amber-800",
  orange: "bg-orange-100 text-orange-800",
  teal: "bg-teal-100 text-teal-800",
  red: "bg-red-100 text-red-800",
  green: "bg-green-100 text-green-800",
  neutral: "bg-slate-100 text-slate-600",
};

export function Badge({ tone = "neutral", children, dot = false }: { tone?: Tone; children: ReactNode; dot?: boolean }) {
  return (
    <span className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${TONES[tone]}`}>
      {dot ? <span className="size-1.5 rounded-full bg-current" /> : null}
      {children}
    </span>
  );
}

const RISK_TONES: Record<Risk["traffic_light"], Tone> = { verde: "green", amarillo: "amber", rojo: "red" };

/** El color nunca va solo: siempre con el texto del nivel (RNF-004). */
export function RiskBadge({ risk }: { risk: Risk | null }) {
  if (!risk) return <Badge>Sin resultado</Badge>;
  return <Badge tone={RISK_TONES[risk.traffic_light]} dot>{risk.label} · Nivel {risk.level}</Badge>;
}

const CONTRACT_TONES: Record<ContractStatus, Tone> = { vigente: "teal", por_vencer: "amber", por_iniciar: "blue", vencido: "neutral" };

export function ContractBadge({ status, label }: { status: ContractStatus; label: string }) {
  return <Badge tone={CONTRACT_TONES[status]}>{label}</Badge>;
}
