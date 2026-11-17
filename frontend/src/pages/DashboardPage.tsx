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

/** Une frases cortas como en español: «a, b y c». */
function sentence(parts: string[]): string {
  if (parts.length <= 1) return parts[0] ?? "";
  return `${parts.slice(0, -1).join(", ")} y ${parts[parts.length - 1]}`;
}

/**
 * Portada del panel: saludo, resumen del día en una frase y las acciones principales a la
 * izquierda, sobre el campo azul; a la derecha, la hoja blanca con lo más importante para el rol.
 */
function Hero({ data, summary, actions, feature }: { data: Dashboard; summary: ReactNode; actions: ReactNode; feature: ReactNode }) {
  return (
    <section className="-mt-10 mb-12 ml-[calc(50%-50vw)] w-screen bg-brand-700 text-white sm:-mt-14">
      <div className="mx-auto grid max-w-7xl items-end gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[1.25fr_1fr] lg:gap-14 lg:px-8 lg:py-16">
        <div className="motion-safe:animate-[rise_520ms_cubic-bezier(0.2,0.8,0.2,1)]">
          <h1 className="font-display text-[2.8rem] leading-[0.98] sm:text-7xl">
            {data.greeting},<br />{data.display_name}
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-white/85"><time dateTime={data.today}>{formatLongDate(data.today)}</time>. {summary}</p>
          <div className="mt-8 flex flex-wrap items-center gap-3">{actions}</div>
        </div>
        <div className="text-ink-950 motion-safe:animate-[rise_620ms_100ms_cubic-bezier(0.2,0.8,0.2,1)_backwards]">{feature}</div>
      </div>
    </section>
  );
}

function Feature({ label, children, footer }: { label: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="bg-white p-7">
      <p className="mb-6 border-b-2 border-ink-950 pb-3 text-sm font-semibold text-ink-950">{label}</p>
      <div>{children}</div>
      {footer ? <div className="mt-7 border-t border-ink-200 pt-5">{footer}</div> : null}
    </div>
  );
}

/** Indicadores en una sola franja bajo una regla negra: se leen de corrido, como un tablero. */
function Metrics({ children, columns }: { children: ReactNode; columns: 3 | 4 }) {
  return (
    <div className={`mb-10 grid border-t-2 border-ink-950 ${columns === 4 ? "grid-cols-2 lg:grid-cols-4" : "grid-cols-1 sm:grid-cols-3"} [&>*]:border-ink-200 max-lg:[&>*:nth-child(-n+2)]:border-b lg:[&>*+*]:border-l max-lg:[&>*:nth-child(even)]:border-l`}>
      {children}
    </div>
  );
}

function Metric({ label, value, detail, href, alert = false }: { label: string; value: number; detail?: string; href?: string; alert?: boolean }) {
  const content = (
    <>
      <p className="flex items-center gap-2 pr-6 text-sm font-medium text-ink-600">
        {alert ? <span className="size-2 bg-ink-950" aria-hidden="true" /> : null}
        {label}
      </p>
      <p className={`mt-4 font-display text-[2.5rem] leading-none tabular sm:text-6xl text-ink-950 ${alert ? "underline decoration-4 underline-offset-8" : ""}`}>{value}</p>
      {detail ? <p className="mt-3 text-xs text-ink-500">{detail}</p> : null}
    </>
  );
  const box = "group relative min-w-0 p-5 sm:p-6";
  return href ? (
    <AppLink href={href} className={`${box} transition-colors hover:bg-ink-50`}>
      {content}
      <span className="absolute right-4 top-5 grid size-7 place-items-center text-ink-400 transition-[transform,color] duration-200 group-hover:translate-x-0.5 group-hover:text-brand-700">
        <Icon name="arrow-right" className="size-3.5" />
      </span>
    </AppLink>
  ) : <div className={box}>{content}</div>;
}

const leafDay = new Intl.DateTimeFormat("es-CO", { timeZone: "America/Bogota", day: "numeric" });
const leafMonth = new Intl.DateTimeFormat("es-CO", { timeZone: "America/Bogota", month: "short" });

