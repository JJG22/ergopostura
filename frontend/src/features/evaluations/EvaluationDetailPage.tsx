import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, useParams } from "react-router";

import { toApiError, type ApiError } from "../../api/client";
import { controlClass, Grid, SelectField } from "../../components/forms";
import { ConfirmModal, FormModal } from "../../components/Modal";
import { useNotify, usePageTitle } from "../../components/Page";
import { Badge, Button, Card, ErrorState, Field, Icon, linkButtonClass, Meta, RISK_COLORS, RiskBadge, Spinner } from "../../components/ui";
import { formatShortDate } from "../../lib/format";
import { useForm } from "../../lib/useForm";
import { useResource } from "../../lib/useResource";
import { evaluationsApi, formatNumber, type EvaluationDetail, type Posture, type PostureInput, type PostureResult } from "./api";
import { EvaluationFormModal } from "./EvaluationsPage";

export function EvaluationDetailPage() {
  const id = Number(useParams().id);
  const [resource, retry, refresh] = useResource((signal) => evaluationsApi.get(id, signal), [id]);
  usePageTitle(resource.state === "ready" ? resource.data.code : "Evaluación");
  if (resource.state === "loading") return <Spinner />;
  if (resource.state === "error") return <ErrorState error={resource.error} onRetry={retry} />;
  return <Detail evaluation={resource.data} refresh={refresh} />;
}

type Dialog =
  | { type: "edit" }
  | { type: "posture"; posture?: Posture }
  | { type: "confirm"; title: string; message: string; label: string; danger: boolean; action: () => Promise<unknown>; done: string }
  | null;

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0 border-t border-ink-200 pt-2.5">
      <small className="block text-xs font-medium text-ink-500">{label}</small>
      <span className="mt-0.5 block text-sm text-ink-950">{children}</span>
    </div>
  );
}

