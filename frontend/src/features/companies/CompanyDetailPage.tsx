import { useState, type ReactNode } from "react";
import { Link, useParams, useSearchParams } from "react-router";

import { AppLink } from "../../components/AppLink";
import { usePageTitle } from "../../components/Page";
import { Badge, Button, Card, ContractBadge, ErrorState, Icon, linkButtonClass, SectionHead, Spinner } from "../../components/ui";
import { formatLongDate, plural } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { AccountActions, AccountStatus, CreateAccountButton, lastLogin, type AccountOptions } from "../accounts/AccountModals";
import { companiesApi, type Area, type CompanyDetail, type Position, type Saved, type Site, type Worker } from "./api";
import { CompanyFormModal, NamedFormModal, SiteFormModal, WorkerFormModal } from "./forms";

type Node =
  | { kind: "company" }
  | { kind: "site"; site: Site }
  | { kind: "area"; site: Site; area: Area }
  | { kind: "position"; site: Site; area: Area; position: Position };

/** Busca el nodo solo dentro de esta empresa: una clave ajena vuelve a mostrar la empresa. */
function findNode(company: CompanyDetail, key: string | null): Node {
  for (const site of company.sites) {
    if (site.key === key) return { kind: "site", site };
    for (const area of site.areas) {
      if (area.key === key) return { kind: "area", site, area };
      for (const position of area.positions) {
        if (position.key === key) return { kind: "position", site, area, position };
      }
    }
  }
  return { kind: "company" };
}

type Dialog =
  | { type: "company" }
  | { type: "site"; site?: Site }
  | { type: "area"; siteId: number; area?: Area }
  | { type: "position"; areaId: number; position?: Position }
  | { type: "worker"; positionId: number; worker?: Worker }
  | null;

export function CompanyDetailPage() {
  const id = Number(useParams().id);
  const [params, setParams] = useSearchParams();
  const [resource, retry, refresh] = useResource((signal) => companiesApi.get(id, signal), [id]);
  usePageTitle(resource.state === "ready" ? resource.data.name : "Empresa");

  if (resource.state === "loading") return <Spinner />;
  if (resource.state === "error") return <ErrorState error={resource.error} onRetry={retry} />;
  return <Detail company={resource.data} selected={params.get("nodo")} onSelect={(key) => setParams(key === "empresa" ? {} : { nodo: key }, { replace: true })} refresh={refresh} />;
}

