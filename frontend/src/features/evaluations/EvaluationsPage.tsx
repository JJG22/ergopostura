import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";

import { useAuth } from "../../auth/AuthContext";
import { CheckboxField, Grid, SelectField, TextAreaField, type Option } from "../../components/forms";
import { FormModal } from "../../components/Modal";
import { useNotify, usePageTitle } from "../../components/Page";
import { EmptyState, PageHead, Pagination, SearchBar, Table } from "../../components/Table";
import { Badge, Button, Card, ErrorState, Field, Icon, RiskBadge, Spinner } from "../../components/ui";
import { formatShortDate } from "../../lib/format";
import { useForm } from "../../lib/useForm";
import { useResource } from "../../lib/useResource";
import { evaluationsApi, type EvaluationDetail, type EvaluationInput, type EvaluationOptions } from "./api";

export function EvaluationsPage() {
  usePageTitle("Evaluaciones");
  const { can } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const page = Number(params.get("pagina") ?? "1") || 1;
  const fromVisit = params.get("visita");
  const [creating, setCreating] = useState(fromVisit !== null);
  const [resource, retry] = useResource((signal) => evaluationsApi.list({ q, page }, signal), [q, page]);

  const head = (
    <PageHead title="Evaluaciones" subtitle="Consulta los registros ergonómicos realizados con el método RULA."
      action={can("evaluation.manage") ? <Button onClick={() => setCreating(true)}><Icon name="plus" />Nueva evaluación</Button> : null} />
  );
  const modal = creating ? (
    <EvaluationFormModal {...(fromVisit ? { visit: fromVisit } : {})} onClose={() => setCreating(false)}
      onSaved={(id) => navigate(`/evaluaciones/${id}`)} />
  ) : null;
  if (resource.state === "error") return <>{head}<ErrorState error={resource.error} onRetry={retry} />{modal}</>;

  return (
    <>
      {head}
      <Card>
        <SearchBar key={q} query={q} label="Buscar evaluaciones" placeholder="Buscar código, empresa o puesto"
          onSearch={(text) => setParams(text ? { q: text } : {})} />
        {resource.state === "loading" ? <Spinner /> : resource.data.results.length === 0 ? (
          <EmptyState icon="clipboard-check" title={q ? "No hay resultados" : "Aún no hay evaluaciones"}>{q ? "Prueba con otra búsqueda." : undefined}</EmptyState>
        ) : (
          <>
            <Table head={["Evaluación", "Empresa", "Área y puesto", "Fecha", "Riesgo", "Estado"]}>
              {resource.data.results.map((e) => (
                <tr key={e.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3"><Link to={`/evaluaciones/${e.id}`} className="font-semibold text-slate-900 hover:text-teal-700">{e.code}</Link></td>
                  <td className="px-5 py-3">{e.company}</td>
                  <td className="px-5 py-3 text-slate-600">{e.area} · {e.position}</td>
                  <td className="whitespace-nowrap px-5 py-3">{formatShortDate(e.evaluated_on)}</td>
                  <td className="px-5 py-3"><RiskBadge risk={e.risk} /></td>
                  <td className="px-5 py-3"><Badge tone={e.status === "borrador" ? "amber" : "teal"}>{e.status_label}</Badge></td>
                </tr>
              ))}
            </Table>
            <Pagination page={resource.data} noun="evaluaciones"
              onPage={(next) => setParams({ ...(q ? { q } : {}), ...(next > 1 ? { pagina: String(next) } : {}) })} />
          </>
        )}
      </Card>
      {modal}
    </>
  );
}

const blankOptions: EvaluationOptions = { visits: [], areas: [], positions: [], workers: [], area_hint: "", evaluated_on: null };

/**
 * Crear o editar los datos de la evaluación. Visita > área > puesto > trabajador se piden al
 * servidor con cada cambio: así nunca se ofrece un puesto de otra sede.
 */
export function EvaluationFormModal({ evaluation, visit, onClose, onSaved }: {
  evaluation?: EvaluationDetail; visit?: string; onClose: () => void; onSaved: (id: number) => void;
}) {
  const notify = useNotify();
  const form = useForm<EvaluationInput>(evaluation ? {
    visit: String(evaluation.visit_id), area: String(evaluation.area_id), position: String(evaluation.position_id),
    worker: evaluation.worker ? String(evaluation.worker.id) : "", evaluated_on: evaluation.evaluated_on,
    activity_description: evaluation.activity_description, worker_context: evaluation.worker_context,
    carries_load: evaluation.carries_load, load_weight_kg: evaluation.load_weight_kg === null ? "" : String(evaluation.load_weight_kg),
    repetitive_movements: evaluation.repetitive_movements, repetition_notes: evaluation.repetition_notes,
  } : {
    visit: visit ?? "", area: "", position: "", worker: "", evaluated_on: "", activity_description: "", worker_context: "",
    carries_load: false, load_weight_kg: "", repetitive_movements: false, repetition_notes: "",
  });
  const { values, set } = form;
  const [options, setOptions] = useState<EvaluationOptions | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    evaluationsApi.options({ visit: values.visit, area: values.area, position: values.position, ...(evaluation ? { evaluation: evaluation.id } : {}) }, controller.signal)
      .then((data) => {
        setOptions(data);
        // La fecha propuesta es la de la visita, mientras el usuario no haya escrito otra.
        if (!evaluation && data.evaluated_on) form.setValues((current) => (current.evaluated_on ? current : { ...current, evaluated_on: data.evaluated_on ?? "" }));
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, [values.visit, values.area, values.position]);

  const choose = (name: "visit" | "area" | "position", value: string) => {
    form.setValues((current) => {
      const next = { ...current, [name]: value };
      // Cambiar un nivel limpia los que dependen de él.
      if (name === "visit") Object.assign(next, { area: "", position: "", worker: "", evaluated_on: "" });
      if (name === "area") Object.assign(next, { position: "", worker: "" });
      if (name === "position") next.worker = "";
      return next;
    });
  };

  async function save() {
    const result = await form.submit((input) => (evaluation ? evaluationsApi.update(evaluation.id, input) : evaluationsApi.create(input)));
    if (result) {
      notify(evaluation ? "Evaluación actualizada" : "Evaluación creada");
      onSaved(result.id);
    }
  }

  const opts = options ?? blankOptions;
  const waiting = (list: Option[], previous: string, label: string) => (previous ? (list.length ? label : "No hay opciones") : label);
  return (
    <FormModal wide title={evaluation ? "Editar evaluación" : "Nueva evaluación"} submitLabel={evaluation ? "Guardar" : "Crear evaluación"}
      note={evaluation ? undefined : "Parte de una visita realizada. Después agregarás las posturas, sus fotografías y el análisis RULA."}
      sending={form.sending} error={form.error} onClose={onClose} onSubmit={() => void save()}>
      <SelectField id="visit" label="Visita realizada" placeholder="Selecciona la visita" options={opts.visits} value={values.visit}
        hint="Solo aparecen visitas registradas como realizadas." onChange={(e) => choose("visit", e.target.value)} error={form.fieldError("visit")} />
      <Grid>
        <SelectField id="area" label="Área de trabajo" options={opts.areas} value={values.area} disabled={!values.visit}
          placeholder={values.visit ? "Selecciona un área" : "Selecciona primero la visita"} hint={opts.area_hint || undefined}
          onChange={(e) => choose("area", e.target.value)} error={form.fieldError("area")} />
        <SelectField id="position" label="Puesto de trabajo" options={opts.positions} value={values.position} disabled={!values.area}
          placeholder={values.area ? waiting(opts.positions, values.area, "Selecciona un puesto") : "Selecciona primero un área"}
          onChange={(e) => choose("position", e.target.value)} error={form.fieldError("position")} />
      </Grid>
      <Grid>
        <SelectField id="worker" label="Trabajador observado (opcional)" options={opts.workers} value={values.worker} disabled={!values.position}
          placeholder={values.position ? "Sin indicar" : "Selecciona primero un puesto"}
          onChange={(e) => set("worker", e.target.value)} error={form.fieldError("worker")} />
        <Field id="evaluated_on" label="Fecha de la evaluación" type="date" value={values.evaluated_on}
          onChange={(e) => set("evaluated_on", e.target.value)} error={form.fieldError("evaluated_on")} />
      </Grid>
      <TextAreaField id="activity_description" label="Actividad observada" value={values.activity_description}
        hint="Qué hace el trabajador durante la actividad evaluada." onChange={(e) => set("activity_description", e.target.value)}
        error={form.fieldError("activity_description")} />
      <TextAreaField id="worker_context" label="Contexto del trabajador (opcional)" rows={2} value={values.worker_context}
        hint="Solo lo necesario para el análisis. No escribas nombres, documentos ni diagnósticos."
        onChange={(e) => set("worker_context", e.target.value)} error={form.fieldError("worker_context")} />
      <CheckboxField id="carries_load" label="La actividad incluye levantar o cargar peso" checked={values.carries_load}
        onChange={(checked) => form.setValues((c) => ({ ...c, carries_load: checked, load_weight_kg: checked ? c.load_weight_kg : "" }))} />
      {values.carries_load ? (
        <Field id="load_weight_kg" label="Peso aproximado en kg (opcional)" type="number" min={0} step={0.01} inputMode="decimal"
          value={values.load_weight_kg} hint="Déjalo vacío si no se conoce." onChange={(e) => set("load_weight_kg", e.target.value)}
          error={form.fieldError("load_weight_kg")} />
      ) : null}
      <CheckboxField id="repetitive_movements" label="Se observan movimientos repetitivos" checked={values.repetitive_movements}
        onChange={(checked) => set("repetitive_movements", checked)} />
      {values.repetitive_movements ? (
        <Field id="repetition_notes" label="Detalle de la repetición (opcional)" value={values.repetition_notes}
          onChange={(e) => set("repetition_notes", e.target.value)} error={form.fieldError("repetition_notes")} />
      ) : null}
    </FormModal>
  );
}
