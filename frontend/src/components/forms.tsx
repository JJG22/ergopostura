import type { ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

/** Campos de formulario con la misma presentación que `Field`: etiqueta, ayuda y error accesibles. */

export const controlClass = (error?: string, full = true) =>
  `${full ? "w-full " : ""}rounded-lg border bg-white px-3 text-sm text-slate-900 outline-none transition focus:ring-2 focus:ring-teal-600/30 disabled:bg-slate-100 disabled:text-slate-400 ${
    error ? "border-red-600" : "border-slate-300 focus:border-teal-600"
  }`;

interface ShellProps {
  id: string;
  label: string;
  error?: string | undefined;
  hint?: string | undefined;
  children: ReactNode;
}

export function FieldShell({ id, label, error, hint, children }: ShellProps) {
  return (
    <div className="mb-4">
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-slate-700">{label}</label>
      {children}
      {hint && !error ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
      {error ? <p id={`${id}-error`} role="alert" className="mt-1 text-xs font-medium text-red-700">{error}</p> : null}
    </div>
  );
}

export interface Option {
  value: string;
  label: string;
}

type SelectProps = Omit<SelectHTMLAttributes<HTMLSelectElement>, "id"> & {
  id: string;
  label: string;
  options: readonly Option[];
  placeholder?: string;
  error?: string | undefined;
  hint?: string | undefined;
};

export function SelectField({ id, label, options, placeholder, error, hint, ...select }: SelectProps) {
  return (
    <FieldShell id={id} label={label} error={error} hint={hint}>
      <select id={id} aria-invalid={error ? true : undefined} aria-describedby={error ? `${id}-error` : undefined}
        className={`h-11 ${controlClass(error)}`} {...select}>
        {placeholder !== undefined ? <option value="">{placeholder}</option> : null}
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    </FieldShell>
  );
}

type TextAreaProps = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "id"> & {
  id: string;
  label: string;
  error?: string | undefined;
  hint?: string | undefined;
};

export function TextAreaField({ id, label, error, hint, ...textarea }: TextAreaProps) {
  return (
    <FieldShell id={id} label={label} error={error} hint={hint}>
      <textarea id={id} rows={3} aria-invalid={error ? true : undefined} aria-describedby={error ? `${id}-error` : undefined}
        className={`py-2.5 ${controlClass(error)}`} {...textarea} />
    </FieldShell>
  );
}

export function CheckboxField({ id, label, checked, onChange, hint }: {
  id: string; label: string; checked: boolean; onChange: (checked: boolean) => void; hint?: string;
}) {
  return (
    <div className="mb-4">
      <label htmlFor={id} className="flex items-center gap-2.5 text-sm font-medium text-slate-700">
        <input id={id} type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)}
          className="size-4 rounded border-slate-300 accent-teal-700" />
        {label}
      </label>
      {hint ? <p className="mt-1 pl-6.5 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}

export function Grid({ children }: { children: ReactNode }) {
  return <div className="grid gap-x-4 sm:grid-cols-2">{children}</div>;
}
