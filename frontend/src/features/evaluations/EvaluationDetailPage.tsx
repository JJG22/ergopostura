import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, useParams } from "react-router";

import { toApiError, type ApiError } from "../../api/client";
import { controlClass, FilePicker, Grid, SelectField } from "../../components/forms";
import { ConfirmModal, FormModal } from "../../components/Modal";
import { useNotify, usePageTitle } from "../../components/Page";
import { Badge, Button, Card, ErrorState, Field, Icon, linkButtonClass, Meta, RiskBadge, riskInk, Spinner } from "../../components/ui";
import { formatShortDate } from "../../lib/format";
import { useForm } from "../../lib/useForm";
import { useResource } from "../../lib/useResource";
import { evaluationsApi, formatNumber, type AiAdvice, type AiAdviceItem, type EvaluationDetail, type Posture, type PostureInput, type PostureResult } from "./api";
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
      <section className="mb-10 grid items-end gap-8 lg:grid-cols-[1.3fr_1fr] lg:gap-12">
        <div className="min-w-0 motion-safe:animate-[rise_480ms_cubic-bezier(0.2,0.8,0.2,1)]">
          <p className="mb-3 flex items-center gap-2.5 text-sm font-semibold text-brand-700">
            <span className="tabular">{e.code}</span>
            <Badge tone={e.status === "terminada" ? "teal" : "amber"}>{e.status_label}</Badge>
          </p>
          <h1 className="font-display text-[2.25rem] leading-[1.05] text-ink-950 sm:text-5xl">{e.position}</h1>
          <Meta items={[e.company, e.site, e.area]} />
          <div className="mt-7 flex flex-wrap gap-2">
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
        <div className="border-2 border-ink-950 bg-white p-7 motion-safe:animate-[rise_580ms_100ms_cubic-bezier(0.2,0.8,0.2,1)_backwards]">
          <p className="border-b-2 border-ink-950 pb-3 text-sm font-semibold text-ink-950">Mayor riesgo entre las posturas</p>
          {e.risk ? (
            <div className="mt-5">
              <div className="flex items-baseline gap-2">
                <strong className={`font-display text-8xl leading-none tabular ${riskInk(e.risk).text}`}>{e.risk.score}</strong>
                <span className="text-ink-500">de 7</span>
              </div>
              <div className="mt-4"><RiskBadge risk={e.risk} /></div>
              <RiskScale score={e.risk.score} />
            </div>
          ) : <p className="mt-4 text-[15px] text-ink-600">Aún no hay posturas analizadas.</p>}
        </div>
      </section>

      <Card className="mb-5">
        <h2 className="mb-3 font-display text-lg">Actividad observada</h2>
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
        <h2 className="font-display text-3xl">Posturas</h2>
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
  { from: 1, to: 2, color: "#1e7a46", pattern: "none" },
  { from: 3, to: 4, color: "#c99700", pattern: "repeating-linear-gradient(45deg, transparent 0 5px, rgb(255 255 255 / .3) 5px 7px)" },
  { from: 5, to: 6, color: "#c2531a", pattern: "repeating-linear-gradient(45deg, transparent 0 4px, rgb(255 255 255 / .28) 4px 6px), repeating-linear-gradient(-45deg, transparent 0 4px, rgb(255 255 255 / .2) 4px 6px)" },
  { from: 7, to: 7, color: "#b3121f", pattern: "repeating-linear-gradient(0deg, transparent 0 3px, rgb(255 255 255 / .25) 3px 5px)" },
] as const;

/** Escala de 1 a 7 con el puntaje marcado: muestra qué tan lejos está el puesto de lo aceptable. */
export function RiskScale({ score }: { score: number }) {
  return (
    <div role="img" aria-label={`Puntaje RULA ${score} de 7`} className="mt-5 max-w-sm">
      <div className="flex items-end gap-1 border-b-2 border-ink-950">
        {[1, 2, 3, 4, 5, 6, 7].map((n) => {
          const zone = ZONES.find((z) => n >= z.from && n <= z.to) ?? ZONES[0];
          return <span key={n} className={`flex-1 ${n === score ? "h-6" : "h-3"}`} style={{ backgroundColor: zone.color, backgroundImage: zone.pattern }} />;
        })}
      </div>
      <div className="mt-1.5 flex gap-1 text-center text-xs tabular text-ink-700" aria-hidden="true">
        {[1, 2, 3, 4, 5, 6, 7].map((n) => <span key={n} className={`flex-1 ${n === score ? "font-bold text-ink-950 underline decoration-2 underline-offset-4" : ""}`}>{n}</span>)}
      </div>
    </div>
  );
}