function Detail({ evaluation, refresh }: { evaluation: EvaluationDetail; refresh: () => void }) {
  const notify = useNotify();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [busy, setBusy] = useState<{ sending: boolean; error: ApiError | null }>({ sending: false, error: null });
  const close = () => { setDialog(null); setBusy({ sending: false, error: null }); };

  async function confirm(action: () => Promise<unknown>, done: string) {
    setBusy({ sending: true, error: null });
    try {
      await action();
      notify(done);
      close();
      refresh();
    } catch (cause) {
      setBusy({ sending: false, error: toApiError(cause) });
    }
  }

  const e = evaluation;
  return (
    <>
      <Link to="/evaluaciones" className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700 hover:underline">
        <Icon name="arrow-left" className="size-4" />Volver a evaluaciones
      </Link>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="mb-1.5 flex items-center gap-2.5 text-sm font-semibold text-brand-700">
            <span className="tabular">{e.code}</span>
            <Badge tone={e.status === "terminada" ? "teal" : "amber"}>{e.status_label}</Badge>
          </p>
          <h1 className="font-display text-[1.75rem] font-bold leading-tight text-ink-950">{e.position}</h1>
          <Meta items={[e.company, e.site, e.area]} />
        </div>
        <div className="flex flex-wrap gap-2">
          {e.can_edit ? <Button variant="secondary" onClick={() => setDialog({ type: "edit" })}>Editar datos</Button> : null}
          {e.status === "terminada" ? <Link to={`/evaluaciones/${e.id}/informe`} className={linkButtonClass("secondary")}><Icon name="file-text" />Ver informe</Link> : null}
          {e.can_reopen ? (
            <Button variant="secondary" onClick={() => setDialog({
              type: "confirm", title: "Reabrir evaluación", label: "Reabrir", danger: false, done: "Evaluación reabierta",
              message: "Volverá a estar en curso y la empresa dejará de verla hasta que la termines de nuevo.",
              action: () => evaluationsApi.reopen(e.id),
            })}>Reabrir</Button>
          ) : null}
        </div>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-3 rounded-lg border border-ink-200 bg-white px-4 py-3 text-sm text-ink-600">
        <span>Mayor riesgo entre las posturas</span><RiskBadge risk={e.risk} />
      </div>

      <Card className="mb-5">
        <h2 className="mb-2 text-[15px] font-semibold">Actividad observada</h2>
        <p className="whitespace-pre-line text-sm text-ink-800">{e.activity_description}</p>
        {e.worker_context ? <p className="mt-2 whitespace-pre-line text-sm text-ink-600">{e.worker_context}</p> : null}
        <div className="mt-5 grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
          <Fact label="Fecha">{formatShortDate(e.evaluated_on)}</Fact>
          <Fact label="Ingeniero">{e.evaluator}</Fact>
          <Fact label="Visita"><Link className="text-brand-700 hover:underline" to={`/visitas/${e.visit.id}`}>{formatShortDate(e.visit.date)}</Link></Fact>
          {e.worker ? <Fact label="Trabajador observado">{e.worker.full_name}</Fact> : null}
          <Fact label="Carga">{e.carries_load ? `Sí, ${e.load_weight_kg !== null ? `${formatNumber(e.load_weight_kg)} kg` : "peso no conocido"}` : "No"}</Fact>
          <Fact label="Movimientos repetitivos">{e.repetitive_movements ? `Sí${e.repetition_notes ? `: ${e.repetition_notes}` : ""}` : "No"}</Fact>
        </div>
      </Card>

      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-display text-xl font-bold">Posturas</h2>
        {e.can_edit ? <Button variant="secondary" onClick={() => setDialog({ type: "posture" })}><Icon name="plus" />Agregar postura</Button> : null}
      </div>
      {e.postures.length === 0 ? (
        <Card className="mb-5 py-10 text-center">
          <p className="font-semibold">Aún no hay posturas</p>
          {e.can_edit ? <p className="text-sm text-ink-500">Agrega la primera postura que vas a evaluar.</p> : null}
        </Card>
      ) : e.postures.map((posture, index) => (
        <PostureCard key={posture.id} number={index + 1} posture={posture} canEdit={e.can_edit} refresh={refresh}
          onEdit={() => setDialog({ type: "posture", posture })}
          onDelete={() => setDialog({
            type: "confirm", title: "Eliminar postura", label: "Eliminar", danger: true, done: "Postura eliminada",
            message: `¿Eliminar «${posture.name}» con sus fotografías, análisis y recomendaciones?`,
            action: () => evaluationsApi.deletePosture(posture.id),
          })} />
      ))}

      {e.can_edit ? (
        <Card className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <strong>Terminar evaluación</strong>
            {e.completion_problems.length ? (
              <ul className="ml-5 mt-1 list-disc text-sm text-amber-800">{e.completion_problems.map((p) => <li key={p}>{p}</li>)}</ul>
            ) : <p className="text-sm text-ink-500">Todo está completo. Al terminar ya no podrás modificarla.</p>}
          </div>
          <Button disabled={e.completion_problems.length > 0} onClick={() => setDialog({
            type: "confirm", title: "Terminar evaluación", label: "Terminar", danger: false, done: "Evaluación terminada",
            message: "¿Terminar la evaluación? Ya no podrás modificarla y la empresa podrá ver el resultado.",
            action: () => evaluationsApi.complete(e.id),
          })}><Icon name="check" />Terminar</Button>
        </Card>
      ) : null}

      {dialog?.type === "edit" ? <EvaluationFormModal evaluation={e} onClose={close} onSaved={() => { close(); refresh(); }} /> : null}
      {dialog?.type === "posture" ? (
        <PostureFormModal evaluation={e} {...(dialog.posture ? { posture: dialog.posture } : {})} onClose={close} onSaved={() => { close(); refresh(); }} />
      ) : null}
      {dialog?.type === "confirm" ? (
        <ConfirmModal title={dialog.title} message={dialog.message} confirmLabel={dialog.label} danger={dialog.danger}
          sending={busy.sending} error={busy.error} onClose={close} onConfirm={() => void confirm(dialog.action, dialog.done)} />
      ) : null}
    </>
  );
}

