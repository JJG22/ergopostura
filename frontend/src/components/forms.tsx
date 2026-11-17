import { useState, type ReactNode, type Ref, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

/** Campos de formulario con la misma presentación que `Field`: etiqueta, ayuda y error accesibles. */

export const controlClass = (error?: string, full = true) =>
  `${full ? "w-full " : ""}border bg-white px-3.5 text-sm text-ink-950 outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-ink-400 focus:ring-4 disabled:bg-ink-100 disabled:text-ink-400 ${
    error ? "border-red-600 focus:ring-red-600/15" : "border-ink-200 hover:border-ink-300 focus:border-brand-600 focus:ring-brand-600/15"
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
      <label htmlFor={id} className="mb-1.5 block text-[13px] font-medium text-ink-700">{label}</label>
      {children}
      {hint && !error ? <p className="mt-1.5 text-xs text-ink-500">{hint}</p> : null}
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
      <label htmlFor={id} className="flex items-center gap-2.5 text-sm font-medium text-ink-700">
        <input id={id} type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)}
          className="size-4 rounded border-ink-300 accent-brand-700" />
        {label}
      </label>
      {hint ? <p className="mt-1 pl-6.5 text-xs text-ink-500">{hint}</p> : null}
    </div>
  );
}

/**
 * Selector de archivo en español: un botón cuadrado y el nombre del archivo elegido. El campo
 * nativo sigue ahí (oculto a la vista), así que el teclado, la etiqueta y el formulario funcionan igual.
 */
export function FilePicker({ id, accept, button, inputRef, onFile, invalid, name }: {
  id: string; accept: string; button: string; inputRef?: Ref<HTMLInputElement>;
  onFile?: (file: File | null) => void; invalid?: boolean; name?: string;
}) {
  const [chosen, setChosen] = useState("");
  return (
    <span className="flex min-w-0 items-center gap-3">
      <input id={id} ref={inputRef} name={name} type="file" accept={accept} className="peer sr-only" aria-invalid={invalid ? true : undefined}
        onChange={(event) => { const file = event.target.files?.[0] ?? null; setChosen(file?.name ?? ""); onFile?.(file); }} />
      <label htmlFor={id} className="inline-flex h-11 shrink-0 cursor-pointer items-center border border-ink-950 bg-white px-4 text-sm font-semibold text-ink-950 transition-colors hover:bg-ink-950 hover:text-white peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-brand-700">
        {button}
      </label>
      <span className="min-w-0 truncate text-sm text-ink-600">{chosen || "Ningún archivo elegido"}</span>
    </span>
  );
}

export function Grid({ children }: { children: ReactNode }) {
  return <div className="grid gap-x-4 sm:grid-cols-2">{children}</div>;
}
