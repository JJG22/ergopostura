import { useState } from "react";

import { toApiError, type ApiError } from "../../api/client";
import { AppLink } from "../../components/AppLink";
import { Grid, SelectField, TextAreaField } from "../../components/forms";
import { FormModal, Modal } from "../../components/Modal";
import { useNotify } from "../../components/Page";
import { Badge, Button, ErrorState, Field, Icon, linkButtonClass, Spinner } from "../../components/ui";
import { formatDay, formatInstant, formatTime } from "../../lib/format";
import { useForm } from "../../lib/useForm";
import { useResource } from "../../lib/useResource";
import { colorOf, visitsApi, type VisitDetail, type VisitInput } from "./api";

const timeOf = (iso: string) => iso.slice(11, 16);

/** Agendar (sin `visit`) o reprogramar. Las reglas las revisa el servidor y llegan como errores. */
export function VisitFormModal({ visit, preset, onClose, onSaved }: {
  visit?: VisitDetail; preset?: { date?: string; hour?: number }; onClose: () => void; onSaved: (startsAt: string) => void;
}) {
  const [options, retry] = useResource((signal) => visitsApi.options(signal));
  const title = visit ? "Reprogramar visita" : "Agendar visita";
  if (options.state !== "ready") {
    return (
      <Modal title={title} onClose={onClose}>
        <div className="p-5">{options.state === "loading" ? <Spinner /> : <ErrorState error={options.error} onRetry={retry} />}</div>
      </Modal>
    );
  }
  const data = options.data;
  const initial: VisitInput = visit
    ? { date: visit.starts_at.slice(0, 10), time: timeOf(visit.starts_at), duration_minutes: String(visit.duration_minutes),
        site: String(visit.site_id), purpose: visit.purpose, contact_name: visit.contact_name, contact_phone: visit.contact_phone }
    : { date: preset?.date ?? "", time: preset?.hour !== undefined ? `${String(preset.hour).padStart(2, "0")}:00` : "",
        duration_minutes: "120", site: data.sites.length === 1 ? (data.sites[0]?.value ?? "") : "", purpose: "", contact_name: "", contact_phone: "" };
  return <VisitForm title={title} visit={visit} initial={initial} options={data} onClose={onClose} onSaved={onSaved} />;
}

function VisitForm({ title, visit, initial, options, onClose, onSaved }: {
  title: string; visit: VisitDetail | undefined; initial: VisitInput; options: Awaited<ReturnType<typeof visitsApi.options>>;
  onClose: () => void; onSaved: (startsAt: string) => void;
}) {
  const notify = useNotify();
  const form = useForm<VisitInput>(initial);
  const { values, set } = form;

  async function save() {
    const result = await form.submit((input) => (visit ? visitsApi.reschedule(visit.id, input) : visitsApi.create(input)));
    if (result) {
      notify(visit ? "Visita reprogramada" : "Visita agendada");
      onSaved(result.starts_at);
    }
  }

  return (
    <FormModal title={title} submitLabel={visit ? "Guardar cambios" : "Agendar visita"} sending={form.sending} error={form.error}
      note={visit ? undefined : "El ingeniero verá la visita en su calendario. Puedes reprogramarla o cancelarla hasta una hora antes."}
      onClose={onClose} onSubmit={() => void save()}>
      <Grid>
        <Field id="date" label="Fecha" type="date" value={values.date} onChange={(e) => set("date", e.target.value)} error={form.fieldError("date")} />
        <Field id="time" label="Hora de llegada" type="time" step={1800} value={values.time} onChange={(e) => set("time", e.target.value)}
          error={form.fieldError("time")} hint={`De lunes a sábado, entre las ${options.work_start} y las ${options.work_end}.`} />
      </Grid>
      <Grid>
        <SelectField id="duration_minutes" label="Duración" options={options.durations} value={values.duration_minutes}
          onChange={(e) => set("duration_minutes", e.target.value)} error={form.fieldError("duration_minutes")} />
        <SelectField id="site" label="Sede" placeholder="Selecciona la sede" options={options.sites} value={values.site}
          onChange={(e) => set("site", e.target.value)} error={form.fieldError("site")} />
      </Grid>
      <TextAreaField id="purpose" label="Motivo de la visita" placeholder="Ej. Evaluar los puestos de empaque y despacho de la planta."
        value={values.purpose} onChange={(e) => set("purpose", e.target.value)} error={form.fieldError("purpose")} />
      <Grid>
        <Field id="contact_name" label="Persona que recibe la visita" placeholder="Ej. Marta Salazar, jefe de SST" value={values.contact_name}
          onChange={(e) => set("contact_name", e.target.value)} error={form.fieldError("contact_name")} />
        <Field id="contact_phone" label="Teléfono de contacto (opcional)" inputMode="tel" placeholder="Ej. 300 123 4567" value={values.contact_phone}
          onChange={(e) => set("contact_phone", e.target.value)} error={form.fieldError("contact_phone")} />
      </Grid>
    </FormModal>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-0.5 py-2 sm:grid-cols-[9rem_1fr]">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="whitespace-pre-line text-sm">{children}</dd>
    </div>
  );
}