function Detail({ company, selected, onSelect, refresh }: {
  company: CompanyDetail; selected: string | null; onSelect: (key: string) => void; refresh: () => void;
}) {
  const [dialog, setDialog] = useState<Dialog>(null);
  const node = findNode(company, selected);
  const { permissions, counts } = company;
  const close = () => setDialog(null);
  const saved = (result: Saved | { id: number }) => {
    setDialog(null);
    if ("key" in result) onSelect(result.key);
    refresh();
  };
  const accountOptions: AccountOptions = { roles: [{ value: "empresa", label: "Empresa" }], companies: [], company: { id: company.id, name: company.name } };

  return (
    <>
      {permissions.view_all ? (
        <Link to="/empresas" className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700 hover:underline">
          <Icon name="arrow-left" className="size-4" />Volver a empresas
        </Link>
      ) : null}
      <div className="mb-5">
        <p className="text-xs font-bold tracking-wider text-teal-700">EMPRESA</p>
        <h1 className="text-2xl font-bold">{company.name}</h1>
        <p className="mt-1 text-sm text-slate-500">NIT {company.nit} · {company.location} · {company.is_active ? "Empresa activa" : "Empresa inactiva"}</p>
      </div>

      <div className="mb-5 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600">
        <Stat icon="building-complex" text={plural(counts.sites, "sede", "sedes")} />
        <Stat icon="layout-list" text={plural(counts.areas, "área", "áreas")} />
        <Stat icon="users" text={plural(counts.positions, "puesto", "puestos")} />
        <Stat icon="user" text={plural(counts.workers, "trabajador", "trabajadores")} />
      </div>

      {company.shows_contract ? <ContractCard company={company} /> : null}

      <div className="grid gap-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <Card>
          <SectionHead title="Estructura de la empresa" subtitle="Sedes, áreas, puestos y trabajadores" />
          <Tree company={company} selectedKey={node.kind === "company" ? "empresa" : keyOf(node)} onSelect={onSelect} />
        </Card>
        <Card>
          <NodePanel company={company} node={node} onDialog={setDialog} />
        </Card>
      </div>

      {company.accounts ? (
        <Card className="mt-5">
          <div id="accesos" />
          <SectionHead title="Accesos de la empresa" subtitle="Con estas cuentas la empresa agenda visitas y consulta sus resultados"
            action={company.is_active ? <CreateAccountButton label="Crear acceso" options={accountOptions} onCreated={refresh} /> : null} />
          {company.accounts.length === 0 ? (
            <p className="text-sm text-slate-500">La empresa aún no tiene acceso. Créalo y entrega el correo y la contraseña temporal a su encargado.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {company.accounts.map((account) => (
                <li key={account.id} className={`flex flex-wrap items-center gap-3 py-3 ${account.is_active ? "" : "opacity-60"}`}>
                  <Avatar text={account.initials} />
                  <span className="min-w-0 flex-1">
                    <strong className="block truncate text-sm">{account.full_name}</strong>
                    <small className="block truncate text-slate-500">{account.email} · {lastLogin(account)}</small>
                  </span>
                  <AccountStatus account={account} />
                  <AccountActions account={account} options={accountOptions} onChanged={refresh} />
                </li>
              ))}
            </ul>
          )}
        </Card>
      ) : null}

      {dialog?.type === "company" ? <CompanyFormModal company={company} onClose={close} onSaved={saved} /> : null}
      {dialog?.type === "site" ? (
        <SiteFormModal companyId={company.id} {...(dialog.site ? { site: dialog.site } : {})} onClose={close} onSaved={saved}
          defaultPlace={{ department: String(company.department.id), municipality: String(company.municipality.id) }} />
      ) : null}
      {dialog?.type === "area" ? (
        <NamedFormModal level="areas" parentId={dialog.siteId} {...(dialog.area ? { item: dialog.area } : {})} onClose={close} onSaved={saved} />
      ) : null}
      {dialog?.type === "position" ? (
        <NamedFormModal level="positions" parentId={dialog.areaId} {...(dialog.position ? { item: dialog.position } : {})} onClose={close} onSaved={saved} />
      ) : null}
      {dialog?.type === "worker" ? (
        <WorkerFormModal positionId={dialog.positionId} {...(dialog.worker ? { worker: dialog.worker } : {})}
          documentTypes={company.document_types} onClose={close} onSaved={saved} />
      ) : null}
    </>
  );
}

function keyOf(node: Exclude<Node, { kind: "company" }>): string {
  if (node.kind === "site") return node.site.key;
  if (node.kind === "area") return node.area.key;
  return node.position.key;
}

function Stat({ icon, text }: { icon: string; text: string }) {
  const [count, ...rest] = text.split(" ");
  return <span className="inline-flex items-center gap-2"><Icon name={icon} className="size-4 text-slate-400" /><strong className="text-slate-900">{count}</strong>{rest.join(" ")}</span>;
}

function Avatar({ text }: { text: string }) {
  return <span className="grid size-9 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-bold text-slate-700">{text}</span>;
}

