import type { ReactNode } from "react";

import { dashboardApi } from "../api/endpoints";
import type { CompanyDashboard, Contract, Dashboard, EngineerDashboard, Evaluation, SupportDashboard, Visit } from "../api/types";
import { Badge, Card, ContractBadge, EmptyText, ErrorState, Icon, linkButtonClass, RiskBadge, SectionHead, Spinner } from "../components/ui";
import { formatDay, formatLongDate, formatShortDate, formatTime, plural } from "../lib/format";
import { useResource } from "../lib/useResource";
import { AppLink } from "../components/AppLink";
import { usePageTitle } from "../components/Page";

export function DashboardPage() {
  usePageTitle("Panel principal");
  const [resource, retry] = useResource((signal) => dashboardApi.get(signal));
  if (resource.state === "loading") return <Spinner />;
  if (resource.state === "error") return <ErrorState error={resource.error} onRetry={retry} />;
  return <DashboardView data={resource.data} />;
}

function DashboardView({ data }: { data: Dashboard }) {
  // La unión está discriminada por rol: si se agrega un rol, TypeScript exige su panel.
  switch (data.role) {
    case "admin":
      return <SupportPanel data={data} />;
    case "ingeniero":
      return <EngineerPanel data={data} />;
    case "empresa":
      return <CompanyPanel data={data} />;
  }
}

function Head({ data, subtitle }: { data: Dashboard; subtitle: string }) {
  return (
    <div className="mb-8">
      <p className="mb-2 text-sm text-ink-500"><time dateTime={data.today}>{formatLongDate(data.today)}</time></p>
      <h1 className="font-display text-[2rem] font-bold leading-tight text-ink-950">{data.greeting}, {data.display_name}</h1>
      {subtitle ? <p className="mt-1.5 max-w-2xl text-[15px] text-ink-500">{subtitle}</p> : null}
    </div>
  );
}

/** Indicadores en una sola franja: se leen de corrido, como un tablero, y no como tarjetas sueltas. */
function Metrics({ children, columns }: { children: ReactNode; columns: 3 | 4 }) {
  return (
    <div className={`mb-6 grid gap-px overflow-hidden rounded-lg border border-ink-200 bg-ink-200 ${columns === 4 ? "grid-cols-2 lg:grid-cols-4" : "grid-cols-1 sm:grid-cols-3"}`}>
      {children}
    </div>
  );
}

function Metric({ label, value, detail, href, alert = false }: { label: string; value: number; detail?: string; href?: string; alert?: boolean }) {
  const content = (
    <>
      <p className="flex items-center gap-2 pr-5 text-sm font-medium text-ink-600">
        {alert ? <span className="size-2 rounded-full bg-red-600" aria-hidden="true" /> : null}
        {label}
      </p>
      <p className={`mt-3 font-display text-[2rem] font-bold leading-none tabular sm:text-[2.5rem] ${alert ? "text-red-700" : "text-ink-950"}`}>{value}</p>
      {detail ? <p className="mt-2 text-xs text-ink-500">{detail}</p> : null}
    </>
  );
  const box = "group relative min-w-0 bg-white p-4 sm:p-5";
  return href ? (
    <AppLink href={href} className={`${box} transition-colors hover:bg-ink-50`}>
      {content}
      <Icon name="chevron-right" className="absolute right-4 top-5 size-4 text-ink-300 transition-transform group-hover:translate-x-0.5 group-hover:text-brand-700" />
    </AppLink>
  ) : <div className={box}>{content}</div>;
}

function Row({ icon, leaf, title, detail, aside }: { icon?: string; leaf?: ReactNode; title: string; detail: string; aside?: ReactNode }) {
  return (
    <li className="flex flex-wrap items-center gap-x-3.5 gap-y-2 border-t border-ink-100 py-3 first:border-t-0 first:pt-0 sm:flex-nowrap">
      {leaf ?? <span className="grid size-10 shrink-0 place-items-center rounded-md border border-ink-200 text-ink-500"><Icon name={icon ?? "file-text"} className="size-4" /></span>}
      <div className="min-w-0 flex-1 basis-[calc(100%-3.5rem)] sm:basis-auto">
        <p className="truncate text-sm font-semibold">{title}</p>
        <p className="truncate text-xs text-ink-500">{detail}</p>
      </div>
      {aside ? <div className="ml-[3.375rem] sm:ml-0">{aside}</div> : null}
    </li>
  );
}

