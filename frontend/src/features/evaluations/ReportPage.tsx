import { Link, useParams } from "react-router";

import { usePageTitle } from "../../components/Page";
import { Badge, Button, ErrorState, Icon, RiskBadge, Spinner } from "../../components/ui";
import { formatInstantDate, formatShortDate } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { evaluationsApi, formatNumber, type EvaluationDetail } from "./api";
import { AiTrace, ResultSummary } from "./EvaluationDetailPage";

/** Informe para imprimir o guardar como PDF (RF-028). Solo de evaluaciones terminadas. */
export function ReportPage() {
  const id = Number(useParams().id);
  const [resource, retry] = useResource((signal) => evaluationsApi.get(id, signal), [id]);
  usePageTitle(resource.state === "ready" ? `Informe ${resource.data.code}` : "Informe");
  if (resource.state === "loading") return <Spinner />;
  if (resource.state === "error") return <ErrorState error={resource.error} onRetry={retry} />;
  if (resource.data.status !== "terminada") {
    return <p className="text-sm text-slate-600">El informe está disponible cuando la evaluación está terminada. <Link className="text-teal-700" to={`/evaluaciones/${id}`}>Volver</Link></p>;
  }
  return <Report e={resource.data} />;
}

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return <span className="block"><small className="block text-[11px] font-bold tracking-wider text-slate-500">{label}</small>{children}</span>;
}

function Report({ e }: { e: EvaluationDetail }) {
  const method = e.postures[0]?.result?.method ?? "RULA";
  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link to={`/evaluaciones/${e.id}`} className="inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700 hover:underline">
          <Icon name="arrow-left" className="size-4" />Volver a la evaluación
        </Link>
        <Button onClick={() => window.print()}><Icon name="download" />Imprimir o guardar PDF</Button>
      </div>
      <article className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm print:border-0 print:p-0 print:shadow-none">
        <header className="mb-6 flex items-center gap-2.5">
          <span className="grid size-8 place-items-center rounded-lg bg-teal-700 text-white"><Icon name="activity" /></span>
          <strong className="flex-1">ErgoPostura</strong>
          <Badge tone="teal">{e.code}</Badge>
        </header>
        <h1 className="text-2xl font-bold">Informe de evaluación ergonómica</h1>
        <p className="mb-5 text-slate-600">{e.company} · NIT {e.company_nit}</p>
        <div className="mb-6 grid gap-3 rounded-lg bg-slate-50 p-4 text-sm sm:grid-cols-3">
          <Item label="SEDE">{e.site}</Item><Item label="ÁREA">{e.area}</Item><Item label="PUESTO">{e.position}</Item>
          <Item label="FECHA">{formatShortDate(e.evaluated_on)}</Item><Item label="INGENIERO">{e.evaluator}</Item>
          <Item label="VISITA">{formatShortDate(e.visit.date)}</Item>
          {e.worker ? <Item label="TRABAJADOR">{e.worker.full_name}</Item> : null}
          <Item label="MAYOR RIESGO"><RiskBadge risk={e.risk} /></Item>
        </div>
        <h2 className="mb-1 text-lg font-semibold">Actividad observada</h2>
        <p className="whitespace-pre-line text-sm">{e.activity_description}</p>
        {e.worker_context ? <p className="mt-1 whitespace-pre-line text-sm text-slate-600">{e.worker_context}</p> : null}
        <p className="mt-2 text-sm">
          Carga: {e.carries_load ? `sí, ${e.load_weight_kg !== null ? `${formatNumber(e.load_weight_kg)} kg` : "peso no conocido"}` : "no"}.{" "}
          Movimientos repetitivos: {e.repetitive_movements ? `sí${e.repetition_notes ? `, ${e.repetition_notes}` : ""}` : "no"}.
        </p>

        {e.postures.map((posture, index) => {
          const result = posture.result;
          if (!result) return null;
          const s = result.partial_scores;
          const photo = posture.photos.find((p) => p.id === result.photo_id);
          const rows: [string, string, string, string][] = [
            ["Brazo", `${s.upper_arm}`, "Cuello", `${s.neck}`], ["Antebrazo", `${s.lower_arm}`, "Tronco", `${s.trunk}`],
            ["Muñeca", `${s.wrist}`, "Piernas", `${s.legs}`], ["Giro de muñeca", `${s.wrist_twist}`, "Músculo y carga B", `+${s.muscle_b} / +${s.load_b}`],
            ["Músculo y carga A", `+${s.muscle_a} / +${s.load_a}`, "Puntaje D", `${s.score_d}`], ["Puntaje C", `${s.score_c}`, "Puntaje final", `${result.grand_score}`],
          ];
          return (
            <section key={posture.id} className="mt-8 break-inside-avoid border-t border-slate-200 pt-6">
              <h2 className="text-lg font-semibold">Postura {index + 1}: {posture.name}</h2>
              <p className="mb-4 text-sm text-slate-600">{posture.side_label} · {formatNumber(posture.duration_value)} {posture.duration_unit_label.toLowerCase()} en la postura</p>
              <div className="grid gap-5 sm:grid-cols-[14rem_1fr]">
                {photo ? <img src={photo.url} alt={`Fotografía analizada de ${posture.name}`} className="w-full rounded-lg border border-slate-200 object-contain" /> : <span />}
                <div>
                  <ResultSummary result={result} />
                  <table className="mt-4 w-full text-sm">
                    <tbody>
                      {rows.map(([a, av, b, bv]) => (
                        <tr key={a} className="border-b border-slate-100">
                          <th scope="row" className="py-1.5 pr-2 text-left font-medium text-slate-600">{a}</th><td className="pr-4">{av}</td>
                          <th scope="row" className="py-1.5 pr-2 text-left font-medium text-slate-600">{b}</th><td>{bv}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <AiTrace result={result} />
                </div>
              </div>
              <h3 className="mb-1 mt-4 font-semibold">Recomendaciones</h3>
              {posture.recommendations.length ? (
                <ol className="ml-5 list-decimal text-sm">{posture.recommendations.map((r) => <li key={r.id}>{r.text}</li>)}</ol>
              ) : <p className="text-sm text-slate-600">Sin recomendaciones: la postura es aceptable si no se mantiene ni se repite durante periodos largos.</p>}
            </section>
          );
        })}
        <footer className="mt-8 border-t border-slate-200 pt-4 text-xs text-slate-500">
          Método: {method}. RULA es una guía para priorizar la investigación de los puestos y no reemplaza el criterio profesional.
          {e.completed_at ? ` Evaluación terminada el ${formatInstantDate(e.completed_at)}.` : ""}
        </footer>
      </article>
    </div>
  );
}