function ContractCard({ company }: { company: CompanyDetail }) {
  const { contract } = company;
  return (
    <Card className="mb-5 flex flex-wrap items-center gap-4">
      <span className={`grid size-10 place-items-center rounded-lg ${contract ? "bg-teal-50 text-teal-700" : "bg-amber-50 text-amber-700"}`}>
        <Icon name="file-signature" />
      </span>
      {contract ? (
        <>
          <span className="min-w-0 flex-1">
            <strong className="block text-sm">Contrato {contract.code} · {contract.kind_label}</strong>
            <small className="text-slate-500">Del {formatLongDate(contract.start_date)} al {formatLongDate(contract.end_date)}</small>
          </span>
          <ContractBadge status={contract.status} label={contract.status_label} />
          <AppLink href={contract.legacy_url} className={linkButtonClass()}>Ver contrato</AppLink>
        </>
      ) : (
        <>
          <span className="min-w-0 flex-1">
            <strong className="block text-sm">Sin contrato vigente</strong>
            <small className="text-slate-500">La empresa no puede agendar visitas hasta que tenga uno.</small>
          </span>
          {company.permissions.manage_contracts && company.is_active ? (
            <AppLink href={`/contratos/nuevo/?empresa=${company.id}`} className={linkButtonClass("primary")}><Icon name="plus" />Subir contrato</AppLink>
          ) : null}
        </>
      )}
    </Card>
  );
}

