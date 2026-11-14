import { Link, useSearchParams } from "react-router";

import { useAuth } from "../../auth/AuthContext";
import { usePageTitle } from "../../components/Page";
import { EmptyState, PageHead, Pagination, SearchBar, Table } from "../../components/Table";
import { Card, ErrorState, Spinner } from "../../components/ui";
import { formatShortDate, formatTime } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { AccountActions, AccountStatus, CreateAccountButton, type AccountOptions } from "./AccountModals";
import { accountsApi } from "./api";

const ROLE_TONES: Record<string, string> = {
  admin: "bg-violet-100 text-violet-800",
  ingeniero: "bg-blue-100 text-blue-800",
  empresa: "bg-teal-100 text-teal-800",
};

export function AccountsPage() {
  const { can } = useAuth();
  const support = can("user.manage");
  usePageTitle(support ? "Usuarios" : "Accesos de empresas");
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const role = params.get("rol") ?? "";
  const page = Number(params.get("pagina") ?? "1") || 1;
  const [resource, retry, refresh] = useResource((signal) => accountsApi.list({ q, role, page }, signal), [q, role, page]);

  const search = (text: string, chosen: string) => setParams(clean({ q: text, rol: chosen }));
  const goTo = (next: number) => setParams(clean({ q, rol: role, pagina: next > 1 ? String(next) : "" }));

  const head = (
    <PageHead
      title={support ? "Usuarios" : "Accesos de empresas"}
      subtitle={support
        ? "Crea la cuenta del ingeniero industrial y da soporte a las demás. Las cuentas no se borran: se desactivan y conservan su historia."
        : "Accesos de las empresas cliente. Cada cuenta ve solo los datos de su empresa."}
      action={resource.state === "ready" && resource.data.creatable_roles.length ? (
        <CreateAccountButton options={optionsOf(resource.data)} onCreated={refresh} startOpen={params.get("crear") === "1"} />
      ) : null}
    />
  );

  if (resource.state === "error") return <>{head}<ErrorState error={resource.error} onRetry={retry} /></>;

  return (
    <>
      {head}
      <Card>
        <SearchBar key={`${q}|${role}`} query={q} label="Buscar cuentas" placeholder="Buscar por nombre, correo o empresa" onSearch={search}
          {...(resource.state === "ready" && resource.data.role_filter.length
            ? { filter: { label: "Filtrar por rol", value: role, options: resource.data.role_filter, allLabel: "Todos los roles" } }
            : {})} />
        {resource.state === "loading" ? <Spinner /> : resource.data.results.length === 0 ? (
          <EmptyState icon="users" title={q || role ? "No hay resultados" : support ? "Aún no hay más cuentas" : "Aún no hay accesos de empresas"}>
            {q || role ? "Prueba con otro nombre, correo o rol." : support
              ? "Crea la cuenta del ingeniero industrial para empezar a prestar el servicio."
              : "Crea el acceso desde aquí o desde el detalle de cada empresa."}
          </EmptyState>
        ) : (
          <>
            <Table head={["Persona", "Rol", "Empresa", "Último ingreso", "Estado", ""]}>
              {resource.data.results.map((account) => (
                <tr key={account.id} className={account.is_active ? "" : "opacity-60"}>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <span className="grid size-9 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-bold text-slate-700">{account.initials}</span>
                      <span className="min-w-0">
                        <strong className="block truncate">{account.full_name}</strong>
                        <small className="block truncate text-slate-500">{account.email}</small>
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    <span className={`whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${ROLE_TONES[account.role] ?? ""}`}>{account.role_label}</span>
                  </td>
                  <td className="px-5 py-3">
                    {account.company ? <Link className="hover:text-teal-700 hover:underline" to={`/empresas/${account.company.id}`}>{account.company.name}</Link> : <span className="text-slate-400">—</span>}
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 text-slate-600">
                    {account.last_login ? `${formatShortDate(account.last_login.slice(0, 10))}, ${formatTime(account.last_login)}` : <span className="text-slate-400">Nunca</span>}
                  </td>
                  <td className="px-5 py-3"><AccountStatus account={account} /></td>
                  <td className="px-5 py-3"><AccountActions account={account} options={optionsOf(resource.data)} onChanged={refresh} /></td>
                </tr>
              ))}
            </Table>
            <Pagination page={resource.data} noun="cuentas" onPage={goTo} />
          </>
        )}
      </Card>
    </>
  );
}

function optionsOf(data: { creatable_roles: AccountOptions["roles"]; companies: AccountOptions["companies"] }): AccountOptions {
  return { roles: data.creatable_roles, companies: data.companies };
}

function clean(values: Record<string, string>): Record<string, string> {
  return Object.fromEntries(Object.entries(values).filter(([, value]) => value));
}
