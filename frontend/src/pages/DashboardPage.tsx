import type { ReactNode } from "react";

import { dashboardApi } from "../api/endpoints";
import type { CompanyDashboard, Contract, Dashboard, EngineerDashboard, Evaluation, SupportDashboard, Visit } from "../api/types";
import { Badge, Card, ContractBadge, EmptyText, ErrorState, Icon, linkButtonClass, RiskBadge, SectionHead, Spinner } from "../components/ui";
import { formatDay, formatLongDate, formatShortDate, formatTime, legacyUrl, plural } from "../lib/format";
import { useResource } from "../lib/useResource";

export function DashboardPage() {
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
    <div className="mb-6">
      <p className="text-xs font-bold uppercase tracking-wider text-teal-700">{formatLongDate(data.today)}</p>
      <h1 className="text-2xl font-bold">{data.greeting}, {data.display_name}</h1>
      <p className="text-slate-500">{subtitle}</p>
    </div>
  );
}

function Metric({ label, value, detail, href, alert = false }: { label: string; value: number; detail?: string; href?: string; alert?: boolean }) {
  const content = (
    <>
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className={`my-1 text-3xl font-bold ${alert ? "text-red-700" : ""}`}>{value}</p>
      {detail ? <p className="text-xs text-slate-500">{detail}</p> : null}
    </>
  );
  const box = "min-w-0 rounded-xl border border-slate-200 bg-white p-5 shadow-sm";
  return href ? <a href={legacyUrl(href)} className={`${box} transition hover:border-teal-300`}>{content}</a> : <div className={box}>{content}</div>;
}

function Row({ icon, title, detail, aside }: { icon: string; title: string; detail: string; aside?: ReactNode }) {
  return (
    <li className="flex items-center gap-3 border-t border-slate-100 py-3 first:border-t-0">
      <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-600"><Icon name={icon} className="size-4" /></span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold">{title}</p>
        <p className="truncate text-xs text-slate-500">{detail}</p>
      </div>
      {aside}
    </li>
  );
}

function VisitRow({ visit }: { visit: Visit }) {
  return (
    <Row icon="calendar-days" title={visit.company}
      detail={`${formatDay(visit.starts_at)} · ${formatTime(visit.starts_at)} – ${formatTime(visit.ends_at)} · ${visit.site}`}
      aside={<div className="flex items-center gap-2"><Badge tone={visit.level.tone} dot>{visit.level.label}</Badge><a className={linkButtonClass()} href={legacyUrl(visit.legacy_url)}>Ver</a></div>} />
  );
}

function ContractRow({ contract }: { contract: Contract }) {
  return (
    <Row icon="file-signature" title={contract.company} detail={`El contrato ${contract.code} vence el ${formatLongDate(contract.end_date)}`}
      aside={<a className={linkButtonClass()} href={legacyUrl(contract.legacy_url)}>Ver</a>} />
  );
}

