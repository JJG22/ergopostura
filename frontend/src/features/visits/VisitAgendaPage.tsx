import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";

import { usePageTitle } from "../../components/Page";
import { EmptyState, Pagination } from "../../components/Table";
import { Card, ErrorState, Icon, Spinner } from "../../components/ui";
import { formatDay, formatTime } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { colorOf, visitsApi, type AgendaTab } from "./api";
import { LevelBadge, VisitsHeader } from "./VisitsCalendarPage";
import { VisitDetailModal, VisitDetailView, VisitFormModal } from "./VisitModals";

const TABS: { value: AgendaTab; label: string }[] = [
  { value: "proximas", label: "Próximas" },
  { value: "por_cerrar", label: "Por cerrar" },
  { value: "historial", label: "Historial" },
];

const EMPTY: Record<AgendaTab, string> = {
  proximas: "No hay visitas programadas",
  por_cerrar: "No hay visitas por cerrar",
  historial: "Aún no hay visitas realizadas o canceladas",
};

/** Lista de visitas en orden, para quien prefiere leerlas que verlas en el calendario. */
export function VisitAgendaPage() {
  usePageTitle("Agenda de visitas");
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab = (params.get("ver") ?? "proximas") as AgendaTab;
  const page = Number(params.get("pagina") ?? "1") || 1;
  const [resource, retry, refresh] = useResource((signal) => visitsApi.agenda({ tab, page }, signal), [tab, page]);
  const [open, setOpen] = useState<number | null>(null);
  const [scheduling, setScheduling] = useState(false);

  if (resource.state === "loading") return <Spinner />;
  if (resource.state === "error") return <ErrorState error={resource.error} onRetry={retry} />;
  const data = resource.data;
  const tabs = TABS.filter((t) => t.value !== "por_cerrar" || data.attends);

  return (
    <>
      <VisitsHeader info={data} onSchedule={() => setScheduling(true)} />
      <Card>
        <div className="-mx-5 -mt-1 mb-2 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-5">
          <div className="flex overflow-x-auto">
            {tabs.map((t) => (
              <button key={t.value} type="button" onClick={() => setParams(t.value === "proximas" ? {} : { ver: t.value })}
                aria-current={data.tab === t.value ? "page" : undefined}
                className={`-mb-px border-b-2 px-3 py-2.5 text-sm font-semibold whitespace-nowrap ${data.tab === t.value ? "border-teal-700 text-teal-800" : "border-transparent text-slate-500 hover:text-slate-800"}`}>
                {t.label}
              </button>
            ))}
          </div>
          <Link to="/visitas" className="inline-flex items-center gap-1.5 py-2 text-sm font-semibold text-teal-700 hover:underline">
            <Icon name="calendar-days" className="size-4" />Ver calendario
          </Link>
        </div>
        {data.results.length === 0 ? <EmptyState icon="calendar-days" title={EMPTY[data.tab]} /> : (
          <ul className="divide-y divide-slate-100">
            {data.results.map((visit) => (
              <li key={visit.id}>
                <button type="button" onClick={() => setOpen(visit.id)} className="flex w-full flex-wrap items-center gap-3 px-1 py-3 text-left hover:bg-slate-50">
                  <span className="h-10 w-1 shrink-0 rounded-full" style={{ background: colorOf(visit.color).fg }} aria-hidden="true" />
                  <span className="min-w-0 flex-1">
                    <strong className="block truncate text-sm">{visit.company.name}</strong>
                    <small className="block text-slate-500">{formatDay(visit.starts_at)} · {formatTime(visit.starts_at)} – {formatTime(visit.ends_at)}</small>
                    <small className="block truncate text-slate-500">{visit.site} · {visit.municipality} · recibe {visit.contact_name}</small>
                  </span>
                  <LevelBadge level={visit.level} />
                </button>
              </li>
            ))}
          </ul>
        )}
        <Pagination page={data} noun="visitas" onPage={(next) => setParams({ ...(data.tab !== "proximas" ? { ver: data.tab } : {}), ...(next > 1 ? { pagina: String(next) } : {}) })} />
      </Card>
      {open !== null ? <VisitDetailModal id={open} onClose={() => setOpen(null)} onChanged={refresh} /> : null}
      {scheduling ? (
        <VisitFormModal onClose={() => setScheduling(false)} onSaved={(startsAt) => navigate(`/visitas?fecha=${startsAt.slice(0, 10)}`)} />
      ) : null}
    </>
  );
}

/** Página propia de una visita, para enlaces directos (por ejemplo, desde el panel). */
export function VisitPage() {
  const id = Number(useParams().id);
  usePageTitle("Visita");
  const [resource, retry, refresh] = useResource((signal) => visitsApi.get(id, signal), [id]);
  if (resource.state === "loading") return <Spinner />;
  if (resource.state === "error") return <ErrorState error={resource.error} onRetry={retry} />;
  const visit = resource.data;
  return (
    <div className="mx-auto max-w-2xl">
      <Link to={`/visitas?fecha=${visit.starts_at.slice(0, 10)}`} className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700 hover:underline">
        <Icon name="arrow-left" className="size-4" />Volver al calendario
      </Link>
      <Card><VisitDetailView visit={visit} onChanged={refresh} /></Card>
    </div>
  );
}
