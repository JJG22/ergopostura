import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

import type { ApiError } from "../api/client";
import type { ContractStatus, Risk, Tone } from "../api/types";
import { ICONS } from "./icons";

export function Icon({ name, className = "size-4.5" }: { name: string; className?: string }) {
  const nodes = ICONS[name];
  if (!nodes) throw new Error(`Ícono desconocido: ${name}`);
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
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

/**
 * Marca de ErgoPostura: tronco, brazo y antebrazo articulados en el codo, con el arco del
 * ángulo que mide el goniómetro. Es lo que RULA observa en cada puesto.
 */
export function LogoMark({ className = "size-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={`shrink-0 ${className}`}>
      <rect width="32" height="32" rx="7" fill="#3343d3" />
      <path d="M15.06 14.6A4.5 4.5 0 0 1 22.2 14.94" fill="none" stroke="#c4cdff" strokeWidth="1.6" strokeLinecap="round" />
      <g fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="7" r="2.4" />
        <path d="M12 11.2 10.6 25M12 12.2l6.5 5.3L25 13" />
      </g>
      <circle cx="18.5" cy="17.5" r="1.7" fill="#c4cdff" />
    </svg>
  );
}

export function Logo({ tone = "dark" }: { tone?: "dark" | "light" }) {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      <span className={`font-display text-[17px] font-bold ${tone === "light" ? "text-white" : "text-ink-950"}`}>ErgoPostura</span>
    </span>
  );
}

/** Datos secundarios bajo un título (empresa, sede, área…), separados por una barra fina. */
export function Meta({ items }: { items: readonly (ReactNode | null | false | undefined)[] }) {
  const shown = items.filter((item) => item !== null && item !== false && item !== undefined && item !== "");
  return (
    <p className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-500">
      {shown.map((item, index) => (
        <span key={index} className="inline-flex items-center gap-3">
          {index ? <span className="h-3.5 w-px bg-ink-300" aria-hidden="true" /> : null}
          {item}
        </span>
      ))}
    </p>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`min-w-0 rounded-lg border border-ink-200 bg-white p-5 ${className}`}>{children}</section>;
}

export function SectionHead({ title, subtitle, action }: { title: string; subtitle?: string | undefined; action?: ReactNode }) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div>
        <h2 className="text-[15px] font-semibold text-ink-950">{title}</h2>
        {subtitle ? <p className="mt-0.5 text-sm text-ink-500">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

type Variant = "primary" | "secondary" | "ghost" | "danger" | "dangerGhost";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand-700 text-white hover:bg-brand-800 disabled:bg-brand-700/50",
  secondary: "border border-ink-200 bg-white text-ink-800 hover:border-ink-300 hover:bg-ink-50 disabled:text-ink-400",
  ghost: "text-brand-700 hover:bg-brand-50",
  dangerGhost: "text-red-700 hover:bg-red-50",
  danger: "bg-red-700 text-white hover:bg-red-800 disabled:bg-red-700/50",
};

// La presión se nota: el botón cede un poco al hacer clic.
const PRESS = "transition-[background-color,border-color,color,transform] duration-150 ease-out active:scale-[0.98] disabled:active:scale-100";

