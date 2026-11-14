import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";

import { useAuth } from "../../auth/AuthContext";
import { usePageTitle } from "../../components/Page";
import { EmptyState, PageHead, Pagination, SearchBar, Table } from "../../components/Table";
import { Badge, Button, Card, ErrorState, Icon, Spinner } from "../../components/ui";
import { useResource } from "../../lib/useResource";
import { companiesApi } from "./api";
import { CompanyFormModal } from "./forms";

export function CompaniesPage() {
  usePageTitle("Empresas");
  const { can } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [creating, setCreating] = useState(false);
  const q = params.get("q") ?? "";
  const page = Number(params.get("pagina") ?? "1") || 1;
  const [resource, retry] = useResource((signal) => companiesApi.list({ q, page }, signal), [q, page]);

  const head = (
    <PageHead title="Empresas" subtitle="Administra empresas, sedes, áreas y puestos de trabajo."
      action={can("company.manage") ? <Button onClick={() => setCreating(true)}><Icon name="plus" />Registrar empresa</Button> : null} />
  );
  const modal = creating ? (
    <CompanyFormModal onClose={() => setCreating(false)} onSaved={({ id }) => navigate(`/empresas/${id}`)} />
  ) : null;

  if (resource.state === "error") return <>{head}<ErrorState error={resource.error} onRetry={retry} />{modal}</>;

  return (
    <>
      {head}
      <Card>
        <SearchBar key={q} query={q} label="Buscar empresas" placeholder="Buscar por nombre o NIT"
          onSearch={(text) => setParams(text ? { q: text } : {})} />
        {resource.state === "loading" ? <Spinner /> : resource.data.results.length === 0 ? (
          <EmptyState icon="building-complex" title={q ? "No hay resultados" : "Aún no hay empresas"}>
            {q ? "Prueba con otro nombre o NIT." : "Registra la primera para organizar sus sedes, áreas y puestos."}
          </EmptyState>
        ) : (
          <>
            <Table head={["Empresa", "NIT", "Ubicación", "Sedes", "Estado"]}>
              {resource.data.results.map((company) => (
                <tr key={company.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3"><Link to={`/empresas/${company.id}`} className="font-semibold text-slate-900 hover:text-teal-700">{company.name}</Link></td>
                  <td className="px-5 py-3 tabular-nums text-slate-600">{company.nit}</td>
                  <td className="px-5 py-3 text-slate-600">{company.location}</td>
                  <td className="px-5 py-3 tabular-nums">{company.site_count}</td>
                  <td className="px-5 py-3">{company.is_active ? <Badge tone="teal">Activa</Badge> : <Badge>Inactiva</Badge>}</td>
                </tr>
              ))}
            </Table>
            <Pagination page={resource.data} noun="empresas"
              onPage={(next) => setParams({ ...(q ? { q } : {}), ...(next > 1 ? { pagina: String(next) } : {}) })} />
          </>
        )}
      </Card>
      {modal}
    </>
  );
}