/** Hoja de calendario: el día se reconoce de un vistazo. */
function DateLeaf({ iso, size = "md" }: { iso: string; size?: "md" | "lg" }) {
  const date = new Date(iso);
  const big = size === "lg";
  return (
    <span className={`flex shrink-0 flex-col items-center overflow-hidden border border-ink-950 bg-white ${big ? "w-20" : "w-12"}`} aria-hidden="true">
      <span className={`w-full bg-brand-700 text-center font-semibold text-white ${big ? "py-1 text-xs" : "py-0.5 text-[10px]"}`}>{leafMonth.format(date).replace(".", "")}</span>
      <span className={`font-display leading-tight tabular text-ink-950 ${big ? "py-2 text-4xl" : "py-1 text-lg"}`}>{leafDay.format(date)}</span>
    </span>
  );
}

function Row({ icon, leaf, title, detail, aside }: { icon?: string; leaf?: ReactNode; title: string; detail: string; aside?: ReactNode }) {
  return (
    <li className="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2 border-t border-ink-200 py-3.5 first:border-t-0 sm:flex-nowrap">
      {leaf ?? <span className="grid size-12 shrink-0 place-items-center bg-ink-100 text-ink-700"><Icon name={icon ?? "file-text"} className="size-5" /></span>}
      <div className="min-w-0 flex-1 basis-[calc(100%-4rem)] sm:basis-auto">
        <p className="truncate font-semibold text-ink-950">{title}</p>
        <p className="truncate text-sm text-ink-500">{detail}</p>
      </div>
      {aside ? <div className="ml-16 flex items-center gap-2 sm:ml-0">{aside}</div> : null}
    </li>
  );
}

function VisitRow({ visit }: { visit: Visit }) {
  return (
    <Row leaf={<DateLeaf iso={visit.starts_at} />} title={visit.company}
      detail={`${formatDay(visit.starts_at)}, ${formatTime(visit.starts_at)} a ${formatTime(visit.ends_at)}, ${visit.site}`}
      aside={<><Badge tone={visit.level.tone} dot>{visit.level.label}</Badge><AppLink className={linkButtonClass()} href={visit.url}>Ver</AppLink></>} />
  );
}

function ContractRow({ contract }: { contract: Contract }) {
  return (
    <Row icon="file-signature" title={contract.company} detail={`El contrato ${contract.code} vence el ${formatLongDate(contract.end_date)}`}
      aside={<AppLink className={linkButtonClass()} href={contract.url}>Ver</AppLink>} />
  );
}

function NextVisit({ visit, empty }: { visit: Visit | undefined; empty: string }) {
  if (!visit) {
    return <p className="text-[15px] text-ink-600">{empty}</p>;
  }
  return (
    <div className="flex items-start gap-5">
      <DateLeaf iso={visit.starts_at} size="lg" />
      <div className="min-w-0">
        <p className="font-display text-2xl leading-tight text-ink-950">{visit.company}</p>
        <p className="mt-2 text-[15px] text-ink-600">{formatDay(visit.starts_at)}</p>
        <p className="text-[15px] text-ink-600">{formatTime(visit.starts_at)} a {formatTime(visit.ends_at)}</p>
        <p className="mt-1 flex items-center gap-1.5 text-sm text-ink-500"><Icon name="map-pin" className="size-4" />{visit.site}</p>
        <div className="mt-4"><Badge tone={visit.level.tone} dot>{visit.level.label}</Badge></div>
      </div>
    </div>
  );
}

