import { useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { toApiError, type ApiError } from "../../api/client";
import { ConfirmModal } from "../../components/Modal";
import { useNotify, usePageTitle } from "../../components/Page";
import { Button, Card, ContractBadge, ErrorState, Icon, linkButtonClass, SectionHead, Spinner } from "../../components/ui";
import { formatInstantDate, formatLongDate, formatShortDate } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { contractsApi, formatMoney, formatSize, type ComparisonRow, type ContractDetail } from "./api";

export function ContractDetailPage() {
  const id = Number(useParams().id);
  const [resource, retry] = useResource((signal) => contractsApi.get(id, signal), [id]);
  usePageTitle(resource.state === "ready" ? `Contrato ${resource.data.code}` : "Contrato");
  if (resource.state === "loading") return <Spinner />;
  if (resource.state === "error") return <ErrorState error={resource.error} onRetry={retry} />;
  return <Detail initial={resource.data} />;
}

function Banner({ tone, children }: { tone: "amber" | "red" | "neutral"; children: ReactNode }) {
  const tones = { amber: "bg-amber-50 text-amber-900", red: "bg-red-50 text-red-900", neutral: "bg-slate-100 text-slate-700" };
  return (
    <div role="status" className={`mb-4 flex gap-2.5 rounded-lg px-4 py-3 text-sm ${tones[tone]}`}>
      <Icon name="circle-exclamation-point" className="mt-0.5 size-4" /><span>{children}</span>
    </div>
  );
}

function Item({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 py-2.5 sm:grid-cols-[9rem_1fr]">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="whitespace-pre-line text-sm text-slate-900">{children}</dd>
    </div>
  );
}

function Detail({ initial }: { initial: ContractDetail }) {
  const navigate = useNavigate();
  const notify = useNotify();
  const [contract, setContract] = useState(initial);
  const [reading, setReading] = useState(false);
  const [readError, setReadError] = useState<ApiError | null>(null);
  const [deleting, setDeleting] = useState<{ sending: boolean; error: ApiError | null } | null>(null);

  async function summarize() {
    setReading(true);
    setReadError(null);
    try {
      setContract(await contractsApi.summarize(contract.id));
      notify("Resumen generado");
    } catch (cause) {
      setReadError(toApiError(cause));
    } finally {
      setReading(false);
    }
  }

  async function remove() {
    setDeleting({ sending: true, error: null });
    try {
      await contractsApi.remove(contract.id);
      notify("Contrato eliminado");
      navigate("/contratos", { replace: true });
    } catch (cause) {
      setDeleting({ sending: false, error: toApiError(cause) });
    }
  }

  const summary = contract.ai_summary;
  return (
    <>
      <Link to={contract.can_manage ? "/contratos" : "/"} className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700 hover:underline">
        <Icon name="arrow-left" className="size-4" />{contract.can_manage ? "Volver a contratos" : "Volver al panel"}
      </Link>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-bold tracking-wider text-teal-700">CONTRATO {contract.code}</p>
          <h1 className="text-2xl font-bold">{contract.company.name}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {contract.kind_label} · {formatLongDate(contract.start_date)} al {formatLongDate(contract.end_date)} ({contract.duration_label})
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ContractBadge status={contract.status} label={contract.status_label} />
          <a href={contract.file_url} target="_blank" rel="noopener" className={linkButtonClass("secondary")}><Icon name="file-text" />Ver PDF</a>
          {contract.can_manage ? <Link to={`/contratos/${contract.id}/editar`} className={linkButtonClass("primary")}><Icon name="pencil" />Editar</Link> : null}
        </div>
      </div>

      {contract.status === "por_vencer" ? (
        <Banner tone="amber">
          Vence en {contract.days_left} día{contract.days_left === 1 ? "" : "s"}.{" "}
          {contract.can_manage ? "Si la empresa renueva, registra el nuevo contrato a partir del día siguiente al vencimiento." : "Comunícate con el ingeniero si quieres renovarlo."}
        </Banner>
      ) : contract.status === "vencido" ? (
        <Banner tone="neutral">El contrato terminó. La empresa no puede agendar visitas nuevas hasta que haya otro vigente.</Banner>
      ) : null}
      {contract.nit_mismatch ? (
        <Banner tone="red">
          El NIT que aparece en el documento ({summary?.client_nit_text}) no es el de {contract.company.name} ({contract.company.nit}). Revisa que el PDF corresponda a esta empresa.
        </Banner>
      ) : null}

      <div className={`grid gap-5 ${contract.can_manage ? "lg:grid-cols-2" : ""}`}>
        <Card>
          <SectionHead title="Datos registrados" />
          <dl className="divide-y divide-slate-100">
            <Item label="Empresa">{contract.company.name} · NIT {contract.company.nit}</Item>
            <Item label="Tipo">{contract.kind_label}</Item>
            <Item label="Servicio">{contract.service}</Item>
            <Item label="Vigencia">{formatShortDate(contract.start_date)} – {formatShortDate(contract.end_date)} · {contract.duration_label}</Item>
            <Item label="Valor">{contract.value !== null ? `${formatMoney(contract.value)} COP` : "Sin registrar"}</Item>
            <Item label="Encargado">
              {contract.responsible_name}{contract.responsible_role ? `, ${contract.responsible_role}` : ""}
              {contract.responsible_email ? <><br /><a className="text-teal-700 hover:underline" href={`mailto:${contract.responsible_email}`}>{contract.responsible_email}</a></> : null}
              {contract.responsible_phone ? <><br />{contract.responsible_phone}</> : null}
            </Item>
            {contract.notes ? <Item label="Notas">{contract.notes}</Item> : null}
            <Item label="Documento">
              <a className="text-teal-700 hover:underline" href={`${contract.file_url}?descargar=1`}>{contract.file_name}</a> · {formatSize(contract.file_size)}
            </Item>
            {contract.created_at ? <Item label="Registrado">{formatInstantDate(contract.created_at)}{contract.created_by ? ` por ${contract.created_by}` : ""}</Item> : null}
          </dl>
          {contract.can_manage ? (
            <div className="mt-4 border-t border-slate-100 pt-4">
              <Button variant="dangerGhost" onClick={() => setDeleting({ sending: false, error: null })}>
                <Icon name="trash" />Eliminar contrato
              </Button>
            </div>
          ) : null}
        </Card>

        {contract.can_manage ? (
          <Card>
            <SectionHead
              title="Resumen con IA"
              subtitle={summary && contract.ai_generated_at
                ? `Leído por ${contract.ai_model ?? ""} el ${formatInstantDate(contract.ai_generated_at)}`
                : "Asistente de lectura del contrato"}
              action={contract.ai_ready ? (
                <Button variant="secondary" disabled={reading} onClick={() => void summarize()}>
                  <Icon name="sparkles" />{reading ? "Leyendo el contrato…" : summary ? "Volver a leer" : "Generar resumen"}
                </Button>
              ) : undefined}
            />
            {readError ? <p role="alert" className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800">{readError.message}</p> : null}
            {summary ? <Summary contract={contract} /> : contract.ai_ready ? (
              <div className="py-6 text-center">
                <span className="mx-auto mb-2 grid size-12 place-items-center rounded-full bg-violet-50 text-violet-700"><Icon name="sparkles" /></span>
                <p className="font-semibold">Aún no hay resumen</p>
                <p className="mx-auto max-w-sm text-sm text-slate-500">La IA lee el PDF y te da la duración, el tipo de contrato, el servicio, el encargado, el NIT y lo que conviene revisar. Tarda entre 10 y 40 segundos.</p>
              </div>
            ) : (
              <p className="text-sm text-slate-500">La lectura con IA no está configurada en este servidor (falta ANTHROPIC_API_KEY). Soporte puede activarla.</p>
            )}
          </Card>
        ) : null}
      </div>

      {contract.history && contract.history.length ? (
        <Card className="mt-5">
          <SectionHead title="Otros contratos de la empresa" />
          <ul className="divide-y divide-slate-100">
            {contract.history.map((other) => (
              <li key={other.id} className="flex items-center gap-3 py-2.5">
                <Icon name="file-signature" className="size-4 text-slate-400" />
                <span className="min-w-0 flex-1">
                  <strong className="block text-sm">{other.code} · {other.kind_label}</strong>
                  <small className="text-slate-500">{formatShortDate(other.start_date)} – {formatShortDate(other.end_date)}</small>
                </span>
                <ContractBadge status={other.status} label={other.status_label} />
                <Link to={`/contratos/${other.id}`} className={linkButtonClass()}>Ver</Link>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {deleting ? (
        <ConfirmModal title="Eliminar contrato" danger confirmLabel="Eliminar" sending={deleting.sending} error={deleting.error}
          message={`¿Eliminar el contrato ${contract.code}? Se borra también el PDF. Esta acción no se puede deshacer.`}
          onClose={() => setDeleting(null)} onConfirm={() => void remove()} />
      ) : null}
    </>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  return <div><strong className="text-sm">{title}</strong><ul className="ml-5 mt-1 list-disc text-sm text-slate-700">{items.map((i) => <li key={i}>{i}</li>)}</ul></div>;
}

function Summary({ contract }: { contract: ContractDetail }) {
  const summary = contract.ai_summary ?? {};
  const details: [string, string | undefined][] = [
    ["Servicio", summary.service], ["Duración", summary.duration_text], ["Contratista", summary.provider_name],
    ["Pagos", summary.payment_terms], ["Terminación", summary.termination], ["Datos personales", summary.data_protection],
  ];
  return (
    <div className="space-y-4">
      {summary.summary ? <p className="text-sm leading-relaxed text-slate-800">{summary.summary}</p> : null}
      {summary.alerts?.length ? (
        <div className="rounded-lg bg-amber-50 px-3 py-2.5 text-amber-900"><List title="Para revisar" items={summary.alerts} /></div>
      ) : null}
      <dl className="divide-y divide-slate-100">
        {details.filter(([, value]) => value).map(([label, value]) => <Item key={label} label={label}>{value}</Item>)}
      </dl>
      {summary.provider_obligations?.length || summary.client_obligations?.length ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {summary.provider_obligations?.length ? <List title="Obligaciones del ingeniero" items={summary.provider_obligations} /> : null}
          {summary.client_obligations?.length ? <List title="Obligaciones de la empresa" items={summary.client_obligations} /> : null}
        </div>
      ) : null}
      {contract.comparison?.length ? <Comparison rows={contract.comparison} /> : null}
      <p className="text-xs text-slate-500">La IA puede equivocarse. Lo que vale es lo registrado y el documento firmado.</p>
    </div>
  );
}

function show(row: ComparisonRow, value: string | number | null): string {
  if (value === null || value === "") return "";
  if (row.label === "Valor" && typeof value === "number") return formatMoney(value);
  if ((row.label === "Inicio" || row.label === "Fin") && typeof value === "string") return formatShortDate(value);
  return String(value);
}

function Comparison({ rows }: { rows: ComparisonRow[] }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold">Leído frente a registrado</h3>
      <div className="relative overflow-x-auto">
        <table className="w-full min-w-[420px] text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-slate-500">
            <tr><th scope="col" className="py-2 pr-3">Dato</th><th scope="col" className="py-2 pr-3">En el documento</th><th scope="col" className="py-2">Registrado</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row) => (
              <tr key={row.label} className={row.differs ? "bg-red-50" : ""}>
                <th scope="row" className="py-2 pr-3 font-medium">{row.label}</th>
                <td className="py-2 pr-3">{row.missing ? <span className="text-slate-400">No aparece</span> : show(row, row.read)}</td>
                <td className="py-2">
                  {row.registered === null ? <span className="text-slate-400">Sin registrar</span> : show(row, row.registered)}
                  {row.differs ? <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-800">No coincide</span> : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
