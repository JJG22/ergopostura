import { Link, useSearchParams } from "react-router";

import { usePageTitle } from "../../components/Page";
import { EmptyState, PageHead, Pagination, SearchBar, Table } from "../../components/Table";
import { Card, ContractBadge, ErrorState, Icon, linkButtonClass, Spinner } from "../../components/ui";
import { formatShortDate } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { contractsApi } from "./api";

export function ContractsPage() {
  usePageTitle("Contratos");
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const status = params.get("estado") ?? "";
  const page = Number(params.get("pagina") ?? "1") || 1;
  const [resource, retry] = useResource((signal) => contractsApi.list({ q, status, page }, signal), [q, status, page]);

  const go = (next: { q?: string; estado?: string; pagina?: number }) => {
    const values = { q, estado: status, ...next, pagina: next.pagina && next.pagina > 1 ? String(next.pagina) : "" };
    setParams(Object.fromEntries(Object.entries(values).filter(([, v]) => v)) as Record<string, string>);
  };

  const head = (
    <PageHead title="Contratos" subtitle="Un contrato por empresa a la vez. Las empresas solo pueden agendar visitas dentro de su vigencia."
      action={<Link to="/contratos/nuevo" className={linkButtonClass("primary")}><Icon name="plus" />Registrar contrato</Link>} />
  );
  if (resource.state === "error") return <>{head}<ErrorState error={resource.error} onRetry={retry} /></>;

  const tab = (value: string, label: string, total?: number) => (
    <button key={value || "todos"} type="button" onClick={() => go({ estado: value })} aria-current={status === value ? "page" : undefined}
      className={`-mb-px inline-flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-semibold whitespace-nowrap ${
        status === value ? "border-teal-700 text-teal-800" : "border-transparent text-slate-500 hover:text-slate-800"}`}>
      {label}
      {total !== undefined ? <span className="rounded-full bg-slate-100 px-2 text-xs text-slate-600">{total}</span> : null}
    </button>
  );

  return (
    <>
      {head}
      <Card>
        <div className="-mx-5 -mt-1 mb-4 flex overflow-x-auto border-b border-slate-200 px-5">
          {tab("", "Todos")}
          {resource.state === "ready" ? resource.data.statuses.map((s) => tab(s.value, s.label, s.total)) : null}
        </div>
        <SearchBar key={q} query={q} label="Buscar contratos" placeholder="Buscar por empresa, código o encargado" onSearch={(text) => go({ q: text })} />
        {resource.state === "loading" ? <Spinner /> : resource.data.results.length === 0 ? (
          <EmptyState icon="file-signature" title={q || status ? "No hay contratos con ese filtro" : "Aún no hay contratos"}>
            {q || status ? undefined : "Sube el contrato firmado con cada empresa. La IA puede leerlo y llenar los datos por ti."}
          </EmptyState>
        ) : (
          <>
            <Table head={["Empresa", "Contrato", "Vigencia", "Encargado", "Estado", "Resumen IA"]}>
              {resource.data.results.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3"><Link to={`/contratos/${c.id}`} className="font-semibold text-slate-900 hover:text-teal-700">{c.company.name}</Link></td>
                  <td className="px-5 py-3">{c.code}<small className="block text-slate-500">{c.kind_label}</small></td>
                  <td className="whitespace-nowrap px-5 py-3">
                    {formatShortDate(c.start_date)} – {formatShortDate(c.end_date)}
                    <small className="block text-slate-500">
                      {c.duration_label}{c.status === "vigente" || c.status === "por_vencer" ? ` · quedan ${c.days_left} día${c.days_left === 1 ? "" : "s"}` : ""}
                    </small>
                  </td>
                  <td className="px-5 py-3">{c.responsible_name}</td>
                  <td className="px-5 py-3"><ContractBadge status={c.status} label={c.status_label} /></td>
                  <td className="px-5 py-3">
                    {c.has_summary ? <span className="inline-flex items-center gap-1 text-xs font-semibold text-violet-700"><Icon name="sparkles" className="size-4" />Listo</span> : <span className="text-slate-400">—</span>}
                  </td>
                </tr>
              ))}
            </Table>
            <Pagination page={resource.data} noun="contratos" onPage={(next) => go({ pagina: next })} />
          </>
        )}
      </Card>
    </>
  );
}
