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
 * Marca de ErgoPostura: una «e» construida como un goniómetro. El arco es el cuerpo de la letra;
 * el travesaño es el brazo fijo y, desde la articulación, sube el brazo móvil marcando el ángulo.
 */
export function LogoGlyph({ className = "size-8", tone = "dark" }: { className?: string; tone?: "dark" | "light" }) {
  const ink = tone === "light" ? "#ffffff" : "#10131f";
  const accent = tone === "light" ? "#a9c6e6" : "#0b4a8f";
  return (
    <svg viewBox="0 0 40 40" aria-hidden="true" className={`shrink-0 ${className}`}>
      <g fill="none" strokeLinecap="round">
        <path d="M32.5 20A12.5 12.5 0 1 0 29.58 28.03" stroke={ink} strokeWidth="3.4" />
        <path d="M7.5 20H32.5" stroke={ink} strokeWidth="3.4" />
        <path d="M20 20 27.9 13.4" stroke={accent} strokeWidth="3.4" />
        <path d="M26.2 20A6.2 6.2 0 0 0 24.75 16.01" stroke={accent} strokeWidth="1.6" />
      </g>
      <circle cx="20" cy="20" r="3.1" fill={accent} />
      <circle cx="20" cy="20" r="1.2" fill={tone === "light" ? "#10131f" : "#ffffff"} />
    </svg>
  );
}

/** Ícono de aplicación: la marca en blanco sobre un cuadrado azul de señal. */
export function LogoMark({ className = "size-9" }: { className?: string }) {
  return (
    <span className={`relative grid shrink-0 place-items-center overflow-hidden bg-brand-700 ${className}`}>
      <LogoGlyph tone="light" className="size-[72%]" />
    </span>
  );
}

export function Logo({ tone = "dark", size = "md" }: { tone?: "dark" | "light"; size?: "md" | "lg" }) {
  return (
    <span className="flex items-center gap-2">
      <LogoGlyph tone={tone} className={size === "lg" ? "size-10" : "size-8"} />
      <span className={`font-display tracking-[-0.03em] ${size === "lg" ? "text-2xl" : "text-[19px]"} ${tone === "light" ? "text-white" : "text-ink-950"}`}>
        ergopostura
      </span>
    </span>
  );
}

/** Datos secundarios bajo un título (empresa, sede, área…), separados por una barra fina. */
export function Meta({ items }: { items: readonly (ReactNode | null | false | undefined)[] }) {
  const shown = items.filter((item) => item !== null && item !== false && item !== undefined && item !== "");
  return (
    <p className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[15px] text-ink-600">
      {shown.map((item, index) => (
        <span key={index} className="inline-flex items-center gap-3">
          {index ? <span className="h-3.5 w-px bg-ink-300" aria-hidden="true" /> : null}
          {item}
        </span>
      ))}
    </p>
  );
}

/** Panel de contenido: superficie de vidrio casi opaca, para leer tablas y formularios con comodidad. */
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`surface min-w-0 p-6 ${className}`}>{children}</section>;
}