function PostureFormModal({ evaluation, posture, onClose, onSaved }: {
  evaluation: EvaluationDetail; posture?: Posture; onClose: () => void; onSaved: () => void;
}) {
  const notify = useNotify();
  const form = useForm<PostureInput>(posture
    ? { name: posture.name, side: posture.side, duration_value: String(posture.duration_value), duration_unit: posture.duration_unit }
    : { name: "", side: "derecho", duration_value: "", duration_unit: "minutos" });
  const { values, set } = form;

  async function save() {
    const result = await form.submit((input) => (posture ? evaluationsApi.updatePosture(posture.id, input) : evaluationsApi.addPosture(evaluation.id, input)));
    if (result) {
      notify(posture ? "Cambios guardados" : "Postura agregada");
      onSaved();
    }
  }

  return (
    <FormModal title={posture ? "Editar postura" : "Agregar postura"} sending={form.sending} error={form.error} onClose={onClose} onSubmit={() => void save()}>
      <Field id="name" label="Nombre de la postura" placeholder="Ej. Empaque en banda" value={values.name}
        onChange={(ev) => set("name", ev.target.value)} error={form.fieldError("name")} />
      <SelectField id="side" label="Lado evaluado" options={evaluation.posture_options.sides} value={values.side} hint="RULA evalúa un lado a la vez."
        onChange={(ev) => set("side", ev.target.value)} error={form.fieldError("side")} />
      <Grid>
        <Field id="duration_value" label="Tiempo en la postura" type="number" min={0} step={0.01} inputMode="decimal" value={values.duration_value}
          onChange={(ev) => set("duration_value", ev.target.value)} error={form.fieldError("duration_value")} />
        <SelectField id="duration_unit" label="Unidad de tiempo" options={evaluation.posture_options.units} value={values.duration_unit}
          onChange={(ev) => set("duration_unit", ev.target.value)} error={form.fieldError("duration_unit")} />
      </Grid>
    </FormModal>
  );
}

const SCORE_LABELS: [string, (s: Record<string, number>) => string][] = [
  ["Brazo", (s) => `${s.upper_arm}`], ["Antebrazo", (s) => `${s.lower_arm}`], ["Muñeca", (s) => `${s.wrist}`],
  ["Giro de muñeca", (s) => `${s.wrist_twist}`], ["Músculo y carga A", (s) => `+${s.muscle_a} / +${s.load_a}`],
  ["Puntaje C", (s) => `${s.score_c}`], ["Cuello", (s) => `${s.neck}`], ["Tronco", (s) => `${s.trunk}`],
  ["Piernas", (s) => `${s.legs}`], ["Músculo y carga B", (s) => `+${s.muscle_b} / +${s.load_b}`], ["Puntaje D", (s) => `${s.score_d}`],
];

/** Zonas de la escala RULA (puntaje final de 1 a 7) y su nivel de acción. */
const ZONES = [
  { from: 1, to: 2, color: "bg-emerald-500" },
  { from: 3, to: 4, color: "bg-amber-400" },
  { from: 5, to: 6, color: "bg-orange-500" },
  { from: 7, to: 7, color: "bg-red-600" },
] as const;

/** Escala de 1 a 7 con el puntaje marcado: muestra qué tan lejos está el puesto de lo aceptable. */
export function RiskScale({ score }: { score: number }) {
  return (
    <div role="img" aria-label={`Puntaje RULA ${score} de 7`} className="mt-4 max-w-sm">
      <div className="flex items-end gap-1">
        {[1, 2, 3, 4, 5, 6, 7].map((n) => {
          const zone = ZONES.find((z) => n >= z.from && n <= z.to) ?? ZONES[0];
          return <span key={n} className={`flex-1 rounded-sm ${zone.color} ${n === score ? "h-3.5" : "h-2 opacity-25"}`} />;
        })}
      </div>
      <div className="mt-1.5 flex gap-1 text-center text-[11px] tabular text-ink-400" aria-hidden="true">
        {[1, 2, 3, 4, 5, 6, 7].map((n) => <span key={n} className={`flex-1 ${n === score ? "font-bold text-ink-950" : ""}`}>{n}</span>)}
      </div>
    </div>
  );
}

export function ResultSummary({ result }: { result: PostureResult }) {
  return (
    <div className="flex flex-wrap items-start gap-x-8 gap-y-4">
      <div className="flex items-baseline gap-1.5">
        <strong className={`font-display text-6xl font-bold leading-none tabular ${RISK_COLORS[result.risk.traffic_light].text}`}>{result.grand_score}</strong>
        <span className="text-sm text-ink-500">de 7</span>
      </div>
      <div className="min-w-60 flex-1">
        <RiskBadge risk={result.risk} />
        <p className="mt-1.5 text-sm text-ink-600">{result.description}</p>
        <RiskScale score={result.grand_score} />
      </div>
    </div>
  );
}

export function ScoreGrid({ result }: { result: PostureResult }) {
  return (
    <div className="grid gap-x-6 gap-y-4 sm:grid-cols-3 lg:grid-cols-4">
      {SCORE_LABELS.map(([label, value]) => <Fact key={label} label={label}>{value(result.partial_scores)}</Fact>)}
      <Fact label="Método">RULA</Fact>
    </div>
  );
}