function EvaluationsCard({ evaluations }: { evaluations: Evaluation[] }) {
  return (
    <Card>
      <SectionHead title="Evaluaciones recientes" subtitle="Últimos registros ergonómicos"
        action={<AppLink className={linkButtonClass()} href={"/evaluaciones/"}>Ver todas</AppLink>} />
      {evaluations.length === 0 ? <EmptyText>Aún no hay evaluaciones.</EmptyText> : (
        <>
        <ul className="-mx-6 -mb-6 border-t-2 border-ink-950 sm:hidden">
          {evaluations.map((evaluation) => (
            <li key={evaluation.id} className="border-b border-ink-200 px-6 py-4 last:border-b-0">
              <div className="flex items-baseline justify-between gap-3">
                <AppLink className="font-semibold tabular text-brand-700 underline decoration-brand-700/30 underline-offset-4" href={evaluation.url}>{evaluation.code}</AppLink>
                <span className="text-sm tabular text-ink-600">{formatShortDate(evaluation.evaluated_on)}</span>
              </div>
              <p className="mt-1 font-medium text-ink-950">{evaluation.position}</p>
              <p className="text-sm text-ink-600">{evaluation.company}, {evaluation.area}</p>
              <div className="mt-2 flex flex-wrap items-center gap-2"><RiskBadge risk={evaluation.risk} /><Badge tone={evaluation.status === "terminada" ? "teal" : "amber"}>{evaluation.status_label}</Badge></div>
            </li>
          ))}
        </ul>
        <div className="relative -mx-6 -mb-6 hidden overflow-x-auto sm:block">
          <table className="w-full min-w-[760px] text-left text-sm [&_td]:whitespace-nowrap">
            <thead className="border-y-2 border-ink-950 text-xs text-ink-600">
              <tr><th scope="col" className="px-6 py-3 font-medium">Evaluación</th><th scope="col" className="px-3 font-medium">Empresa</th><th scope="col" className="px-3 font-medium">Puesto y área</th><th scope="col" className="px-3 font-medium">Fecha</th><th scope="col" className="px-3 font-medium">Riesgo</th><th scope="col" className="px-6 font-medium">Estado</th></tr>
            </thead>
            <tbody className="[&>tr]:transition-colors [&>tr:hover]:bg-ink-50">
              {evaluations.map((evaluation) => (
                <tr key={evaluation.id} className="border-t border-ink-200 first:border-t-0">
                  <td className="px-6 py-3.5 font-semibold tabular"><AppLink className="text-brand-700 hover:underline" href={evaluation.url}>{evaluation.code}</AppLink></td>
                  <td className="px-3">{evaluation.company}</td>
                  <td className="px-3"><span className="block text-ink-950">{evaluation.position}</span><span className="text-xs text-ink-500">{evaluation.area}</span></td>
                  <td className="px-3 tabular text-ink-600">{formatShortDate(evaluation.evaluated_on)}</td>
                  <td className="px-3"><RiskBadge risk={evaluation.risk} /></td>
                  <td className="px-6"><Badge tone={evaluation.status === "terminada" ? "teal" : "amber"}>{evaluation.status_label}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </>
      )}
    </Card>
  );
}

function SupportPanel({ data }: { data: SupportDashboard }) {
  const total = data.users_by_role.reduce((sum, row) => sum + row.total, 0);
  return (
    <>
      <Hero data={data}
        summary={`Gestionas las cuentas y el mantenimiento. Hay ${plural(total, "cuenta activa", "cuentas activas")}; las evaluaciones, visitas y contratos son del ingeniero y de las empresas.`}
        actions={data.has_engineer ? (
          <AppLink href={"/usuarios/"} className={linkButtonClass("inverse")}><Icon name="users" />Gestionar cuentas</AppLink>
        ) : (
          <>
            <AppLink href={"/usuarios/nuevo/"} className={linkButtonClass("inverse")}><Icon name="user-plus" />Crear la cuenta del ingeniero</AppLink>
            <AppLink href={"/usuarios/"} className={linkButtonClass("inverseOutline")}>Ver cuentas</AppLink>
          </>
        )}
        feature={
          <Feature label="Estado del sistema">
            <ul className="grid gap-4">
              <li className="flex items-center gap-4">
                <span className="grid size-12 shrink-0 place-items-center bg-ink-100 text-ink-800"><Icon name="file-text" className="size-5" /></span>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-ink-950">Lectura de contratos con IA</p>
                  <p className="text-sm text-ink-500">{data.ai_ready ? "Configurada en el servidor." : "Falta configurar ANTHROPIC_API_KEY."}</p>
                </div>
                <Badge tone={data.ai_ready ? "teal" : "amber"} dot>{data.ai_ready ? "Activa" : "Pendiente"}</Badge>
              </li>
              <li className="flex items-center gap-4">
                <span className="grid size-12 shrink-0 place-items-center bg-ink-100 text-ink-800"><Icon name="shield-check" className="size-5" /></span>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-ink-950">Panel técnico</p>
                  <p className="text-sm text-ink-500">Consulta de datos para diagnóstico.</p>
                </div>
                <AppLink className={linkButtonClass()} href={"/admin/"}>Abrir</AppLink>
              </li>
            </ul>
          </Feature>
        } />
      <Metrics columns={3}>
        {data.users_by_role.map((row) => <Metric key={row.role} label={row.label} value={row.total} detail={plural(row.total, "cuenta activa", "cuentas activas")} />)}
      </Metrics>
      <Card>
        <SectionHead title="Cuentas recientes" subtitle="Últimas creadas" action={<AppLink className={linkButtonClass()} href={"/usuarios/"}>Gestionar</AppLink>} />
        <ul>
          {data.recent_accounts.map((account) => (
            <Row key={account.id}
              leaf={<span className="grid size-12 shrink-0 place-items-center bg-ink-100 text-sm font-bold text-ink-700">{account.initials}</span>}
              title={account.full_name}
              detail={account.company ? `${account.role_label}, ${account.company.name}` : account.role_label}
              aside={!account.is_active ? <Badge>Desactivada</Badge> : account.must_change_password ? <Badge tone="amber">Clave temporal</Badge> : undefined} />
          ))}
        </ul>
      </Card>
    </>
  );
}

function EngineerPanel({ data }: { data: EngineerDashboard }) {
  const active = data.contract_counts.vigente + data.contract_counts.por_vencer;
  const visits = [...data.to_close, ...data.upcoming_visits];
  const next = data.upcoming_visits[0];
  const pending = [
    data.to_close_count ? plural(data.to_close_count, "visita por cerrar", "visitas por cerrar") : "",
    data.drafts_count ? plural(data.drafts_count, "evaluación en curso", "evaluaciones en curso") : "",
    data.contract_counts.por_vencer ? plural(data.contract_counts.por_vencer, "contrato por vencer", "contratos por vencer") : "",
  ].filter(Boolean);
  const summary = pending.length ? `Tienes ${sentence(pending)}.` : "Todo está al día: no hay visitas por cerrar ni evaluaciones pendientes.";

  return (
    <>
      <Hero data={data} summary={summary}
        actions={<>
          <AppLink href={"/visitas/"} className={linkButtonClass("inverse")}><Icon name="calendar-days" />Ver calendario</AppLink>
          <AppLink href={"/evaluaciones/"} className={linkButtonClass("inverseOutline")}><Icon name="clipboard-check" />Evaluaciones</AppLink>
        </>}
        feature={
          <Feature label="Próxima visita" footer={next ? <AppLink href={next.url} className={linkButtonClass("primary")}>Abrir la visita<Icon name="arrow-right" className="size-4" /></AppLink> : undefined}>
            <NextVisit visit={next} empty="No hay visitas programadas. Las empresas las agendan desde su calendario." />
          </Feature>
        } />

      {data.onboarding ? (
        <Card className="mb-8">
          <SectionHead title="Primeros pasos" subtitle="Así se presta el servicio en ErgoPostura" />
          <ol className="grid gap-3 md:grid-cols-2">
            {data.steps.map((step, index) => (
              <li key={step.label} className={`flex items-center gap-3 border border-ink-200 p-3 text-sm ${step.done ? "text-ink-400 line-through" : "text-ink-700"}`}>
                <span className={`grid size-8 shrink-0 place-items-center text-xs font-bold tabular ${step.done ? "bg-brand-700 text-white" : "border border-ink-950 text-ink-950"}`}>
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

      <div className="mb-8 grid gap-6 lg:grid-cols-[1.35fr_1fr]">
        <Card>
          <SectionHead title="Agenda" subtitle="Visitas agendadas por las empresas" action={<AppLink className={linkButtonClass()} href={"/visitas/"}>Calendario</AppLink>} />
          {visits.length === 0 ? <EmptyText>No hay visitas programadas.</EmptyText> : <ul className="grid grid-cols-[minmax(0,1fr)] gap-1">{visits.map((visit) => <VisitRow key={visit.id} visit={visit} />)}</ul>}
        </Card>
        <Card>
          <SectionHead title="Requiere tu atención" subtitle="Contratos por vencer y visitas sin evaluar" />
          {data.expiring_contracts.length + data.without_evaluation.length === 0 ? (
            <div className="flex items-center gap-3 bg-emerald-50 p-4 text-sm text-emerald-900"><Icon name="check" />Todo al día.</div>
          ) : (
            <ul className="grid grid-cols-[minmax(0,1fr)] gap-1">
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

/** Días entre dos fechas AAAA-MM-DD (en UTC, para no depender de la zona horaria). */
const dayIndex = (iso: string) => Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10))) / 86_400_000;

function ContractFeature({ contract, today }: { contract: Contract | null; today: string }) {
  if (!contract) {
    return (
      <Feature label="Contrato de servicio">
        <p className="text-[15px] leading-relaxed text-ink-600">No hay un contrato vigente. Sin contrato no se pueden agendar visitas: comunícate con el ingeniero.</p>
      </Feature>
    );
  }
  const total = Math.max(1, dayIndex(contract.end_date) - dayIndex(contract.start_date));
  const elapsed = Math.min(total, Math.max(0, dayIndex(today) - dayIndex(contract.start_date)));
  const percent = Math.round((elapsed / total) * 100);
  return (
    <Feature label="Contrato de servicio" footer={<AppLink className={linkButtonClass("secondary")} href={contract.url}>Ver contrato</AppLink>}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-display text-2xl tabular text-ink-950">{contract.code}</p>
          <p className="text-[15px] text-ink-600">{contract.kind_label}</p>
        </div>
        <ContractBadge status={contract.status} label={contract.status_label} />
      </div>
      <div className="mt-7">
        <div className="h-3 overflow-hidden bg-ink-100" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label="Tiempo transcurrido del contrato">
          <div className={`h-full ${contract.status === "por_vencer" ? "bg-amber-500" : "bg-brand-700"}`} style={{ width: `${percent}%` }} />
        </div>
        <div className="mt-2 flex justify-between text-xs text-ink-500">
          <span>{formatLongDate(contract.start_date)}</span>
          <span>{formatLongDate(contract.end_date)}</span>
        </div>
      </div>
      {contract.status === "por_vencer" ? (
        <p className="mt-4 bg-amber-50 p-3 text-sm text-amber-900">Vence en {plural(contract.days_left, "día", "días")}. Habla con el ingeniero si quieres renovarlo.</p>
      ) : contract.status !== "vencido" ? (
        <p className="mt-4 text-sm text-ink-600">Quedan {plural(contract.days_left, "día", "días")} de servicio.</p>
      ) : null}
    </Feature>
  );
}

function CompanyPanel({ data }: { data: CompanyDashboard }) {
  const nextVisit = data.upcoming_visits[0];
  const summary = sentence([
    nextVisit ? `Tu próxima visita es el ${formatDay(nextVisit.starts_at).toLowerCase()}` : "No tienes visitas programadas",
    data.pending_count ? plural(data.pending_count, "recomendación por atender", "recomendaciones por atender") : "ninguna recomendación pendiente",
  ]);
  return (
    <>
      <Hero data={data} summary={<>{data.company?.name ? <strong className="font-semibold text-white">{data.company.name.endsWith(".") ? data.company.name : `${data.company.name}.`} </strong> : null}{summary}.</>}
        actions={<>
          <AppLink href={"/visitas/"} className={linkButtonClass("inverse")}><Icon name="calendar-days" />Agendar una visita</AppLink>
          <AppLink href={"/evaluaciones/"} className={linkButtonClass("inverseOutline")}><Icon name="clipboard-check" />Ver resultados</AppLink>
          <AppLink href={"/tareas/"} className="inline-flex h-11 items-center px-1 text-sm font-semibold text-white underline decoration-white/40 underline-offset-4 hover:decoration-white">Recomendaciones ({data.pending_count})</AppLink>
        </>}
        feature={<ContractFeature contract={data.contract} today={data.today} />} />

      {data.counts ? (
        <Metrics columns={4}>
          <Metric label="Sedes" value={data.counts.sites} />
          <Metric label="Áreas" value={data.counts.areas} />
          <Metric label="Puestos" value={data.counts.positions} />
          <Metric label="Trabajadores" value={data.counts.workers} />
        </Metrics>
      ) : null}
      <div className="mb-8">
        <Card>
          <SectionHead title="Próximas visitas" subtitle="Las siguientes en el calendario" action={<AppLink className={linkButtonClass()} href={"/visitas/"}>Ver todas</AppLink>} />
          {data.upcoming_visits.length === 0 ? <EmptyText>No hay visitas programadas.</EmptyText> : <ul className="grid grid-cols-[minmax(0,1fr)] gap-1">{data.upcoming_visits.map((visit) => <VisitRow key={visit.id} visit={visit} />)}</ul>}
        </Card>
      </div>
      <EvaluationsCard evaluations={data.recent_evaluations} />
    </>
  );
}
