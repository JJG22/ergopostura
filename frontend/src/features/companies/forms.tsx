import { CheckboxField, Grid, SelectField, TextAreaField, type Option } from "../../components/forms";
import { FormModal } from "../../components/Modal";
import { useNotify } from "../../components/Page";
import { Field } from "../../components/ui";
import { useForm } from "../../lib/useForm";
import { LocationFields } from "../geography/LocationFields";
import {
  companiesApi,
  type CompanyDetail,
  type CompanyInput,
  type Level,
  type NamedInput,
  type Saved,
  type Site,
  type SiteInput,
  type Worker,
  type WorkerInput,
} from "./api";

interface Done<T> {
  onClose: () => void;
  onSaved: (result: T) => void;
}

export function CompanyFormModal({ company, onClose, onSaved }: Done<{ id: number }> & { company?: CompanyDetail }) {
  const notify = useNotify();
  const form = useForm<CompanyInput>(company
    ? { name: company.name, nit: company.nit, department: String(company.department.id), municipality: String(company.municipality.id), is_active: company.is_active }
    : { name: "", nit: "", department: "", municipality: "" });
  const { values, set } = form;

  async function save() {
    const result = await form.submit((input) => (company ? companiesApi.update(company.id, input) : companiesApi.create(input)));
    if (result) {
      notify(company ? "Empresa actualizada" : "Empresa registrada");
      onSaved(result);
    }
  }

  return (
    <FormModal title={company ? "Editar empresa" : "Registrar empresa"} submitLabel={company ? "Guardar" : "Registrar empresa"}
      note={company ? undefined : "Las sedes son opcionales. Podrás agregarlas después desde el detalle de la empresa."}
      sending={form.sending} error={form.error} onClose={onClose} onSubmit={() => void save()}>
      <Field id="name" label="Razón social" placeholder="Ej. Café Montaña S.A.S." value={values.name}
        onChange={(e) => set("name", e.target.value)} error={form.fieldError("name")} />
      <Field id="nit" label="NIT" placeholder="Ej. 900.123.456-8" value={values.nit}
        onChange={(e) => set("nit", e.target.value)} error={form.fieldError("nit")} />
      <Grid>
        <LocationFields department={values.department} municipality={values.municipality}
          onChange={(next) => form.setValues((current) => ({ ...current, ...next }))}
          errors={{ department: form.fieldError("department"), municipality: form.fieldError("municipality") }} />
      </Grid>
      {company ? (
        <CheckboxField id="is_active" label="Empresa activa" checked={values.is_active ?? true} onChange={(checked) => set("is_active", checked)}
          hint="Una empresa inactiva conserva su historia, pero no recibe estructura nueva ni agenda visitas." />
      ) : null}
    </FormModal>
  );
}

export function SiteFormModal({ companyId, site, defaultPlace, onClose, onSaved }: Done<Saved> & {
  companyId: number; site?: Site; defaultPlace: { department: string; municipality: string };
}) {
  const notify = useNotify();
  const form = useForm<SiteInput>(site
    ? { name: site.name, address: site.address, department: String(site.department.id), municipality: String(site.municipality.id) }
    // Lo usual es que la sede quede donde está la empresa; se puede cambiar.
    : { name: "", address: "", ...defaultPlace });
  const { values, set } = form;

  async function save() {
    const result = await form.submit((input) =>
      site ? companiesApi.updateChild("sites", site.id, input) : companiesApi.createChild("sites", companyId, input));
    if (result) {
      notify(site ? "Cambios guardados" : "Sede registrada");
      onSaved(result);
    }
  }

  return (
    <FormModal title={site ? "Editar sede" : "Agregar sede"} sending={form.sending} error={form.error}
      onClose={onClose} onSubmit={() => void save()}>
      <Field id="name" label="Nombre" placeholder="Ej. Planta Armenia" value={values.name}
        onChange={(e) => set("name", e.target.value)} error={form.fieldError("name")} />
      <Grid>
        <LocationFields department={values.department} municipality={values.municipality}
          onChange={(next) => form.setValues((current) => ({ ...current, ...next }))}
          errors={{ department: form.fieldError("department"), municipality: form.fieldError("municipality") }} />
      </Grid>
      <Field id="address" label="Dirección (opcional)" value={values.address}
        onChange={(e) => set("address", e.target.value)} error={form.fieldError("address")} />
    </FormModal>
  );
}