export function SectionHead({ title, subtitle, action }: { title: string; subtitle?: string | undefined; action?: ReactNode }) {
  return (
    <div className="mb-5 flex items-start justify-between gap-3">
      <div>
        <h2 className="font-display text-xl text-ink-950">{title}</h2>
        {subtitle ? <p className="mt-0.5 text-sm text-ink-500">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

/** inverse e inverseOutline: botones sobre el campo azul del cartel. */
type Variant = "primary" | "secondary" | "ghost" | "danger" | "dangerGhost" | "inverse" | "inverseOutline";
const VARIANTS: Record<Variant, string> = {
  primary: "btn-primary",
  secondary: "border border-ink-950 bg-white text-ink-950 hover:bg-ink-950 hover:text-white disabled:border-ink-300 disabled:text-ink-400 disabled:hover:bg-white",
  ghost: "text-brand-700 underline decoration-brand-700/30 underline-offset-4 hover:decoration-brand-700",
  dangerGhost: "text-red-700 underline decoration-red-700/30 underline-offset-4 hover:decoration-red-700",
  danger: "bg-red-700 text-white hover:bg-red-800 disabled:opacity-55",
  inverse: "bg-white text-brand-800 hover:bg-ink-100",
  inverseOutline: "border border-white text-white hover:bg-white hover:text-brand-800",
};

// La presión se nota: el botón cede un poco al hacer clic.
const PRESS = "transition-[background-color,color,text-decoration-color,transform] duration-150 ease-out active:translate-y-px disabled:active:translate-y-0";

export function Button({ variant = "primary", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={`inline-flex h-11 items-center justify-center gap-2 px-5 text-sm font-semibold ${PRESS} disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}

/** Enlace con forma de botón. Los de texto (ghost) son más compactos; los demás miden lo mismo que Button. */
export function linkButtonClass(variant: Variant = "ghost") {
  const size = variant === "ghost" || variant === "dangerGhost" ? "h-9 px-1" : "h-11 px-5";
  return `inline-flex ${size} shrink-0 items-center justify-center gap-2 whitespace-nowrap text-sm font-semibold ${PRESS} ${VARIANTS[variant]}`;
}

export function Field({ label, error, hint, id, ...input }: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string | undefined; hint?: string; id: string }) {
  return (
    <div className="mb-4">
      <label htmlFor={id} className="mb-1.5 block text-[13px] font-medium text-ink-700">{label}</label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        className={`h-11 w-full border bg-white px-3.5 text-sm text-ink-950 outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-ink-400 focus:ring-4 ${
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
  return <div role="alert" className="mb-4 border border-red-700 bg-red-50 px-3.5 py-2.5 text-sm text-red-800">{error.message}</div>;
}

export function ErrorState({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  return (
    <Card className="flex flex-col items-center gap-3 py-10 text-center">
      <span className="grid size-12 place-items-center bg-red-50 text-red-700"><Icon name="circle-exclamation-point" /></span>
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
  blue: "border border-brand-700 bg-white text-brand-800",
  amber: "border border-ink-950 bg-white text-ink-950",
  orange: "border border-ink-950 bg-white text-ink-950",
  teal: "bg-brand-50 text-brand-800",
  red: "bg-ink-950 text-white",
  green: "bg-ink-100 text-ink-800",
  neutral: "bg-ink-100 text-ink-700",
};

export function Badge({ tone = "neutral", children, dot = false }: { tone?: Tone; children: ReactNode; dot?: boolean }) {
  return (
    <span className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap px-2 py-0.5 text-xs font-semibold ${TONES[tone]}`}>
      {dot ? <span className="size-1.5 rounded-full bg-current" /> : null}
      {children}
    </span>
  );
}

/** Colores del semáforo RULA: solo para riesgo, nunca para acciones. */
export const RISK_COLORS = {
  verde: { chip: "bg-[#1e7a46] text-white", text: "text-[#1e7a46]", soft: "bg-emerald-50 text-emerald-900" },
  amarillo: { chip: "bg-[#c99700] text-ink-950", text: "text-[#8a6700]", soft: "bg-amber-50 text-amber-950" },
  rojo: { chip: "bg-[#b3121f] text-white", text: "text-[#b3121f]", soft: "bg-red-50 text-red-900" },
} as const;

/** Trama de cada nivel, igual que en la portada: el riesgo se lee también en blanco y negro. */
export const RISK_PATTERN = {
  verde: {},
  amarillo: { backgroundImage: "repeating-linear-gradient(45deg, transparent 0 5px, rgb(255 255 255 / .28) 5px 7px)" },
  rojo: { backgroundImage: "repeating-linear-gradient(0deg, transparent 0 3px, rgb(255 255 255 / .2) 3px 5px)" },
} as const;

/** El color nunca va solo: el número del nivel de acción, su texto y su trama lo acompañan (RNF-004). */
export function RiskBadge({ risk }: { risk: Risk | null }) {
  if (!risk) return <Badge>Sin resultado</Badge>;
  const colors = RISK_COLORS[risk.traffic_light];
  return (
    <span className="inline-flex shrink-0 items-center gap-2 whitespace-nowrap text-xs font-semibold" title={`Nivel de acción ${risk.level} de 4`}>
      <span className={`grid h-5 place-items-center px-1.5 text-[11px] font-bold tabular ${colors.chip}`} style={RISK_PATTERN[risk.traffic_light]}>
        Nivel {risk.level}
      </span>
      <span className={colors.text}>{risk.label}</span>
    </span>
  );
}

const CONTRACT_TONES: Record<ContractStatus, Tone> = { vigente: "teal", por_vencer: "amber", por_iniciar: "blue", vencido: "neutral" };

export function ContractBadge({ status, label }: { status: ContractStatus; label: string }) {
  return <Badge tone={CONTRACT_TONES[status]}>{label}</Badge>;
}
