import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";

import { toApiError, type ApiError } from "../../api/client";
import { FieldShell, Grid, SelectField, TextAreaField, controlClass } from "../../components/forms";
import { FormAlert } from "../../components/Modal";
import { useNotify, usePageTitle } from "../../components/Page";
import { Button, Card, ErrorState, Field, Icon, Spinner } from "../../components/ui";
import { useForm } from "../../lib/useForm";
import { useResource } from "../../lib/useResource";
import { CONTRACT_FIELDS, contractsApi, type ContractDetail, type ContractOptions, type ContractValues, type Reading } from "./api";

const EMPTY: ContractValues = Object.fromEntries(CONTRACT_FIELDS.map((name) => [name, ""])) as ContractValues;

function fromContract(contract: ContractDetail): ContractValues {
  return {
    company: String(contract.company.id), code: contract.code_value, kind: contract.kind,
    start_date: contract.start_date, end_date: contract.end_date, value: contract.value === null ? "" : String(contract.value),
    service: contract.service, responsible_name: contract.responsible_name, responsible_role: contract.responsible_role,
    responsible_email: contract.responsible_email, responsible_phone: contract.responsible_phone, notes: contract.notes,
  };
}

/** Registro y edición. Carga primero las opciones (y el contrato, si se edita). */
export function ContractFormPage() {
  const id = useParams().id;
  const editing = id !== undefined;
  usePageTitle(editing ? "Editar contrato" : "Registrar contrato");
  const [resource, retry] = useResource(async (signal) => {
    const [options, contract] = await Promise.all([
      contractsApi.options(signal),
      editing ? contractsApi.get(Number(id), signal) : Promise.resolve(null),
    ]);
    return { options, contract };
  }, [id]);

  if (resource.state === "loading") return <Spinner />;
  if (resource.state === "error") return <ErrorState error={resource.error} onRetry={retry} />;
  return <ContractForm options={resource.data.options} contract={resource.data.contract} />;
}