export function ResultSummary({ result }: { result: PostureResult }) {
  return (
    <div className="flex flex-wrap items-start gap-x-8 gap-y-4">
      <div className="flex items-baseline gap-1.5">
        <strong className={`font-display text-7xl leading-none tabular ${riskInk(result.risk).text}`}>{result.grand_score}</strong>
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
    <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3 xl:grid-cols-4">
      {SCORE_LABELS.map(([label, value]) => <Fact key={label} label={label}>{value(result.partial_scores)}</Fact>)}
      <Fact label="Método">RULA</Fact>
    </div>
  );
}

export function AiTrace({ result }: { result: PostureResult }) {
  const trace = result.ai_trace;
  if (!trace) return null;
  return (
    <div className="mt-5 border-t-2 border-ink-950 pt-4 text-sm">
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
            <tr key={row.label} className="border-t border-ink-200">
              <th scope="row" className="py-1 font-medium">{row.label}</th>
              <td>{row.suggested === null ? "No detectado" : `${formatNumber(row.suggested)}°`}</td>
              <td className={row.changed ? "font-semibold text-brand-800" : ""}>{formatNumber(row.registered)}°{row.changed ? " (corregido)" : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const PRIORITY_TONE = { alta: "red", media: "amber", baja: "neutral" } as const;

/**
 * Segunda opinión de la IA: mira la fotografía analizada y el resultado RULA y propone
 * recomendaciones para el puesto. Ninguna se guarda sola; el ingeniero elige cuáles usa.
 */
function AiAdvicePanel({ posture, advice, onUse, refresh }: {
  posture: Posture; advice: AiAdvice | null; onUse: (item: AiAdviceItem) => void; refresh: () => void;
}) {
  const [state, setState] = useState<{ sending: boolean; error: string | null }>({ sending: false, error: null });
  const used = new Set(posture.recommendations.map((r) => r.text));

  async function ask() {
    setState({ sending: true, error: null });
    try {
      await evaluationsApi.requestAdvice(posture.id);
      setState({ sending: false, error: null });
      refresh();
    } catch (cause) {
      setState({ sending: false, error: toApiError(cause).message });
    }
  }

  const button = (
    <Button type="button" variant={advice ? "ghost" : "secondary"} disabled={state.sending} onClick={() => void ask()}>
      <Icon name="activity" />{state.sending ? "La IA está revisando…" : advice ? "Pedir de nuevo" : "Pedir recomendaciones a la IA"}
    </Button>
  );

  return (
    <section aria-labelledby={`ia-${posture.id}`} className="mb-4 border-l-4 border-brand-700 bg-ink-50 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h5 id={`ia-${posture.id}`} className="text-sm font-semibold text-ink-900">Recomendaciones de la IA</h5>
        {advice ? button : null}
      </div>
      {state.sending ? <p role="status" className="mt-2 text-sm text-ink-600">Revisando la fotografía y el resultado. Tarda entre 10 y 40 segundos.</p> : null}
      {state.error ? <p role="alert" className="mt-2 text-sm font-medium text-red-700">{state.error}</p> : null}
      {!advice ? (
        <div className="mt-1">
          <p className="mb-3 text-sm text-ink-600">La IA (Claude, de Anthropic) recibe la fotografía analizada y el resultado RULA, y propone recomendaciones para el puesto. Tú decides cuáles usar.</p>
          {button}
        </div>
      ) : (
        <>
          {advice.stale ? (
            <p className="mt-2 border border-ink-950 bg-white px-3 py-2 text-sm text-ink-900">El análisis cambió después de pedirlas. Pídelas de nuevo para que correspondan al resultado actual.</p>
          ) : null}
          {advice.observations ? <p className="mt-2 text-sm text-ink-700">{advice.observations}</p> : null}
          {advice.caution ? <p className="mt-2 text-sm font-medium text-ink-900">Ojo: {advice.caution}</p> : null}
          <ul className="mt-3 space-y-2">
            {advice.items.map((item, index) => (
              <li key={index} className="flex flex-wrap items-start gap-3 bg-white px-3 py-2.5 text-sm ring-1 ring-ink-500/10">
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex flex-wrap gap-1.5">
                    <Badge tone={PRIORITY_TONE[item.priority]}>Prioridad {item.priority}</Badge>
                    <Badge>{item.kind_label}</Badge>
                    <Badge>{item.focus_label}</Badge>
                  </div>
                  <p>{item.text}</p>
                </div>
                {used.has(item.text) ? <Badge tone="teal">Agregada</Badge> : (
                  <Button type="button" variant="ghost" onClick={() => onUse(item)}><Icon name="plus" />Usar</Button>
                )}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-ink-500">Sugerencias de IA ({advice.model}). Revísalas con tu criterio antes de usarlas.</p>
        </>
      )}
    </section>
  );
}

function PostureCard({ number, posture, canEdit, refresh, onEdit, onDelete }: {
  number: number; posture: Posture; canEdit: boolean; refresh: () => void; onEdit: () => void; onDelete: () => void;
}) {
  const notify = useNotify();
  const fileRef = useRef<HTMLInputElement>(null);
  const [upload, setUpload] = useState<{ sending: boolean; error: string | null }>({ sending: false, error: null });
  const [pickerKey, setPickerKey] = useState(0);
  const [text, setText] = useState("");
  const [fromAi, setFromAi] = useState(false);
  const recRef = useRef<HTMLTextAreaElement>(null);
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
      setPickerKey((k) => k + 1);
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
      await evaluationsApi.addRecommendation(posture.id, text, fromAi);
      setText("");
      setFromAi(false);
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
        <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-ink-950 font-display text-base text-white tabular">{number}</span>
        <div className="min-w-0 flex-1">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="font-display text-2xl">{posture.name}</h3>
              <p className="text-sm text-ink-500">{posture.side_label}, {formatNumber(posture.duration_value)} {posture.duration_unit_label.toLowerCase()} en la postura</p>
            </div>
            {canEdit ? (
              <div className="flex gap-1">
                <Button variant="ghost" onClick={onEdit}>Editar</Button>
                <Button variant="dangerGhost" onClick={onDelete}>Eliminar</Button>
              </div>
            ) : null}
          </div>

          <div className="grid gap-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-10">
          <div className="min-w-0">
          <h4 className="mb-3 text-sm font-semibold text-ink-700">Evidencia</h4>
          {posture.photos.length ? (
            <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-2">
              {posture.photos.map((photo) => (
                <figure key={photo.id} className="relative overflow-hidden rounded-2xl bg-ink-100 ring-1 ring-ink-500/10">
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
              <div className="min-w-56 flex-1 text-sm">
                <span className="mb-1.5 block font-medium text-ink-700">Agregar fotografía (JPG, PNG o WEBP, hasta 10 MB)</span>
                <FilePicker key={pickerKey} id={`foto-${posture.id}`} name="photo" inputRef={fileRef} accept="image/jpeg,image/png,image/webp" button="Elegir fotografía" />
              </div>
              <Button type="submit" variant="secondary" disabled={upload.sending}><Icon name="cloud-upload" />{upload.sending ? "Subiendo…" : "Subir"}</Button>
            </form>
          ) : null}
          {upload.error ? <p role="alert" className="text-sm font-medium text-red-700">{upload.error}</p> : null}

          </div>
          <div className="min-w-0 lg:border-l lg:border-ink-500/10 lg:pl-10">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h4 className="text-sm font-semibold text-ink-700">Resultado RULA</h4>
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
                    <li key={r.id} className="flex items-start gap-3 rounded-2xl bg-ink-500/[0.05] px-4 py-3 text-sm">
                      <b className="tabular text-brand-700">{i + 1}</b><p className="flex-1">{r.text}</p>
                      {r.from_ai ? <Badge>Con apoyo de IA</Badge> : null}
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
                <AiAdvicePanel posture={posture} advice={result.ai_advice} refresh={refresh}
                  onUse={(item) => { setText(item.text); setFromAi(true); setRecError(null); recRef.current?.focus(); }} />
              ) : null}
              {canEdit ? (
                <form onSubmit={(ev) => void addRecommendation(ev)} className="flex flex-wrap items-end gap-2">
                  <label className="min-w-56 flex-1 text-sm">
                    <span className="mb-1 block font-medium text-ink-700">{fromAi ? "Nueva recomendación (tomada de la IA; ajústala si hace falta)" : "Nueva recomendación"}</span>
                    <textarea ref={recRef} rows={2} value={text} onChange={(ev) => { setText(ev.target.value); if (!ev.target.value.trim()) setFromAi(false); }} placeholder="Qué mejorar en el puesto, según lo observado"
                      aria-invalid={recError ? true : undefined} className={`py-2 ${controlClass(recError ?? undefined)}`} />
                  </label>
                  <Button type="submit" variant="secondary"><Icon name="plus" />Agregar</Button>
                </form>
              ) : null}
              {recError ? <p role="alert" className="mt-1 text-sm font-medium text-red-700">{recError}</p> : null}
            </>
          ) : (
            <p className="rounded-2xl bg-ink-500/[0.05] p-4 text-sm text-ink-600">{canEdit ? "Agrega una fotografía y haz el análisis para ver el resultado." : "Sin análisis."}</p>
          )}
          </div>
          </div>
        </div>
      </section>
    </Card>
  );
}