export function AiTrace({ result }: { result: PostureResult }) {
  const trace = result.ai_trace;
  if (!trace) return null;
  return (
    <div className="mt-4 rounded-lg border border-violet-200 bg-violet-50/60 p-3 text-sm">
      <p className="mb-2 text-ink-700">
        <strong>Ángulos medidos con apoyo de IA.</strong> La detección de pose propuso estos valores
        {trace.on_other_photo ? " sobre otra fotografía de la postura" : ""} y el evaluador registró los de la derecha.
        El puntaje se calcula solo con los valores registrados.
        {trace.frontal ? " La fotografía parecía tomada de frente, así que la sugerencia era poco fiable." : ""}
      </p>
      <table className="w-full text-left">
        <thead className="text-xs text-ink-500"><tr><th scope="col" className="py-1">Ángulo</th><th scope="col">Sugerido</th><th scope="col">Registrado</th></tr></thead>
        <tbody>
          {trace.rows.map((row) => (
            <tr key={row.label} className="border-t border-violet-100">
              <th scope="row" className="py-1 font-medium">{row.label}</th>
              <td>{row.suggested === null ? "No detectado" : `${formatNumber(row.suggested)}°`}</td>
              <td className={row.changed ? "font-semibold text-violet-800" : ""}>{formatNumber(row.registered)}°{row.changed ? " (corregido)" : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PostureCard({ number, posture, canEdit, refresh, onEdit, onDelete }: {
  number: number; posture: Posture; canEdit: boolean; refresh: () => void; onEdit: () => void; onDelete: () => void;
}) {
  const notify = useNotify();
  const fileRef = useRef<HTMLInputElement>(null);
  const [upload, setUpload] = useState<{ sending: boolean; error: string | null }>({ sending: false, error: null });
  const [text, setText] = useState("");
  const [recError, setRecError] = useState<string | null>(null);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const result = posture.result;

  async function sendPhoto(event: FormEvent) {
    event.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) { setUpload({ sending: false, error: "Elige una fotografía." }); return; }
    setUpload({ sending: true, error: null });
    try {
      await evaluationsApi.uploadPhoto(posture.id, file);
      if (fileRef.current) fileRef.current.value = "";
      notify("Fotografía agregada");
      setUpload({ sending: false, error: null });
      refresh();
    } catch (cause) {
      setUpload({ sending: false, error: toApiError(cause).message });
    }
  }

  async function removePhoto(id: number) {
    setPhotoError(null);
    try {
      await evaluationsApi.deletePhoto(id);
      notify("Fotografía eliminada");
      refresh();
    } catch (cause) {
      setPhotoError(toApiError(cause).message);
    }
  }

  async function addRecommendation(event: FormEvent) {
    event.preventDefault();
    setRecError(null);
    try {
      await evaluationsApi.addRecommendation(posture.id, text);
      setText("");
      notify("Recomendación agregada");
      refresh();
    } catch (cause) {
      const error = toApiError(cause);
      setRecError(error.field("text") ?? error.message);
    }
  }

  async function removeRecommendation(id: number) {
    await evaluationsApi.deleteRecommendation(id);
    notify("Recomendación eliminada");
    refresh();
  }

  return (
    <Card className="mb-5" >
      <section id={`postura-${posture.id}`} className="flex gap-4">
        <span className="grid size-8 shrink-0 place-items-center rounded-md bg-ink-950 font-display text-sm font-bold text-white tabular">{number}</span>
        <div className="min-w-0 flex-1">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="font-display text-lg font-bold">{posture.name}</h3>
              <p className="text-sm text-ink-500">{posture.side_label}, {formatNumber(posture.duration_value)} {posture.duration_unit_label.toLowerCase()} en la postura</p>
            </div>
            {canEdit ? (
              <div className="flex gap-1">
                <Button variant="ghost" onClick={onEdit}>Editar</Button>
                <Button variant="dangerGhost" onClick={onDelete}>Eliminar</Button>
              </div>
            ) : null}
          </div>

          <h4 className="mb-2 text-sm font-semibold">Evidencia</h4>
          {posture.photos.length ? (
            <div className="mb-3 grid grid-cols-3 gap-2 sm:grid-cols-5">
              {posture.photos.map((photo) => (
                <figure key={photo.id} className="relative overflow-hidden rounded-lg border border-ink-200 bg-ink-100">
                  <a href={photo.url} target="_blank" rel="noopener"><img src={photo.url} alt={`Evidencia de ${posture.name}`} loading="lazy" className="aspect-square w-full object-cover" /></a>
                  {result?.photo_id === photo.id ? <figcaption className="absolute bottom-1 left-1"><Badge tone="teal">Analizada</Badge></figcaption> : null}
                  {canEdit ? (
                    <button type="button" aria-label="Eliminar fotografía" onClick={() => void removePhoto(photo.id)}
                      className="absolute right-1 top-1 rounded-md bg-white/95 p-1 text-ink-700 ring-1 ring-ink-200 hover:text-red-700"><Icon name="x" className="size-4" /></button>
                  ) : null}
                </figure>
              ))}
            </div>
          ) : !canEdit ? <p className="mb-3 text-sm text-ink-500">Sin fotografías.</p> : null}
          {photoError ? <p role="alert" className="mb-3 text-sm font-medium text-red-700">{photoError}</p> : null}
          {canEdit ? (
            <form onSubmit={(ev) => void sendPhoto(ev)} className="mb-2 flex flex-wrap items-end gap-2">
              <label className="min-w-56 flex-1 text-sm">
                <span className="mb-1 block font-medium text-ink-700">Agregar fotografía (JPG, PNG o WEBP, hasta 10 MB)</span>
                <input ref={fileRef} type="file" name="photo" accept="image/jpeg,image/png,image/webp" className="w-full rounded-md border border-ink-200 bg-white px-3 py-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-ink-100 file:px-2.5 file:py-1 file:text-sm file:font-medium file:text-ink-800" />
              </label>
              <Button type="submit" variant="secondary" disabled={upload.sending}><Icon name="cloud-upload" />{upload.sending ? "Subiendo…" : "Subir"}</Button>
            </form>
          ) : null}
          {upload.error ? <p role="alert" className="text-sm font-medium text-red-700">{upload.error}</p> : null}

          <hr className="my-5 border-ink-100" />
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h4 className="text-sm font-semibold">Resultado RULA</h4>
            {canEdit && posture.photos.length ? (
              <Link to={`/evaluaciones/posturas/${posture.id}/analisis`} className={linkButtonClass("primary")}>{result ? "Repetir análisis" : "Hacer análisis"}</Link>
            ) : null}
          </div>
          {result ? (
            <>
              <ResultSummary result={result} />
              <div className="mt-4"><ScoreGrid result={result} /></div>
              <AiTrace result={result} />
              <hr className="my-5 border-ink-100" />
              <h4 className="mb-2 text-sm font-semibold">Recomendaciones</h4>
              {posture.recommendations.length === 0 ? <p className="text-sm text-ink-500">Aún no hay recomendaciones.</p> : (
                <ol className="mb-3 space-y-2">
                  {posture.recommendations.map((r, i) => (
                    <li key={r.id} className="flex items-start gap-3 rounded-md border border-ink-200 px-3 py-2.5 text-sm">
                      <b className="tabular text-brand-700">{i + 1}</b><p className="flex-1">{r.text}</p>
                      {r.attended ? <Badge tone="teal">Atendida</Badge> : null}
                      {canEdit ? (
                        <button type="button" aria-label="Eliminar recomendación" onClick={() => void removeRecommendation(r.id)}
                          className="rounded p-0.5 text-ink-500 hover:text-red-700"><Icon name="x" className="size-4" /></button>
                      ) : null}
                    </li>
                  ))}
                </ol>
              )}
              {canEdit ? (
                <form onSubmit={(ev) => void addRecommendation(ev)} className="flex flex-wrap items-end gap-2">
                  <label className="min-w-56 flex-1 text-sm">
                    <span className="mb-1 block font-medium text-ink-700">Nueva recomendación</span>
                    <textarea rows={2} value={text} onChange={(ev) => setText(ev.target.value)} placeholder="Qué mejorar en el puesto, según lo observado"
                      aria-invalid={recError ? true : undefined} className={`py-2 ${controlClass(recError ?? undefined)}`} />
                  </label>
                  <Button type="submit" variant="secondary"><Icon name="plus" />Agregar</Button>
                </form>
              ) : null}
              {recError ? <p role="alert" className="mt-1 text-sm font-medium text-red-700">{recError}</p> : null}
            </>
          ) : (
            <p className="text-sm text-ink-500">{canEdit ? "Agrega una fotografía y haz el análisis para ver el resultado." : "Sin análisis."}</p>
          )}
        </div>
      </section>
    </Card>
  );
}
