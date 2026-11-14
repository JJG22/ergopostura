import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { CheckboxField, SelectField } from "../../components/forms";
import { FormAlert } from "../../components/Modal";
import { useNotify, usePageTitle } from "../../components/Page";
import { Button, Card, ErrorState, Field, Icon, Spinner } from "../../components/ui";
import { useForm } from "../../lib/useForm";
import { useResource } from "../../lib/useResource";
import { evaluationsApi, formatNumber, type AiSuggestion, type AssessmentForm, type AssessmentValues } from "./api";
import { ANGLE_NAMES, computeAngles, SKELETON, type Landmark, type PoseResult } from "./poseAngles";

export function AssessmentPage() {
  const id = Number(useParams().id);
  usePageTitle("Análisis RULA");
  const [resource, retry] = useResource((signal) => evaluationsApi.assessment(id, signal), [id]);
  if (resource.state === "loading") return <Spinner />;
  if (resource.state === "error") return <ErrorState error={resource.error} onRetry={retry} />;
  return <Assessment data={resource.data} />;
}

// La detección corre en el navegador: la fotografía no sale del equipo. La librería y el
// modelo se descargan solo al pedir la sugerencia, con la versión fija.
const VERSION = "0.10.14";
const CDN = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${VERSION}`;
const MODEL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";
const LABELS: Record<string, string> = {
  upper_arm_angle: "Brazo", lower_arm_angle: "Antebrazo", wrist_angle: "Muñeca", neck_angle: "Cuello", trunk_angle: "Tronco",
};

interface Detector { detect: (image: HTMLImageElement) => { landmarks?: Landmark[][] } }
let detector: Promise<Detector> | null = null;

function loadDetector(): Promise<Detector> {
  detector ??= (async () => {
    const vision = await import(/* @vite-ignore */ `${CDN}/vision_bundle.mjs`);
    const fileset = await vision.FilesetResolver.forVisionTasks(`${CDN}/wasm`);
    return (await vision.PoseLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: MODEL, delegate: "CPU" }, runningMode: "IMAGE", numPoses: 1,
    })) as Detector;
  })();
  detector.catch(() => { detector = null; });
  return detector;
}

type PoseState =
  | { state: "idle"; message?: string }
  | { state: "busy"; message: string }
  | { state: "done"; result: PoseResult; message: string; warning: boolean }
  | { state: "error"; message: string };

function Assessment({ data }: { data: AssessmentForm }) {
  const navigate = useNavigate();
  const notify = useNotify();
  const form = useForm<AssessmentValues>(data.values);
  const [photo, setPhoto] = useState<number | null>(data.photo);
  const [suggestion, setSuggestion] = useState<AiSuggestion | null>(null);
  const [suggested, setSuggested] = useState<Set<string>>(new Set());
  const [pose, setPose] = useState<PoseState>({ state: "idle" });
  const image = useRef<HTMLImageElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const back = `/evaluaciones/${data.evaluation_id}`;
  const photoUrl = data.photos.find((p) => p.id === photo)?.url ?? data.photos[0]?.url ?? "";

  const set = (name: string, value: number | boolean | string | null) => {
    form.set(name, value);
    setSuggested((current) => {
      if (!current.has(name)) return current;
      const next = new Set(current);
      next.delete(name);
      return next;
    });
  };

  // Otra fotografía invalida la sugerencia dibujada.
  useEffect(() => {
    if (canvas.current) canvas.current.hidden = true;
    if (pose.state === "done") setPose({ state: "idle", message: "Elegiste otra fotografía. Vuelve a pedir la sugerencia si la necesitas." });
  }, [photo]);

  async function suggest() {
    const img = image.current;
    if (!img) return;
    setPose({ state: "busy", message: "Cargando el modelo de detección. La primera vez puede tardar unos segundos…" });
    try {
      const [model] = await Promise.all([loadDetector(), img.complete && img.naturalWidth ? Promise.resolve() : img.decode()]);
      setPose({ state: "busy", message: "Analizando la fotografía…" });
      const found = model.detect(img).landmarks?.[0];
      if (!found) { setPose({ state: "error", message: "No se detectó a una persona en la fotografía. Registra los ángulos a mano." }); return; }
      const result = computeAngles(found, data.posture.side, img.naturalWidth, img.naturalHeight);
      if (!result.facing) { setPose({ state: "error", message: "No se pudo saber hacia dónde mira la persona. Usa una foto de perfil o mide a mano." }); return; }
      draw(result);
      const filled = new Set<string>();
      form.setValues((current) => {
        const next = { ...current };
        for (const name of ANGLE_NAMES) {
          const value = result.angles[name];
          if (value !== null) { next[name] = value; filled.add(name); }
        }
        return next;
      });
      setSuggested(filled);
      setSuggestion({ photo, side: data.posture.side, model: `mediapipe-pose-lite@${VERSION}`, frontal: result.frontal, angles: result.angles });
      setPose(result.frontal
        ? { state: "done", result, warning: true, message: "Sugerencia lista, pero la foto parece tomada de frente: los ángulos de perfil pueden no ser fiables. Mídelos a mano o usa una foto de perfil." }
        : { state: "done", result, warning: false, message: `Sugerencia lista: ${5 - result.missing.length} de 5 ángulos. Revísalos sobre la fotografía antes de guardar.` });
    } catch (error) {
      if (import.meta.env.DEV) console.error("Sugerencia de ángulos:", error);
      setPose({ state: "error", message: "No se pudo cargar el modelo. Revisa la conexión a internet o registra los ángulos a mano." });
    }
  }

  /** Dibuja el esqueleto sobre la imagen, respetando el área donde se ve (object-fit: contain). */
  function draw(result: PoseResult) {
    const img = image.current, cv = canvas.current;
    if (!img || !cv) return;
    const box = img.getBoundingClientRect();
    const scale = Math.min(box.width / img.naturalWidth, box.height / img.naturalHeight);
    const width = img.naturalWidth * scale, height = img.naturalHeight * scale;
    const left = (box.width - width) / 2, top = (box.height - height) / 2;
    const ratio = window.devicePixelRatio || 1;
    cv.width = box.width * ratio;
    cv.height = box.height * ratio;
    cv.style.width = `${box.width}px`;
    cv.style.height = `${box.height}px`;
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    ctx.scale(ratio, ratio);
    const place = (p: { x: number; y: number }) => ({ x: left + (p.x / img.naturalWidth) * width, y: top + (p.y / img.naturalHeight) * height });
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    for (const [a, b] of SKELETON) {
      const from = result.points[a], to = result.points[b];
      if (!from?.visible || !to?.visible) continue;
      const p1 = place(from), p2 = place(to);
      ctx.strokeStyle = "#2dd4bf";
      ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
    }
    for (const [name, point] of Object.entries(result.points)) {
      if (!point?.visible || name === "nose") continue;
      const at = place(point);
      ctx.fillStyle = "#f0fdfa"; ctx.strokeStyle = "#0f766e";
      ctx.beginPath(); ctx.arc(at.x, at.y, 5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    }
    cv.hidden = false;
  }

  async function save() {
    if (photo === null) return;
    const result = await form.submit((values) => evaluationsApi.saveAssessment(data.posture.id, { values, photo, ai_suggestion: suggestion }));
    if (result) {
      notify("Análisis guardado");
      navigate(`${back}#postura-${data.posture.id}`);
    }
  }

  return (
    <>
      <Link to={back} className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700 hover:underline">
        <Icon name="arrow-left" className="size-4" />Volver a la evaluación
      </Link>
      <p className="text-xs font-bold tracking-wider text-teal-700">ANÁLISIS RULA · {data.posture.side_label.toUpperCase()}</p>
      <h1 className="text-2xl font-bold">{data.posture.name}</h1>
      <p className="mb-5 mt-1 text-sm text-slate-500">Mide los ángulos sobre la fotografía y registra lo observado. El sistema calcula el resultado.</p>

      <form noValidate onSubmit={(ev) => { ev.preventDefault(); void save(); }}>
        <FormAlert error={form.error} />
        <div className="grid gap-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <div className="space-y-4 lg:sticky lg:top-20 lg:self-start">
            <Card>
              <div className="relative grid h-80 place-items-center overflow-hidden rounded-lg bg-slate-900 sm:h-96">
                <img ref={image} src={photoUrl} alt={`Fotografía analizada de ${data.posture.name}`} className="h-full w-full object-contain" />
                <canvas ref={canvas} hidden aria-hidden="true" className="pointer-events-none absolute inset-0" />
              </div>
              <div className="mt-4 rounded-lg border border-violet-200 bg-violet-50/60 p-3">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="min-w-0 flex-1">
                    <strong className="block text-sm">Sugerir ángulos con IA</strong>
                    <small className="text-slate-600">Detecta el cuerpo en la fotografía y propone los cinco ángulos del {data.posture.side_label.toLowerCase()}. Funciona mejor con una foto de perfil. La foto no sale de tu equipo.</small>
                  </div>
                  <Button type="button" variant="secondary" disabled={pose.state === "busy"} onClick={() => void suggest()}><Icon name="activity" />Sugerir</Button>
                </div>
                {pose.message ? (
                  <p role="status" aria-live="polite" className={`mt-2 text-sm ${pose.state === "error" || (pose.state === "done" && pose.warning) ? "font-medium text-red-700" : pose.state === "done" ? "text-teal-800" : "text-violet-800"}`}>{pose.message}</p>
                ) : null}
                {pose.state === "done" ? (
                  <ul className="mt-2 grid grid-cols-2 gap-1 text-sm sm:grid-cols-3">
                    {ANGLE_NAMES.map((name) => (
                      <li key={name} className="rounded bg-white px-2 py-1">
                        <span className="text-slate-500">{LABELS[name]}</span>{" "}
                        {pose.result.angles[name] === null ? <em className="text-xs">No se detectó</em> : <strong>{formatNumber(pose.result.angles[name] ?? 0)}°</strong>}
                      </li>
                    ))}
                  </ul>
                ) : null}
                <p className="mt-2 text-xs text-slate-500">Es una ayuda para medir: revisa cada valor sobre la fotografía. Giros, inclinaciones laterales, abducción y apoyos no se ven de perfil; regístralos tú.</p>
              </div>
              <fieldset className="mt-4">
                <legend className="mb-2 text-sm font-semibold">Fotografía analizada</legend>
                <div className="flex flex-wrap gap-2">
                  {data.photos.map((p, index) => (
                    <label key={p.id} className={`cursor-pointer overflow-hidden rounded-lg border-2 ${photo === p.id ? "border-teal-600" : "border-transparent"}`}>
                      <input type="radio" name="photo" value={p.id} checked={photo === p.id} onChange={() => setPhoto(p.id)} className="sr-only" />
                      <img src={p.url} alt={`Fotografía ${index + 1}`} loading="lazy" className="size-16 object-cover" />
                    </label>
                  ))}
                </div>
                {form.fieldError("photo") ? <p role="alert" className="mt-1 text-xs font-medium text-red-700">{form.fieldError("photo")}</p> : null}
              </fieldset>
            </Card>
          </div>

          <div className="space-y-4">
            {data.groups.map((group) => (
              <Card key={group.title}>
                <h2 className="mb-3 text-base font-semibold">{group.title}</h2>
                {group.fields.map((field) => {
                  const value = form.values[field.name];
                  const error = form.fieldError(field.name);
                  if (field.type === "checkbox") {
                    return <CheckboxField key={field.name} id={field.name} label={field.label} checked={value === true} onChange={(checked) => set(field.name, checked)} />;
                  }
                  if (field.type === "select") {
                    return <SelectField key={field.name} id={field.name} label={field.label} options={field.choices ?? []} value={String(value ?? "")}
                      onChange={(ev) => set(field.name, ev.target.value)} error={error} />;
                  }
                  const ai = suggested.has(field.name);
                  return (
                    <Field key={field.name} id={field.name} label={field.label} type="number" step={0.5} inputMode="decimal"
                      value={value === null || value === undefined ? "" : String(value)}
                      onChange={(ev) => set(field.name, ev.target.value === "" ? null : ev.target.value)}
                      hint={ai ? "Sugerido por la IA: revísalo sobre la fotografía." : field.help} error={error} />
                  );
                })}
              </Card>
            ))}
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2 border-t border-slate-200 pt-4">
          <Link to={back} className="inline-flex h-10 items-center rounded-lg border border-slate-300 px-4 text-sm font-semibold hover:bg-slate-50">Cancelar</Link>
          <Button type="submit" disabled={form.sending}><Icon name="activity" />{form.sending ? "Calculando…" : "Calcular y guardar"}</Button>
        </div>
      </form>
    </>
  );
}