const NAMED: Record<"areas" | "positions", { noun: string; created: string; placeholder: string }> = {
  areas: { noun: "área", created: "Área registrada", placeholder: "Ej. Empaque" },
  positions: { noun: "puesto de trabajo", created: "Puesto registrado", placeholder: "Ej. Operario de empaque" },
};

/** Área y puesto comparten forma: nombre único entre hermanos y descripción opcional. */
export function NamedFormModal({ level, parentId, item, onClose, onSaved }: Done<Saved> & {
  level: "areas" | "positions"; parentId: number; item?: { id: number; name: string; description: string };
}) {
  const notify = useNotify();
  const text = NAMED[level];
  const form = useForm<NamedInput>({ name: item?.name ?? "", description: item?.description ?? "" });
  const { values, set } = form;

  async function save() {
    const result = await form.submit((input) =>
      item ? companiesApi.updateChild(level, item.id, input) : companiesApi.createChild(level, parentId, input));
    if (result) {
      notify(item ? "Cambios guardados" : text.created);
      onSaved(result);
    }
  }

  return (
    <FormModal title={`${item ? "Editar" : "Agregar"} ${text.noun}`} sending={form.sending} error={form.error}
      onClose={onClose} onSubmit={() => void save()}>
      <Field id="name" label="Nombre" placeholder={text.placeholder} value={values.name}
        onChange={(e) => set("name", e.target.value)} error={form.fieldError("name")} />
      <TextAreaField id="description" label="Descripción (opcional)" value={values.description}
        onChange={(e) => set("description", e.target.value)} error={form.fieldError("description")} />
    </FormModal>
  );
}

export function WorkerFormModal({ positionId, worker, documentTypes, onClose, onSaved }: Done<Saved> & {
  positionId: number; worker?: Worker; documentTypes: Option[];
}) {
  const notify = useNotify();
  const form = useForm<WorkerInput>(worker
    ? { first_name: worker.first_name, last_name: worker.last_name, document_type: worker.document_type,
        document_number: worker.document_number, hired_on: worker.hired_on, is_active: worker.is_active }
    : { first_name: "", last_name: "", document_type: "CC", document_number: "", hired_on: null });
  const { values, set } = form;
  const level: Level = "workers";

  async function save() {
    const result = await form.submit((input) =>
      worker ? companiesApi.updateChild(level, worker.id, input) : companiesApi.createChild(level, positionId, input));
    if (result) {
      notify(worker ? "Cambios guardados" : "Trabajador registrado");
      onSaved(result);
    }
  }

  return (
    <FormModal title={worker ? "Editar trabajador" : "Agregar trabajador"} sending={form.sending} error={form.error}
      note={worker ? undefined : "Son datos personales: solo los verán el ingeniero y la propia empresa."}
      onClose={onClose} onSubmit={() => void save()}>
      <Grid>
        <Field id="first_name" label="Nombres" autoComplete="off" value={values.first_name}
          onChange={(e) => set("first_name", e.target.value)} error={form.fieldError("first_name")} />
        <Field id="last_name" label="Apellidos" autoComplete="off" value={values.last_name}
          onChange={(e) => set("last_name", e.target.value)} error={form.fieldError("last_name")} />
        <SelectField id="document_type" label="Tipo de documento" options={documentTypes} value={values.document_type}
          onChange={(e) => set("document_type", e.target.value)} error={form.fieldError("document_type")} />
        <Field id="document_number" label="Número de documento" inputMode="numeric" autoComplete="off" value={values.document_number}
          onChange={(e) => set("document_number", e.target.value)} error={form.fieldError("document_number")} />
      </Grid>
      <Field id="hired_on" label="Fecha de ingreso al puesto (opcional)" type="date" value={values.hired_on ?? ""}
        onChange={(e) => set("hired_on", e.target.value || null)} error={form.fieldError("hired_on")} />
      {worker ? (
        <CheckboxField id="is_active" label="Trabaja actualmente en el puesto" checked={values.is_active ?? true}
          onChange={(checked) => set("is_active", checked)} hint="Si ya no está, se conserva en la historia del puesto." />
      ) : null}
    </FormModal>
  );
}