type Step = "detail" | "reschedule" | "complete" | "cancel";

/** Detalle de la visita con sus acciones, según el rol y el momento. */
export function VisitDetailView({ visit, onChanged }: { visit: VisitDetail; onChanged: (visit: VisitDetail | null, startsAt?: string) => void }) {
  const [step, setStep] = useState<Step>("detail");
  const color = colorOf(visit.color);
  const back = () => setStep("detail");

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-start gap-3">
        <span className="mt-1.5 size-3 shrink-0 rounded-full" style={{ background: color.fg }} aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <strong className="block">{visit.company.name}</strong>
          <p className="text-sm text-slate-500">{formatDay(visit.starts_at)} · {formatTime(visit.starts_at)} – {formatTime(visit.ends_at)}</p>
        </div>
        <Badge tone={visit.level.tone} dot>{visit.level.label}</Badge>
      </div>
      <dl className="divide-y divide-slate-100">
        <Row label="Sede">{visit.site} · {visit.municipality}{visit.address ? `\n${visit.address}` : ""}</Row>
        <Row label="Duración">{visit.duration_label}</Row>
        <Row label="Motivo">{visit.purpose}</Row>
        <Row label="Recibe">{visit.contact_name}{visit.contact_phone ? <> · <a className="text-teal-700" href={`tel:${visit.contact_phone}`}>{visit.contact_phone}</a></> : null}</Row>
        <Row label="Agendada por">{visit.requested_by ?? "Sin registrar"}{visit.created_at ? ` · ${formatInstant(visit.created_at)}` : ""}</Row>
        {visit.status === "realizada" ? (
          <>
            <Row label="Realizada">Registrada por {visit.completed_by ?? "el ingeniero"}{visit.completed_at ? ` el ${formatInstant(visit.completed_at)}` : ""}</Row>
            {visit.completion_notes ? <Row label="Observaciones">{visit.completion_notes}</Row> : null}
          </>
        ) : visit.cancelled_at ? (
          <>
            <Row label="Cancelada">Por {visit.cancelled_by ?? "Sin registrar"} el {formatInstant(visit.cancelled_at)}</Row>
            <Row label="Motivo de cancelación">{visit.cancellation_reason}</Row>
          </>
        ) : null}
        {visit.evaluations.length ? (
          <Row label="Evaluaciones">
            {visit.evaluations.map((e, i) => <span key={e.id}>{i ? ", " : ""}<AppLink href={e.url} className="text-teal-700 hover:underline">{e.code}</AppLink></span>)}
          </Row>
        ) : null}
      </dl>
      {visit.level.key === "por_cerrar" && visit.can_complete ? (
        <p className="mt-3 flex gap-2 rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-900">
          <Icon name="circle-exclamation-point" className="mt-0.5 size-4" />La hora de la visita ya pasó. Registra si se hizo para poder evaluar, o cancélala si no se realizó.
        </p>
      ) : null}
      {visit.can_cancel || visit.can_reschedule || visit.can_complete || visit.can_evaluate ? (
        <div className="mt-4 flex flex-wrap justify-end gap-2 border-t border-slate-100 pt-4">
          {visit.can_cancel ? <Button variant="dangerGhost" onClick={() => setStep("cancel")}>Cancelar visita</Button> : null}
          {visit.can_reschedule ? <Button onClick={() => setStep("reschedule")}>Reprogramar</Button> : null}
          {visit.can_complete ? <Button onClick={() => setStep("complete")}><Icon name="check" />Registrar realizada</Button> : null}
          {visit.can_evaluate ? <AppLink href={visit.new_evaluation_url} className={linkButtonClass("primary")}><Icon name="clipboard-check" />Nueva evaluación</AppLink> : null}
        </div>
      ) : null}

      {step === "reschedule" ? <VisitFormModal visit={visit} onClose={back} onSaved={(startsAt) => onChanged(null, startsAt)} /> : null}
      {step === "complete" ? <ActionModal kind="complete" visit={visit} onClose={back} onDone={(v) => { back(); onChanged(v); }} /> : null}
      {step === "cancel" ? <ActionModal kind="cancel" visit={visit} onClose={back} onDone={(v) => { back(); onChanged(v); }} /> : null}
    </div>
  );
}