export function Button({ variant = "primary", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={`inline-flex h-10 items-center justify-center gap-2 rounded-md px-4 text-sm font-semibold ${PRESS} disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}

/** Enlace con forma de botón. Los de texto (ghost) son más compactos; los demás miden lo mismo que Button. */
export function linkButtonClass(variant: Variant = "ghost") {
  const size = variant === "ghost" || variant === "dangerGhost" ? "h-9 px-3" : "h-10 px-4";
  return `inline-flex ${size} items-center justify-center gap-2 rounded-md text-sm font-semibold ${PRESS} ${VARIANTS[variant]}`;
}

export function Field({ label, error, hint, id, ...input }: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string | undefined; hint?: string; id: string }) {
  return (
    <div className="mb-4">
      <label htmlFor={id} className="mb-1.5 block text-[13px] font-medium text-ink-700">{label}</label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        className={`h-11 w-full rounded-md border bg-white px-3 text-sm text-ink-950 outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-ink-400 focus:ring-4 ${
          error ? "border-red-600 focus:ring-red-600/15" : "border-ink-200 hover:border-ink-300 focus:border-brand-600 focus:ring-brand-600/15"
        }`}
        {...input}
      />
      {hint && !error ? <p className="mt-1.5 text-xs text-ink-500">{hint}</p> : null}
      {error ? <p id={`${id}-error`} role="alert" className="mt-1.5 text-xs font-medium text-red-700">{error}</p> : null}
    </div>
  );
}

export function Spinner({ label = "Cargando…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 text-sm text-ink-500">
      <span className="size-4 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
      {label}
    </div>
  );
}

export function FullPageSpinner() {
  return (
    <div className="grid min-h-screen place-items-center bg-ink-50">
      <Spinner />
    </div>
  );
}

export function FormError({ error }: { error: ApiError | null }) {
  if (!error) return null;
  return <div role="alert" className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-800">{error.message}</div>;
}

export function ErrorState({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  return (
    <Card className="flex flex-col items-center gap-3 py-10 text-center">
      <span className="grid size-11 place-items-center rounded-md bg-red-50 text-red-600"><Icon name="circle-exclamation-point" /></span>
      <div>
        <p className="font-semibold text-ink-950">No se pudo cargar esta información</p>
        <p className="text-sm text-ink-500">{error.message}</p>
      </div>
      {onRetry ? <Button variant="secondary" onClick={onRetry}>Intentar de nuevo</Button> : null}
    </Card>
  );
}

export function EmptyText({ children }: { children: ReactNode }) {
  return <p className="py-2 text-sm text-ink-500">{children}</p>;
}

const TONES: Record<Tone, string> = {
  blue: "bg-sky-100 text-sky-900",
  amber: "bg-amber-100 text-amber-900",
  orange: "bg-orange-100 text-orange-900",
  teal: "bg-brand-50 text-brand-800",
  red: "bg-red-100 text-red-800",
  green: "bg-emerald-100 text-emerald-900",
  neutral: "bg-ink-100 text-ink-600",
};

export function Badge({ tone = "neutral", children, dot = false }: { tone?: Tone; children: ReactNode; dot?: boolean }) {
  return (
    <span className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded px-2 py-0.5 text-xs font-semibold ${TONES[tone]}`}>
      {dot ? <span className="size-1.5 rounded-full bg-current" /> : null}
      {children}
    </span>
  );
}

/** Colores del semáforo RULA: solo para riesgo, nunca para acciones. */
export const RISK_COLORS = {
  verde: { chip: "bg-emerald-600 text-white", text: "text-emerald-800", soft: "bg-emerald-50 text-emerald-900" },
  amarillo: { chip: "bg-amber-500 text-ink-950", text: "text-amber-800", soft: "bg-amber-50 text-amber-950" },
  rojo: { chip: "bg-red-600 text-white", text: "text-red-700", soft: "bg-red-50 text-red-900" },
} as const;

/** El color nunca va solo: el número del nivel de acción y su texto lo acompañan (RNF-004). */
export function RiskBadge({ risk }: { risk: Risk | null }) {
  if (!risk) return <Badge>Sin resultado</Badge>;
  const colors = RISK_COLORS[risk.traffic_light];
  return (
    <span className="inline-flex shrink-0 items-center gap-2 whitespace-nowrap text-xs font-semibold" title={`Nivel de acción ${risk.level} de 4`}>
      <span className={`grid h-5 min-w-5 place-items-center rounded px-1 text-[11px] font-bold tabular ${colors.chip}`}>
        <span className="sr-only">Nivel </span>{risk.level}
      </span>
      <span className={colors.text}>{risk.label}</span>
    </span>
  );
}

const CONTRACT_TONES: Record<ContractStatus, Tone> = { vigente: "teal", por_vencer: "amber", por_iniciar: "blue", vencido: "neutral" };

export function ContractBadge({ status, label }: { status: ContractStatus; label: string }) {
  return <Badge tone={CONTRACT_TONES[status]}>{label}</Badge>;
}
