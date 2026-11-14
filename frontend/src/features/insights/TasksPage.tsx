import { useState } from "react";
import { Link, useSearchParams } from "react-router";

import { api, toApiError, withQuery } from "../../api/client";
import type { Risk } from "../../api/types";
import { useNotify, usePageTitle } from "../../components/Page";
import { EmptyState, PageHead, Pagination, SearchBar, Table, type Page } from "../../components/Table";
import { Badge, Button, Card, ErrorState, SectionHead, Spinner, RiskBadge } from "../../components/ui";
import { formatInstantDate } from "../../lib/format";
import { useResource } from "../../lib/useResource";

interface Task {
  id: number;
  text: string;
  posture: string;
  company: string;
  position: string;
  evaluation: { id: number | null; code: string };
  risk: Risk | null;
  attended_at: string | null;
  attended_by: string | null;
}

interface Tasks extends Page<Task> {
  view: "pendientes" | "atendidas";
  shows_recommendations: boolean;
  can_attend: boolean;
  manages_evaluations: boolean;
  in_progress: { id: number; code: string; company: string; position: string; problems: string[] }[];
}

export function TasksPage() {
  usePageTitle("Tareas pendientes");
  const notify = useNotify();
  const [params, setParams] = useSearchParams();
  const attended = params.get("ver") === "atendidas";
  const q = params.get("q") ?? "";
  const page = Number(params.get("pagina") ?? "1") || 1;
  const [resource, retry, refresh] = useResource(
    (signal) => api<Tasks>(withQuery("/tasks/", { view: attended ? "atendidas" : "", q, page }), { signal }), [attended, q, page]);
  const [error, setError] = useState<string | null>(null);

  const go = (next: { ver?: string; q?: string; pagina?: number }) => {
    const values = { ver: attended ? "atendidas" : "", q, ...next, pagina: next.pagina && next.pagina > 1 ? String(next.pagina) : "" };
    setParams(Object.fromEntries(Object.entries(values).filter(([, v]) => v)) as Record<string, string>);
  };

  async function toggle(task: Task) {
    setError(null);
    try {
      await api(`/tasks/${task.id}/attend/`, { method: "POST", body: { attended: !attended } });
      notify(attended ? "Recomendación pendiente de nuevo" : "Recomendación atendida");
      refresh();
    } catch (cause) {
      setError(toApiError(cause).message);
    }
  }

  const head = <PageHead title="Tareas pendientes" subtitle="Consulta las actividades pendientes del proceso de evaluación." />;
  if (resource.state === "loading") return <>{head}<Spinner /></>;
  if (resource.state === "error") return <>{head}<ErrorState error={resource.error} onRetry={retry} /></>;
  const data = resource.data;

  return (
    <>
      {head}
      {data.manages_evaluations ? (
        <Card className="mb-5">
          <SectionHead title="Mis evaluaciones en curso" subtitle="Lo que falta para terminarlas" />
          {data.in_progress.length === 0 ? <EmptyState icon="check" title="No tienes evaluaciones en curso" /> : (
            <Table head={["Evaluación", "Empresa y puesto", "Qué falta"]}>
              {data.in_progress.map((item) => (
                <tr key={item.id}>
                  <td className="px-5 py-3"><Link to={`/evaluaciones/${item.id}`} className="font-semibold hover:text-teal-700">{item.code}</Link></td>
                  <td className="px-5 py-3"><strong className="block">{item.company}</strong><small className="text-slate-500">{item.position}</small></td>
                  <td className="px-5 py-3">
                    {item.problems.length ? (
                      <ul className="ml-4 list-disc text-sm text-amber-800">{item.problems.map((p) => <li key={p}>{p}</li>)}</ul>
                    ) : <Badge tone="teal">Lista para terminar</Badge>}
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </Card>
      ) : null}

      {data.shows_recommendations ? (
        <Card>
          <div className="-mx-5 -mt-1 mb-4 flex border-b border-slate-200 px-5">
            {([["", "Por atender"], ["atendidas", "Atendidas"]] as const).map(([value, label]) => (
              <button key={label} type="button" onClick={() => go({ ver: value, pagina: 1 })}
                aria-current={(value === "atendidas") === attended ? "page" : undefined}
                className={`-mb-px border-b-2 px-3 py-2.5 text-sm font-semibold ${(value === "atendidas") === attended ? "border-teal-700 text-teal-800" : "border-transparent text-slate-500 hover:text-slate-800"}`}>
                {label}
              </button>
            ))}
          </div>
          <SearchBar key={`${attended}|${q}`} query={q} label="Buscar tareas" placeholder="Buscar tarea, empresa o puesto" onSearch={(text) => go({ q: text })} />
          {error ? <p role="alert" className="mb-3 text-sm font-medium text-red-700">{error}</p> : null}
          {data.results.length === 0 ? (
            <EmptyState icon="layout-list" title={q ? "No hay resultados" : attended ? "Aún no hay recomendaciones atendidas" : "No hay recomendaciones por atender"} />
          ) : (
            <>
              <Table head={["Tarea", "Empresa y puesto", "Evaluación relacionada", "Riesgo", attended ? "Atendida" : "Estado", ...(data.can_attend ? [""] : [])]}>
                {data.results.map((task) => (
                  <tr key={task.id}>
                    <td className="max-w-xs px-5 py-3"><strong className="block">{task.text}</strong><small className="text-slate-500">{task.posture}</small></td>
                    <td className="px-5 py-3"><strong className="block">{task.company}</strong><small className="text-slate-500">{task.position}</small></td>
                    <td className="px-5 py-3">
                      {task.evaluation.id !== null ? <Link to={`/evaluaciones/${task.evaluation.id}`} className="text-teal-700 hover:underline">{task.evaluation.code}</Link> : task.evaluation.code}
                    </td>
                    <td className="px-5 py-3"><RiskBadge risk={task.risk} /></td>
                    <td className="px-5 py-3">
                      {attended && task.attended_at ? (
                        <><strong className="block">{formatInstantDate(task.attended_at)}</strong><small className="text-slate-500">{task.attended_by ?? ""}</small></>
                      ) : <Badge tone="amber">Pendiente</Badge>}
                    </td>
                    {data.can_attend ? (
                      <td className="px-5 py-3 text-right">
                        <Button variant={attended ? "ghost" : "secondary"} onClick={() => void toggle(task)}>{attended ? "Marcar pendiente" : "Marcar atendida"}</Button>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </Table>
              <Pagination page={data} noun="tareas" onPage={(next) => go({ pagina: next })} />
            </>
          )}
        </Card>
      ) : null}
    </>
  );
}