function ActionModal({ kind, visit, onClose, onDone }: {
  kind: "complete" | "cancel"; visit: VisitDetail; onClose: () => void; onDone: (visit: VisitDetail) => void;
}) {
  const notify = useNotify();
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const complete = kind === "complete";

  async function submit() {
    setSending(true);
    setError(null);
    try {
      const result = complete ? await visitsApi.complete(visit.id, text) : await visitsApi.cancel(visit.id, text);
      notify(complete ? "Visita registrada como realizada" : "Visita cancelada");
      onDone(result);
    } catch (cause) {
      setError(toApiError(cause));
    } finally {
      setSending(false);
    }
  }

  return (
    <FormModal title={complete ? "Registrar visita realizada" : "Cancelar visita"} submitLabel={complete ? "Registrar como realizada" : "Cancelar visita"}
      sending={sending} error={error} onClose={onClose} onSubmit={() => void submit()}
      note={complete ? "Después podrás crear las evaluaciones RULA de los puestos observados en esta visita."
        : visit.cancel_by_company ? "El horario quedará libre en el calendario."
          : "La empresa verá el motivo. Si la visita se hizo, regístrala como realizada en vez de cancelarla."}>
      {complete ? (
        <TextAreaField id="completion_notes" label="Observaciones (opcional)" value={text} onChange={(e) => setText(e.target.value)}
          placeholder="Qué se observó, qué puestos se evaluaron, acuerdos con la empresa." error={error?.field("completion_notes")} />
      ) : (
        <Field id="cancellation_reason" label="Motivo de la cancelación" value={text} onChange={(e) => setText(e.target.value)}
          placeholder="Ej. Cambio de prioridades en la planta" error={error?.field("cancellation_reason")} />
      )}
    </FormModal>
  );
}

/** Abre el detalle de una visita en un modal, cargándolo por su id. */
export function VisitDetailModal({ id, onClose, onChanged }: { id: number; onClose: () => void; onChanged: (startsAt?: string) => void }) {
  const [resource, retry, refresh] = useResource((signal) => visitsApi.get(id, signal), [id]);
  return (
    <Modal title="Visita" onClose={onClose} wide>
      <div className="p-5">
        {resource.state === "loading" ? <Spinner /> : resource.state === "error" ? <ErrorState error={resource.error} onRetry={retry} /> : (
          <VisitDetailView visit={resource.data} onChanged={(_, startsAt) => { refresh(); onChanged(startsAt); }} />
        )}
      </div>
    </Modal>
  );
}