function ContractForm({ options, contract }: { options: ContractOptions; contract: ContractDetail | null }) {
  const navigate = useNavigate();
  const notify = useNotify();
  const [params] = useSearchParams();
  const preset = params.get("empresa") ?? "";
  const initial = contract ? fromContract(contract) : { ...EMPTY, kind: options.kinds[0]?.value ?? "", company: options.companies.some((c) => String(c.id) === preset) ? preset : "" };
  const form = useForm<ContractValues>(initial);
  const [document, setDocument] = useState<File | null>(null);
  const [suggested, setSuggested] = useState<Set<string>>(new Set());
  const [reading, setReading] = useState<{ state: "idle" } | { state: "busy" } | { state: "done"; result: Reading; filled: number } | { state: "error"; error: ApiError }>({ state: "idle" });
  const { values } = form;
  const back = contract ? `/contratos/${contract.id}` : "/contratos";

  const set = (name: keyof ContractValues, value: string) => {
    form.set(name, value);
    setSuggested((current) => {
      if (!current.has(name)) return current;
      const next = new Set(current);
      next.delete(name);
      return next;
    });
  };

  async function read() {
    if (!document) return;
    setReading({ state: "busy" });
    try {
      const result = await contractsApi.read(document);
      const filled = new Set<string>();
      form.setValues((current) => {
        const next = { ...current };
        for (const [name, value] of Object.entries(result.fields)) {
          if (value === null || value === undefined || value === "") continue;
          if (name === "company" && contract) continue;
          next[name as keyof ContractValues] = String(value);
          filled.add(name);
        }
        return next;
      });
      setSuggested(filled);
      setReading({ state: "done", result, filled: filled.size });
    } catch (cause) {
      setReading({ state: "error", error: toApiError(cause) });
    }
  }

  async function save() {
    const result = await form.submit(async (input) => {
      if (contract) {
        const { company: _company, ...rest } = input;
        return contractsApi.update(contract.id, rest, document);
      }
      return contractsApi.create(input, document);
    });
    if (result) {
      notify(contract ? "Contrato actualizado" : "Contrato registrado");
      navigate(`/contratos/${result.id}`);
    }
  }

  const err = (name: string) => form.error?.field(name);
  const mark = (name: string) => (suggested.has(name) ? "Sugerido por la IA: revísalo." : undefined);

  return (
    <div className="mx-auto max-w-3xl">
      <Link to={back} className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700 hover:underline">
        <Icon name="arrow-left" className="size-4" />Volver
      </Link>
      <h1 className="text-2xl font-bold">{contract ? `Editar contrato ${contract.code}` : "Registrar contrato"}</h1>
      <p className="mb-5 mt-1 text-sm text-slate-500">Los datos registrados son los que valen; lo que lea la IA es una ayuda que debes revisar.</p>

      <Card>
        <form noValidate onSubmit={(event) => { event.preventDefault(); void save(); }}>
          <FormAlert error={form.error} />

          <FieldShell id="document" label="Contrato firmado (PDF)" error={err("document")}
            hint={contract ? "Déjalo vacío para conservar el documento actual. Máximo 10 MB." : "Máximo 10 MB."}>
            <input id="document" type="file" accept="application/pdf" className={`py-2 ${controlClass(err("document"))}`}
              onChange={(event) => { setDocument(event.target.files?.[0] ?? null); setReading({ state: "idle" }); }} />
          </FieldShell>

          {options.ai_ready ? (
            <div className="mb-5 rounded-xl border border-violet-200 bg-violet-50/60 p-4">
              <div className="flex flex-wrap items-center gap-3">
                <span className="grid size-9 place-items-center rounded-lg bg-violet-100 text-violet-700"><Icon name="sparkles" /></span>
                <div className="min-w-0 flex-1">
                  <strong className="block text-sm">Leer el contrato con IA</strong>
                  <small className="text-slate-600">La IA propone fechas, tipo, servicio, encargado y valor. El documento se envía a Anthropic (Claude) para leerlo; revisa cada dato antes de guardar.</small>
                </div>
                <Button type="button" variant="secondary" disabled={!document || reading.state === "busy"} onClick={() => void read()}>
                  <Icon name="sparkles" />{reading.state === "busy" ? "Leyendo…" : "Leer contrato"}
                </Button>
              </div>
              <div aria-live="polite" className="mt-2 text-sm">
                {reading.state === "busy" ? <p className="text-violet-800">Leyendo el contrato. Puede tardar entre 10 y 40 segundos…</p> : null}
                {reading.state === "error" ? <p className="font-medium text-red-700">{reading.error.message}</p> : null}
                {reading.state === "done" ? <ReadingResult reading={reading.result} filled={reading.filled} /> : null}
              </div>
            </div>
          ) : (
            <p className="mb-5 rounded-lg bg-slate-50 px-3 py-2.5 text-sm text-slate-600">La lectura con IA no está configurada en este servidor. Registra los datos a mano.</p>
          )}

          {contract ? (
            <p className="mb-4 text-sm"><span className="text-slate-500">Empresa:</span> <strong>{contract.company.name}</strong></p>
          ) : (
            <SelectField id="company" label="Empresa" placeholder="Selecciona la empresa" value={values.company}
              options={options.companies.map((c) => ({ value: String(c.id), label: c.name }))}
              onChange={(e) => set("company", e.target.value)} error={err("company")} hint={mark("company")} />
          )}
          <Grid>
            <Field id="code" label="Número o código (opcional)" placeholder="Ej. CPS-2026-014" value={values.code}
              onChange={(e) => set("code", e.target.value)} error={err("code")} hint={mark("code") ?? ""} />
            <SelectField id="kind" label="Tipo de contrato" options={options.kinds} value={values.kind}
              onChange={(e) => set("kind", e.target.value)} error={err("kind")} hint={mark("kind")} />
            <Field id="start_date" label="Inicio de la vigencia" type="date" value={values.start_date}
              onChange={(e) => set("start_date", e.target.value)} error={err("start_date")} hint={mark("start_date") ?? ""} />
            <Field id="end_date" label="Fin de la vigencia" type="date" value={values.end_date}
              onChange={(e) => set("end_date", e.target.value)} error={err("end_date")} hint={mark("end_date") ?? ""} />
          </Grid>
          <Field id="value" label="Valor total en COP (opcional)" type="number" min={0} step={1} inputMode="numeric" value={values.value}
            onChange={(e) => set("value", e.target.value)} error={err("value")} hint={mark("value") ?? ""} />
          <TextAreaField id="service" label="Servicio contratado" value={values.service} hint={mark("service") ?? "Qué se evaluará y con qué alcance, según el contrato."}
            onChange={(e) => set("service", e.target.value)} error={err("service")} />
          <Grid>
            <Field id="responsible_name" label="Encargado por la empresa" value={values.responsible_name}
              onChange={(e) => set("responsible_name", e.target.value)} error={err("responsible_name")} hint={mark("responsible_name") ?? ""} />
            <Field id="responsible_role" label="Cargo del encargado (opcional)" value={values.responsible_role}
              onChange={(e) => set("responsible_role", e.target.value)} error={err("responsible_role")} hint={mark("responsible_role") ?? ""} />
            <Field id="responsible_email" label="Correo del encargado (opcional)" type="email" value={values.responsible_email}
              onChange={(e) => set("responsible_email", e.target.value)} error={err("responsible_email")} hint={mark("responsible_email") ?? ""} />
            <Field id="responsible_phone" label="Teléfono del encargado (opcional)" value={values.responsible_phone}
              onChange={(e) => set("responsible_phone", e.target.value)} error={err("responsible_phone")} hint={mark("responsible_phone") ?? ""} />
          </Grid>
          <TextAreaField id="notes" label="Notas (opcional)" rows={2} value={values.notes}
            onChange={(e) => set("notes", e.target.value)} error={err("notes")} />

          <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
            <Link to={back} className="inline-flex h-10 items-center rounded-lg border border-slate-300 px-4 text-sm font-semibold hover:bg-slate-50">Cancelar</Link>
            <Button type="submit" disabled={form.sending}>{form.sending ? "Guardando…" : contract ? "Guardar cambios" : "Guardar contrato"}</Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

function ReadingResult({ reading, filled }: { reading: Reading; filled: number }) {
  return (
    <div className="space-y-2 text-slate-700">
      <p className="font-medium text-teal-800">Se llenaron {filled} campos. Revísalos antes de guardar.</p>
      {reading.summary ? <p>{reading.summary}</p> : null}
      {reading.client_nit && !reading.company_found ? (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-amber-900">El NIT del documento ({reading.client_nit}) no corresponde a ninguna empresa registrada. Regístrala antes de guardar el contrato.</p>
      ) : !reading.fields.company && reading.client ? (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-amber-900">No se identificó la empresa «{reading.client}». Elígela en la lista.</p>
      ) : null}
      {reading.alerts.length ? (
        <div><strong>Para revisar</strong><ul className="ml-5 list-disc">{reading.alerts.map((a) => <li key={a}>{a}</li>)}</ul></div>
      ) : null}
    </div>
  );
}