function TreeItem({ icon, title, detail, active, onClick }: { icon: string; title: string; detail: string; active: boolean; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} aria-current={active ? "true" : undefined}
      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition ${active ? "bg-teal-50 ring-1 ring-teal-200" : "hover:bg-slate-50"}`}>
      <Icon name={icon} className={`size-4 ${active ? "text-teal-700" : "text-slate-400"}`} />
      <span className="min-w-0">
        <strong className="block truncate text-sm">{title}</strong>
        <small className="block truncate text-xs text-slate-500">{detail}</small>
      </span>
    </button>
  );
}

function Tree({ company, selectedKey, onSelect }: { company: CompanyDetail; selectedKey: string; onSelect: (key: string) => void }) {
  const branch = "ml-4 border-l border-slate-200 pl-2";
  return (
    <div className="space-y-1">
      <TreeItem icon="building-complex" title={company.name} detail="Empresa" active={selectedKey === "empresa"} onClick={() => onSelect("empresa")} />
      {company.sites.length === 0 ? (
        <p className="px-3 py-6 text-center text-sm text-slate-500">Aún no hay sedes</p>
      ) : company.sites.map((site) => (
        <div key={site.id} className={branch}>
          <TreeItem icon="map-pin" title={site.name} detail={site.location} active={selectedKey === site.key} onClick={() => onSelect(site.key)} />
          {site.areas.map((area) => (
            <div key={area.id} className={branch}>
              <TreeItem icon="layout-list" title={area.name} detail={plural(area.positions.length, "puesto", "puestos")}
                active={selectedKey === area.key} onClick={() => onSelect(area.key)} />
              {area.positions.map((position) => (
                <div key={position.id} className={branch}>
                  <TreeItem icon="users" title={position.name} detail={plural(position.workers.length, "trabajador", "trabajadores")}
                    active={selectedKey === position.key} onClick={() => onSelect(position.key)} />
                </div>
              ))}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

const or = (value: string) => value || "Sin registrar";

function NodePanel({ company, node, onDialog }: { company: CompanyDetail; node: Node; onDialog: (dialog: Dialog) => void }) {
  let view: { kind: string; icon: string; name: string; path: string[]; details: [string, string][]; edit: Dialog; add: Dialog; addLabel: string };
  if (node.kind === "company") {
    view = {
      kind: "EMPRESA", icon: "building-complex", name: company.name, path: [company.name],
      details: [["NIT", company.nit], ["Municipio", company.municipality.name], ["Departamento", company.department.name],
        ["Estado", company.is_active ? "Activa" : "Inactiva"]],
      edit: { type: "company" }, add: { type: "site" }, addLabel: "Agregar sede",
    };
  } else if (node.kind === "site") {
    const { site } = node;
    view = {
      kind: "SEDE", icon: "map-pin", name: site.name, path: [company.name, site.name],
      details: [["Municipio", site.municipality.name], ["Departamento", site.department.name], ["Dirección", or(site.address)],
        ["Áreas", String(site.areas.length)]],
      edit: { type: "site", site }, add: { type: "area", siteId: site.id }, addLabel: "Agregar área",
    };
  } else if (node.kind === "area") {
    const { site, area } = node;
    view = {
      kind: "ÁREA", icon: "layout-list", name: area.name, path: [company.name, site.name, area.name],
      details: [["Sede", site.name], ["Descripción", or(area.description)], ["Puestos", String(area.positions.length)]],
      edit: { type: "area", siteId: site.id, area }, add: { type: "position", areaId: area.id }, addLabel: "Agregar puesto",
    };
  } else {
    const { site, area, position } = node;
    view = {
      kind: "PUESTO DE TRABAJO", icon: "users", name: position.name, path: [company.name, site.name, area.name, position.name],
      details: [["Sede", site.name], ["Área", area.name], ["Descripción", or(position.description)],
        ["Trabajadores activos", String(position.workers.filter((w) => w.is_active).length)]],
      edit: { type: "position", areaId: area.id, position }, add: { type: "worker", positionId: position.id }, addLabel: "Agregar trabajador",
    };
  }

  return (
    <div>
      <div className="mb-3 flex items-center gap-3">
        <span className="grid size-10 place-items-center rounded-lg bg-teal-50 text-teal-700"><Icon name={view.icon} /></span>
        <div className="min-w-0">
          <p className="text-xs font-bold tracking-wider text-slate-400">{view.kind}</p>
          <h2 className="truncate text-lg font-semibold">{view.name}</h2>
        </div>
      </div>
      <p className="mb-4 flex flex-wrap items-center gap-1 text-xs text-slate-500">
        {view.path.map((part, index) => index === view.path.length - 1
          ? <strong key={index} className="text-slate-700">{part}</strong>
          : <span key={index} className="inline-flex items-center gap-1">{part}<Icon name="chevron-right" className="size-3" /></span>)}
      </p>
      <dl className="mb-4 grid gap-3 sm:grid-cols-2">
        {view.details.map(([label, value]) => (
          <div key={label} className="rounded-lg bg-slate-50 px-3 py-2">
            <dt className="text-xs text-slate-500">{label}</dt>
            <dd className="text-sm font-medium text-slate-900">{value}</dd>
          </div>
        ))}
      </dl>
      {node.kind === "position" ? (
        <Workers workers={node.position.workers} canEdit={company.permissions.manage}
          onEdit={(worker) => onDialog({ type: "worker", positionId: node.position.id, worker })} />
      ) : null}
      {company.permissions.manage ? (
        <div className="flex flex-wrap justify-end gap-2 border-t border-slate-100 pt-4">
          <Button variant="secondary" onClick={() => onDialog(view.edit)}>Editar</Button>
          {company.is_active ? <Button onClick={() => onDialog(view.add)}><Icon name="plus" />{view.addLabel}</Button> : null}
        </div>
      ) : null}
    </div>
  );
}

function Workers({ workers, canEdit, onEdit }: { workers: Worker[]; canEdit: boolean; onEdit: (worker: Worker) => void }): ReactNode {
  const month = new Intl.DateTimeFormat("es-CO", { timeZone: "UTC", month: "short", year: "numeric" });
  return (
    <div className="mb-4">
      <h3 className="mb-2 text-sm font-semibold">Trabajadores del puesto</h3>
      {workers.length === 0 ? <p className="text-sm text-slate-500">Aún no hay trabajadores registrados en este puesto.</p> : (
        <ul className="divide-y divide-slate-100">
          {workers.map((worker) => (
            <li key={worker.id} className={`flex items-center gap-3 py-2.5 ${worker.is_active ? "" : "opacity-60"}`}>
              <Avatar text={worker.initials} />
              <span className="min-w-0 flex-1">
                <strong className="block truncate text-sm">{worker.full_name}</strong>
                <small className="block truncate text-slate-500">
                  {worker.document_display}
                  {worker.hired_on ? ` · desde ${month.format(new Date(`${worker.hired_on}T00:00:00Z`))}` : ""}
                  {worker.is_active ? "" : " · ya no está en el puesto"}
                </small>
              </span>
              {worker.is_active ? null : <Badge>Inactivo</Badge>}
              {canEdit ? (
                <button type="button" title="Editar" onClick={() => onEdit(worker)} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-900">
                  <Icon name="pencil" /><span className="sr-only">Editar {worker.full_name}</span>
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