function VisitRow({ visit }: { visit: Visit }) {
  return (
    <Row leaf={<DateLeaf iso={visit.starts_at} />} title={visit.company}
      detail={`${formatDay(visit.starts_at)}, ${formatTime(visit.starts_at)} a ${formatTime(visit.ends_at)}, ${visit.site}`}
      aside={<div className="flex items-center gap-2"><Badge tone={visit.level.tone} dot>{visit.level.label}</Badge><AppLink className={linkButtonClass()} href={visit.url}>Ver</AppLink></div>} />
  );
}

const leafDay = new Intl.DateTimeFormat("es-CO", { timeZone: "America/Bogota", day: "numeric" });
const leafMonth = new Intl.DateTimeFormat("es-CO", { timeZone: "America/Bogota", month: "short" });

/** Hoja de calendario: el día se reconoce de un vistazo en la lista de visitas. */
function DateLeaf({ iso }: { iso: string }) {
  const date = new Date(iso);
  return (
    <span className="flex w-10 shrink-0 flex-col items-center overflow-hidden rounded-md border border-ink-200 bg-white" aria-hidden="true">
      <span className="w-full bg-ink-100 py-px text-center text-[10px] font-semibold text-ink-600">{leafMonth.format(date).replace(".", "")}</span>
      <span className="py-0.5 font-display text-base font-bold leading-tight tabular text-ink-950">{leafDay.format(date)}</span>
    </span>
  );
}

function ContractRow({ contract }: { contract: Contract }) {
  return (
    <Row icon="file-signature" title={contract.company} detail={`El contrato ${contract.code} vence el ${formatLongDate(contract.end_date)}`}
      aside={<AppLink className={linkButtonClass()} href={contract.url}>Ver</AppLink>} />
  );
}

