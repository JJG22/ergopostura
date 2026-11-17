import { useState, type FormEvent, type ReactNode } from "react";

import type { Option } from "./forms";
import { controlClass } from "./forms";
import { Button, Icon } from "./ui";

export interface Page<T> {
  results: T[];
  count: number;
  page: number;
  pages: number;
}

/** Búsqueda de una lista. Se envía al pulsar «Buscar» o Enter, como en la pantalla actual. */
export function SearchBar({ query, placeholder, label, onSearch, filter }: {
  query: string;
  placeholder: string;
  label: string;
  onSearch: (query: string, filter: string) => void;
  filter?: { label: string; value: string; options: readonly Option[]; allLabel: string };
}) {
  const [text, setText] = useState(query);
  const [chosen, setChosen] = useState(filter?.value ?? "");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSearch(text.trim(), chosen);
  }

  return (
    <form role="search" onSubmit={handleSubmit} className="mb-4 flex flex-wrap gap-2">
      <label className="relative min-w-56 flex-1">
        <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-ink-400"><Icon name="search" /></span>
        <input type="search" value={text} onChange={(event) => setText(event.target.value)} aria-label={label}
          placeholder={placeholder} className={`h-10 pl-10 ${controlClass()}`} />
      </label>
      {filter ? (
        <select aria-label={filter.label} value={chosen} onChange={(event) => setChosen(event.target.value)}
          className={`h-10 ${controlClass(undefined, false)}`}>
          <option value="">{filter.allLabel}</option>
          {filter.options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      ) : null}
      <Button type="submit" variant="secondary">Buscar</Button>
    </form>
  );
}

export function Pagination({ page, noun, onPage }: { page: Page<unknown>; noun: string; onPage: (page: number) => void }) {
  if (page.pages <= 1) return null;
  return (
    <nav aria-label="Paginación" className="mt-4 flex items-center justify-between gap-3 border-t border-ink-100 pt-4 text-sm text-ink-500 tabular">
      <span>{page.count} {noun} · página {page.page} de {page.pages}</span>
      <div className="flex gap-2">
        <Button variant="secondary" disabled={page.page <= 1} onClick={() => onPage(page.page - 1)}>Anterior</Button>
        <Button variant="secondary" disabled={page.page >= page.pages} onClick={() => onPage(page.page + 1)}>Siguiente</Button>
      </div>
    </nav>
  );
}

export function Table({ head, children }: { head: readonly string[]; children: ReactNode }) {
  return (
    <div className="relative -mx-6 overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="border-y-2 border-ink-950 text-xs font-medium text-ink-600">
          <tr>{head.map((title, index) => <th key={index} scope="col" className="px-6 py-3 font-medium">{title}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-ink-100 [&>tr]:transition-colors [&>tr:hover]:bg-ink-50 [&_td:first-child]:pl-6 [&_td:last-child]:pr-6">{children}</tbody>
      </table>
    </div>
  );
}

export function EmptyState({ icon, title, children }: { icon: string; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center">
      <span className="grid size-12 place-items-center border border-dashed border-ink-300 text-ink-400"><Icon name={icon} /></span>
      <p className="font-semibold text-ink-950">{title}</p>
      {children ? <p className="max-w-sm text-sm text-ink-500">{children}</p> : null}
    </div>
  );
}

/**
 * Encabezado de pantalla con forma de portada: título grande, una frase que explica para qué
 * sirve la pantalla y, a la derecha, la acción principal.
 */
export function PageHead({ title, subtitle, eyebrow, action }: { title: string; subtitle?: ReactNode; eyebrow?: string; action?: ReactNode }) {
  return (
    <header className="mb-10 flex flex-wrap items-end justify-between gap-6 motion-safe:animate-[rise_480ms_cubic-bezier(0.2,0.8,0.2,1)]">
      <div className="min-w-0 max-w-3xl">
        {eyebrow ? <p className="mb-3 text-sm font-semibold text-brand-700">{eyebrow}</p> : null}
        <h1 className="font-display text-[2.4rem] leading-[1.02] text-ink-950 sm:text-6xl">{title}</h1>
        {subtitle ? <p className="mt-4 max-w-2xl text-[17px] leading-relaxed text-ink-600">{subtitle}</p> : null}
      </div>
      {action}
    </header>
  );
}