function EvaluationsCard({ evaluations }: { evaluations: Evaluation[] }) {
  return (
    <Card className="mt-6">
      <SectionHead title="Evaluaciones recientes" subtitle="Últimos registros ergonómicos"
        action={<a className={linkButtonClass()} href={legacyUrl("/evaluaciones/")}>Ver todas</a>} />
      {evaluations.length === 0 ? <EmptyText>Aún no hay evaluaciones.</EmptyText> : (
        <div className="-mx-5 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr><th className="px-5 py-2.5">Evaluación</th><th className="px-3">Empresa</th><th className="px-3">Área y puesto</th><th className="px-3">Fecha</th><th className="px-3">Riesgo</th><th className="px-5">Estado</th></tr>
            </thead>
            <tbody>
              {evaluations.map((evaluation) => (
                <tr key={evaluation.id} className="border-t border-slate-100">
                  <td className="px-5 py-3 font-semibold"><a className="hover:text-teal-700" href={legacyUrl(evaluation.legacy_url)}>{evaluation.code}</a></td>
                  <td className="px-3">{evaluation.company}</td>
                  <td className="px-3">{evaluation.area} · {evaluation.position}</td>
                  <td className="px-3">{formatShortDate(evaluation.evaluated_on)}</td>
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
        <a href={legacyUrl("/usuarios/nuevo/")} className="mb-6 flex items-center gap-4 rounded-xl bg-teal-700 p-5 text-white shadow-sm hover:bg-teal-800">
          <Icon name="user-plus" />
          <div className="flex-1"><p className="font-semibold">Crea la cuenta del ingeniero industrial</p><p className="text-sm text-teal-50/80">Es el primer paso: el ingeniero registra después sus empresas cliente y les da acceso.</p></div>
          <Icon name="chevron-right" />
        </a>
      ) : null}
      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        {data.users_by_role.map((row) => <Metric key={row.role} label={row.label} value={row.total} detail={plural(row.total, "cuenta activa", "cuentas activas")} />)}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionHead title="Cuentas recientes" subtitle="Últimas creadas" action={<a className={linkButtonClass()} href={legacyUrl("/usuarios/")}>Gestionar</a>} />
          <ul>
            {data.recent_accounts.map((account) => (
              <Row key={account.id} icon="users" title={account.full_name}
                detail={`${account.role_label}${account.company ? ` · ${account.company.name}` : ""}`}
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
            <Row icon="shield-check" title="Panel técnico" detail="Consulta de datos para diagnóstico." aside={<a className={linkButtonClass()} href={legacyUrl("/admin/")}>Abrir</a>} />
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
        <Card className="mb-6 border-teal-200 bg-gradient-to-b from-teal-50 to-white">
          <SectionHead title="Primeros pasos" subtitle="Así se presta el servicio en ErgoPostura" />
          <ol className="space-y-2.5">
            {data.steps.map((step, index) => (
              <li key={step.label} className={`flex items-center gap-3 text-sm ${step.done ? "text-slate-400 line-through" : "text-slate-700"}`}>
                <span className={`grid size-7 shrink-0 place-items-center rounded-full border-2 text-xs font-bold ${step.done ? "border-teal-700 bg-teal-700 text-white" : "border-teal-200 text-teal-700"}`}>
                  {step.done ? <Icon name="check" className="size-3.5" /> : index + 1}
                </span>
                {step.label}
              </li>
            ))}
          </ol>
        </Card>
      ) : null}
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Empresas" value={data.totals.companies} detail={plural(data.totals.positions, "puesto registrado", "puestos registrados")} href="/empresas/" />
        <Metric label="Contratos vigentes" value={active} detail={data.contract_counts.por_vencer ? `${data.contract_counts.por_vencer} por vencer` : "Ninguno por vencer"} href="/contratos/?estado=vigente" />
        <Metric label="Visitas por cerrar" value={data.to_close_count} detail="Registra si se hicieron" href="/visitas/agenda/?ver=por_cerrar" alert={data.to_close_count > 0} />
        <Metric label="Evaluaciones en curso" value={data.drafts_count} detail="Por terminar" href="/tareas/" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionHead title="Visitas" subtitle="Agendadas por las empresas" action={<a className={linkButtonClass()} href={legacyUrl("/visitas/")}>Calendario</a>} />
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
                  aside={<a className={linkButtonClass()} href={legacyUrl(`/evaluaciones/nueva/?visita=${visit.id}`)}>Evaluar</a>} />
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
              <p className="font-semibold">{contract.code} · {contract.kind_label}</p>
              <p className="text-sm text-slate-500">Del {formatLongDate(contract.start_date)} al {formatLongDate(contract.end_date)}</p>
              {contract.status === "por_vencer" ? <p className="text-sm text-amber-800">Vence en {plural(contract.days_left, "día", "días")}. Habla con el ingeniero si quieres renovarlo.</p> : null}
              <a className={linkButtonClass()} href={legacyUrl(contract.legacy_url)}>Ver contrato</a>
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
            <a key={link.href} href={legacyUrl(link.href)}
              className={`flex items-center gap-4 rounded-xl p-4 shadow-sm ${link.main ? "bg-teal-700 text-white hover:bg-teal-800" : "border border-slate-200 bg-white hover:border-teal-300"}`}>
              <Icon name={link.icon} />
              <div className="flex-1"><p className="font-semibold">{link.title}</p><p className={`text-sm ${link.main ? "text-teal-50/80" : "text-slate-500"}`}>{link.detail}</p></div>
              <Icon name="chevron-right" />
            </a>
          ))}
        </div>
      </div>
      {data.counts ? (
        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Sedes" value={data.counts.sites} />
          <Metric label="Áreas" value={data.counts.areas} />
          <Metric label="Puestos" value={data.counts.positions} />
          <Metric label="Trabajadores" value={data.counts.workers} />
        </div>
      ) : null}
      <Card>
        <SectionHead title="Próximas visitas" subtitle="Las siguientes en el calendario" action={<a className={linkButtonClass()} href={legacyUrl("/visitas/")}>Ver todas</a>} />
        {data.upcoming_visits.length === 0 ? <EmptyText>No hay visitas programadas.</EmptyText> : <ul>{data.upcoming_visits.map((visit) => <VisitRow key={visit.id} visit={visit} />)}</ul>}
      </Card>
      <EvaluationsCard evaluations={data.recent_evaluations} />
    </>
  );
}
