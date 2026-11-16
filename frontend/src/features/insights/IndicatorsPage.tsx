import { useSearchParams } from "react-router";

import { api, withQuery } from "../../api/client";
import { usePageTitle } from "../../components/Page";
import { EmptyState, PageHead, Table } from "../../components/Table";
import { Card, ErrorState, Icon, SectionHead, Spinner } from "../../components/ui";
import { useResource } from "../../lib/useResource";

interface Distribution {
  green: number;
  yellow: number;
  red: number;
  total: number;
  follow_up: number;
  follow_up_percent: number;
}

interface RiskRow {
  id: number | null;
  label: string;
  risk: Distribution;
}

interface Indicators {
  totals: Distribution;
  company_count: number;
  area_count: number;
  shows_all_companies: boolean;
  selected_company: { id: number; name: string } | null;
  companies: RiskRow[];
  areas: RiskRow[] | null;
}

const COLORS = { green: "#10b981", yellow: "#f59e0b", red: "#dc2626" } as const;

export function IndicatorsPage() {
  usePageTitle("Indicadores");
  const [params, setParams] = useSearchParams();
  const company = params.get("empresa") ?? "";
  const [resource, retry] = useResource((signal) => api<Indicators>(withQuery("/indicators/", { company }), { signal }), [company]);

  const head = <PageHead title="Indicadores" subtitle="Reconoce dónde se concentran las dificultades ergonómicas por empresa y área." />;
  if (resource.state === "loading") return <>{head}<Spinner /></>;
  if (resource.state === "error") return <>{head}<ErrorState error={resource.error} onRetry={retry} /></>;
  const data = resource.data;

  return (
    <>
      {head}
      <div className="mb-6 grid gap-px overflow-hidden rounded-lg border border-ink-200 bg-ink-200 sm:grid-cols-3">
        <Metric label="Puestos evaluados" value={data.totals.total} detail={`En ${data.area_count} área${data.area_count === 1 ? "" : "s"}`} />
        <Metric label="Requieren seguimiento" value={data.totals.follow_up} detail={`${data.totals.follow_up_percent}% de los puestos evaluados`} />
        <Metric label="Empresas evaluadas" value={data.company_count} detail="Con evaluaciones terminadas" />
      </div>

      {data.shows_all_companies ? (
        <Card className="mb-5">
          <SectionHead title="Por empresa" subtitle="Elige una empresa para comparar sus áreas" />
          {data.companies.length ? (
            <RiskTable first="Empresa" rows={data.companies} selected={data.selected_company?.id ?? null}
              onSelect={(id) => setParams({ empresa: String(id) })} />
          ) : <EmptyState icon="chart-column" title="Aún no hay evaluaciones terminadas" />}
        </Card>
      ) : null}

      {data.areas !== null ? (
        <Card className="mb-5">
          <SectionHead title="Comparación entre áreas" subtitle={data.selected_company?.name || "Tu empresa"}
            action={data.shows_all_companies ? (
              <button type="button" onClick={() => setParams({})} className="text-sm font-semibold text-brand-700 hover:underline">Quitar selección</button>
            ) : undefined} />
          {data.areas.length ? <RiskTable first="Sede y área" rows={data.areas} selected={null} /> : (
            <p className="text-sm text-ink-500">Esta empresa aún no tiene áreas registradas.</p>
          )}
        </Card>
      ) : null}

      <p className="flex gap-2 text-sm text-ink-500">
        <Icon name="circle-exclamation-point" className="mt-0.5 size-4" />
        <span>Cada puesto cuenta una vez: se toma la evaluación terminada más reciente de cada puesto y, dentro de ella, la postura de mayor riesgo. No se promedian puntajes, porque RULA no lo define.</span>
      </p>
    </>
  );
}

function Metric({ label, value, detail }: { label: string; value: number; detail: string }) {
  return (
    <div className="min-w-0 bg-white px-5 py-5">
      <small className="block text-sm font-medium text-ink-600">{label}</small>
      <strong className="mt-3 block font-display text-[2rem] sm:text-[2.5rem] font-bold leading-none tabular text-ink-950">{value}</strong>
      <span className="mt-2 block text-xs text-ink-500">{detail}</span>
    </div>
  );
}

function Dot({ color }: { color: keyof typeof COLORS }) {
  return <span className="mr-1.5 inline-block size-2.5 rounded-full align-middle" style={{ background: COLORS[color] }} aria-hidden="true" />;
}

function RiskTable({ first, rows, selected, onSelect }: { first: string; rows: RiskRow[]; selected: number | null; onSelect?: (id: number) => void }) {
  return (
    <Table head={[first, "Puestos", "Adecuado", "Revisión", "Intervención", "Distribución"]}>
      {rows.map((row) => (
        <tr key={row.label} className={row.id !== null && row.id === selected ? "bg-brand-50" : ""}>
          <td className="px-5 py-3">
            {row.id !== null && onSelect ? (
              <button type="button" onClick={() => onSelect(row.id as number)} className="text-left font-semibold text-brand-700 hover:underline">{row.label}</button>
            ) : <strong>{row.label}</strong>}
          </td>
          {row.risk.total ? (
            <>
              <td className="px-5 py-3 tabular-nums">{row.risk.total}</td>
              <td className="px-5 py-3 tabular-nums"><Dot color="green" />{row.risk.green}</td>
              <td className="px-5 py-3 tabular-nums"><Dot color="yellow" />{row.risk.yellow}</td>
              <td className="px-5 py-3 tabular-nums"><Dot color="red" />{row.risk.red}</td>
              <td className="px-5 py-3">
                <div className="flex h-2.5 w-40 gap-px overflow-hidden rounded-sm bg-ink-100" aria-hidden="true">
                  {(["green", "yellow", "red"] as const).map((color) => row.risk[color] ? (
                    <i key={color} style={{ flexGrow: row.risk[color], background: COLORS[color] }} title={`${color === "green" ? "Adecuado" : color === "yellow" ? "Revisión" : "Intervención"}: ${row.risk[color]}`} />
                  ) : null)}
                </div>
              </td>
            </>
          ) : <td colSpan={5} className="px-5 py-3 text-ink-400">Sin evaluaciones terminadas</td>}
        </tr>
      ))}
    </Table>
  );
}
