import { useEffect, useId, useRef, type FormEvent, type ReactNode } from "react";

import type { ApiError } from "../api/client";
import { Button, Icon } from "./ui";

/** Ventana modal sobre <dialog>: el navegador maneja el foco, Escape y el fondo. */
export function Modal({ title, onClose, children, wide = false }: {
  title: string; onClose: () => void; children: ReactNode; wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (dialog && !dialog.open) dialog.showModal();
    return () => dialog?.close();
  }, []);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      className={`m-auto max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] overflow-y-auto rounded-xl border-0 bg-white p-0 text-ink-950 shadow-float backdrop:bg-ink-950/45 backdrop:backdrop-blur-[2px] ${
        wide ? "max-w-2xl" : "max-w-lg"
      }`}
    >
      <div className="flex items-center justify-between gap-3 border-b border-ink-100 px-5 py-4">
        <h2 id={titleId} className="font-display text-lg font-bold">{title}</h2>
        <button type="button" onClick={onClose} className="rounded-md p-1.5 text-ink-500 transition-colors hover:bg-ink-100 hover:text-ink-900" aria-label="Cerrar">
          <Icon name="x" />
        </button>
      </div>
      {children}
    </dialog>
  );
}

/** Mensaje general del error: el de la API y, si existe, el error que no es de un campo. */
export function FormAlert({ error }: { error: ApiError | null }) {
  if (!error) return null;
  const general = error.field("__all__");
  return (
    <div role="alert" className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-800">
      {error.message}
      {general && general !== error.message ? <span className="mt-1 block font-medium">{general}</span> : null}
    </div>
  );
}

export function FormModal({ title, note, submitLabel = "Guardar", sending, error, onClose, onSubmit, children, wide }: {
  title: string;
  note?: string | undefined;
  submitLabel?: string;
  sending: boolean;
  error: ApiError | null;
  onClose: () => void;
  onSubmit: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <Modal title={title} onClose={onClose} wide={wide ?? false}>
      <form onSubmit={handleSubmit} noValidate>
        <div className="px-5 pt-5">
          <FormAlert error={error} />
          {children}
          {note ? <p className="mb-4 rounded-md border-l-2 border-brand-300 bg-brand-50/60 px-3 py-2.5 text-sm text-ink-700">{note}</p> : null}
        </div>
        <div className="flex justify-end gap-2 border-t border-ink-100 px-5 py-4">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button type="submit" disabled={sending}>{sending ? "Guardando…" : submitLabel}</Button>
        </div>
      </form>
    </Modal>
  );
}

export function ConfirmModal({ title, message, confirmLabel, danger = false, sending, error, onClose, onConfirm }: {
  title: string; message: string; confirmLabel: string; danger?: boolean; sending: boolean;
  error: ApiError | null; onClose: () => void; onConfirm: () => void;
}) {
  return (
    <Modal title={title} onClose={onClose}>
      <div className="px-5 pt-5">
        <FormAlert error={error} />
        <p className="mb-5 text-sm text-ink-600">{message}</p>
      </div>
      <div className="flex justify-end gap-2 border-t border-ink-100 px-5 py-4">
        <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
        <Button type="button" variant={danger ? "danger" : "primary"} disabled={sending} onClick={onConfirm}>
          {sending ? "Guardando…" : confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