function EvaluationsCard({ evaluations }: { evaluations: Evaluation[] }) {
  return (
    <Card className="mt-6">
      <SectionHead title="Evaluaciones recientes" subtitle="Últimos registros ergonómicos"
        action={<AppLink className={linkButtonClass()} href={"/evaluaciones/"}>Ver todas</AppLink>} />
      {evaluations.length === 0 ? <EmptyText>Aún no hay evaluaciones.</EmptyText> : (
        <div className="relative -mx-5 overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm [&_td]:whitespace-nowrap">
            <thead className="border-y border-ink-200 bg-ink-50/70 text-xs text-ink-500">
              <tr><th scope="col" className="px-5 py-2.5 font-medium">Evaluación</th><th scope="col" className="px-3 font-medium">Empresa</th><th scope="col" className="px-3 font-medium">Puesto y área</th><th scope="col" className="px-3 font-medium">Fecha</th><th scope="col" className="px-3 font-medium">Riesgo</th><th scope="col" className="px-5 font-medium">Estado</th></tr>
            </thead>
            <tbody className="[&>tr]:transition-colors [&>tr:hover]:bg-ink-50/60">
              {evaluations.map((evaluation) => (
                <tr key={evaluation.id} className="border-t border-ink-100 first:border-t-0">
                  <td className="px-5 py-3 font-semibold tabular"><AppLink className="text-brand-700 hover:underline" href={evaluation.url}>{evaluation.code}</AppLink></td>
                  <td className="px-3">{evaluation.company}</td>
                  <td className="px-3"><span className="block text-ink-950">{evaluation.position}</span><span className="text-xs text-ink-500">{evaluation.area}</span></td>
                  <td className="px-3 tabular text-ink-600">{formatShortDate(evaluation.evaluated_on)}</td>
                  <td className="px-3"><RiskBadge risk={evaluation.risk} /></td>
                  <td className="px-5"><Badge tone={evaluation.status === "terminada" ? "teal" : "amber"}>{evaluation.status_label}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function SupportPanel({ data }: { data: SupportDashboard }) {
  return (
    <>
      <Head data={data} subtitle="Gestionas las cuentas y el mantenimiento. Las evaluaciones, visitas y contratos son del ingeniero y de las empresas." />
      {!data.has_engineer ? (
        <AppLink href={"/usuarios/nuevo/"} className="mb-6 flex items-center gap-4 rounded-lg bg-brand-700 p-5 text-white transition-colors hover:bg-brand-800">
          <Icon name="user-plus" />
          <div className="flex-1"><p className="font-semibold">Crea la cuenta del ingeniero industrial</p><p className="text-sm text-brand-100">Es el primer paso: el ingeniero registra después sus empresas cliente y les da acceso.</p></div>
          <Icon name="chevron-right" />
        </AppLink>
      ) : null}
      <Metrics columns={3}>
        {data.users_by_role.map((row) => <Metric key={row.role} label={row.label} value={row.total} detail={plural(row.total, "cuenta activa", "cuentas activas")} />)}
      </Metrics>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionHead title="Cuentas recientes" subtitle="Últimas creadas" action={<AppLink className={linkButtonClass()} href={"/usuarios/"}>Gestionar</AppLink>} />
          <ul>
            {data.recent_accounts.map((account) => (
              <Row key={account.id} icon="users" title={account.full_name}
                detail={account.company ? `${account.role_label}, ${account.company.name}` : account.role_label}
                aside={!account.is_active ? <Badge>Desactivada</Badge> : account.must_change_password ? <Badge tone="amber">Clave temporal</Badge> : undefined} />
            ))}
          </ul>
        </Card>
        <Card>
          <SectionHead title="Estado del sistema" subtitle="Configuración del servidor" />
          <ul>
            <Row icon="sparkles" title="Lectura de contratos con IA"
              detail={data.ai_ready ? "Configurada (ANTHROPIC_API_KEY)." : "Sin configurar: falta ANTHROPIC_API_KEY."}
              aside={<Badge tone={data.ai_ready ? "teal" : "amber"}>{data.ai_ready ? "Activa" : "Pendiente"}</Badge>} />
            <Row icon="shield-check" title="Panel técnico" detail="Consulta de datos para diagnóstico." aside={<AppLink className={linkButtonClass()} href={"/admin/"}>Abrir</AppLink>} />
          </ul>
        </Card>
      </div>
    </>
  );
}

function EngineerPanel({ data }: { data: EngineerDashboard }) {
  const active = data.contract_counts.vigente + data.contract_counts.por_vencer;
  return (
    <>
      <Head data={data} subtitle="Tus empresas cliente, sus visitas y las evaluaciones pendientes." />
      {data.onboarding ? (
        <Card className="mb-6 border-l-4 border-l-brand-700">
          <SectionHead title="Primeros pasos" subtitle="Así se presta el servicio en ErgoPostura" />
          <ol className="space-y-2.5">
            {data.steps.map((step, index) => (
              <li key={step.label} className={`flex items-center gap-3 text-sm ${step.done ? "text-ink-400 line-through" : "text-ink-700"}`}>
                <span className={`grid size-7 shrink-0 place-items-center rounded-full border-2 text-xs font-bold tabular ${step.done ? "border-brand-700 bg-brand-700 text-white" : "border-ink-200 text-ink-600"}`}>
                  {step.done ? <Icon name="check" className="size-3.5" /> : index + 1}
                </span>
                {step.label}
              </li>
            ))}
          </ol>
        </Card>
      ) : null}
      <Metrics columns={4}>
        <Metric label="Empresas" value={data.totals.companies} detail={plural(data.totals.positions, "puesto registrado", "puestos registrados")} href="/empresas/" />
        <Metric label="Contratos vigentes" value={active} detail={data.contract_counts.por_vencer ? `${data.contract_counts.por_vencer} por vencer` : "Ninguno por vencer"} href="/contratos/?estado=vigente" />
        <Metric label="Visitas por cerrar" value={data.to_close_count} detail="Registra si se hicieron" href="/visitas/agenda/?ver=por_cerrar" alert={data.to_close_count > 0} />
        <Metric label="Evaluaciones en curso" value={data.drafts_count} detail="Por terminar" href="/tareas/" />
      </Metrics>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionHead title="Visitas" subtitle="Agendadas por las empresas" action={<AppLink className={linkButtonClass()} href={"/visitas/"}>Calendario</AppLink>} />
          {data.to_close.length + data.upcoming_visits.length === 0 ? <EmptyText>No hay visitas programadas.</EmptyText> : (
            <ul>{[...data.to_close, ...data.upcoming_visits].map((visit) => <VisitRow key={visit.id} visit={visit} />)}</ul>
          )}
        </Card>
        <Card>
          <SectionHead title="Requiere tu atención" subtitle="Contratos por vencer y visitas sin evaluar" />
          {data.expiring_contracts.length + data.without_evaluation.length === 0 ? <EmptyText>Todo al día.</EmptyText> : (
            <ul>
              {data.expiring_contracts.map((contract) => <ContractRow key={contract.id} contract={contract} />)}
              {data.without_evaluation.map((visit) => (
                <Row key={visit.id} icon="clipboard-check" title={visit.company} detail={`Visita del ${formatDay(visit.starts_at)} sin evaluación`}
                  aside={<AppLink className={linkButtonClass()} href={`/evaluaciones/nueva/?visita=${visit.id}`}>Evaluar</AppLink>} />
              ))}
            </ul>
          )}
        </Card>
      </div>
      <EvaluationsCard evaluations={data.recent_evaluations} />
    </>
  );
}

function CompanyPanel({ data }: { data: CompanyDashboard }) {
  const { contract } = data;
  return (
    <>
      <Head data={data} subtitle={data.company?.name ?? ""} />
      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionHead title="Contrato de servicio" subtitle="Con el ingeniero industrial" />
          {contract ? (
            <div className="space-y-2">
              <ContractBadge status={contract.status} label={contract.status_label} />
              <p className="font-semibold">{contract.code} <span className="font-normal text-ink-500">{contract.kind_label}</span></p>
              <p className="text-sm text-ink-500">Del {formatLongDate(contract.start_date)} al {formatLongDate(contract.end_date)}</p>
              {contract.status === "por_vencer" ? <p className="text-sm text-amber-800">Vence en {plural(contract.days_left, "día", "días")}. Habla con el ingeniero si quieres renovarlo.</p> : null}
              <AppLink className={linkButtonClass()} href={contract.url}>Ver contrato</AppLink>
            </div>
          ) : (
            <EmptyText>No hay un contrato vigente. Sin contrato no se pueden agendar visitas: comunícate con el ingeniero.</EmptyText>
          )}
        </Card>
        <div className="grid gap-3">
          {[
            { href: "/visitas/", icon: "calendar-days", title: "Agendar una visita", detail: "Elige el día y la hora en el calendario", main: true },
            { href: "/evaluaciones/", icon: "clipboard-check", title: "Ver resultados", detail: "Evaluaciones terminadas de tus puestos", main: false },
            { href: "/tareas/", icon: "layout-list", title: "Recomendaciones por atender", detail: plural(data.pending_count, "pendiente", "pendientes"), main: false },
          ].map((link) => (
            <AppLink key={link.href} href={link.href}
              className={`group flex items-center gap-4 rounded-lg p-4 transition-colors ${link.main ? "bg-brand-700 text-white hover:bg-brand-800" : "border border-ink-200 bg-white hover:border-ink-300 hover:bg-ink-50"}`}>
              <Icon name={link.icon} />
              <div className="flex-1"><p className="font-semibold">{link.title}</p><p className={`text-sm ${link.main ? "text-brand-100" : "text-ink-500"}`}>{link.detail}</p></div>
              <Icon name="chevron-right" className="size-4.5 transition-transform group-hover:translate-x-0.5" />
            </AppLink>
          ))}
        </div>
      </div>
      {data.counts ? (
        <Metrics columns={4}>
          <Metric label="Sedes" value={data.counts.sites} />
          <Metric label="Áreas" value={data.counts.areas} />
          <Metric label="Puestos" value={data.counts.positions} />
          <Metric label="Trabajadores" value={data.counts.workers} />
        </Metrics>
      ) : null}
      <Card>
        <SectionHead title="Próximas visitas" subtitle="Las siguientes en el calendario" action={<AppLink className={linkButtonClass()} href={"/visitas/"}>Ver todas</AppLink>} />
        {data.upcoming_visits.length === 0 ? <EmptyText>No hay visitas programadas.</EmptyText> : <ul>{data.upcoming_visits.map((visit) => <VisitRow key={visit.id} visit={visit} />)}</ul>}
      </Card>
      <EvaluationsCard evaluations={data.recent_evaluations} />
    </>
  );
}
