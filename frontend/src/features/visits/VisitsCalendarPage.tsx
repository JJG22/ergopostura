import { useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router";

import type { Level } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { usePageTitle } from "../../components/Page";
import { PageHead } from "../../components/Table";
import { Badge, Button, Card, ErrorState, Icon, linkButtonClass, SectionHead, Spinner } from "../../components/ui";
import { formatLongDate, formatTime } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { colorOf, visitsApi, type Calendar, type CalendarDay, type CalendarEvent, type ScheduleInfo, type VisitRow } from "./api";
import { VisitDetailModal, VisitFormModal } from "./VisitModals";

const shortMonth = new Intl.DateTimeFormat("es-CO", { timeZone: "America/Bogota", month: "short" });
const weekdayLong = new Intl.DateTimeFormat("es-CO", { timeZone: "America/Bogota", weekday: "long" });
const dayLabel = new Intl.DateTimeFormat("es-CO", { timeZone: "UTC", day: "numeric", month: "long" });
const dayNumber = (date: string) => Number(date.slice(8, 10));
const labelOf = (date: string) => dayLabel.format(new Date(`${date}T00:00:00Z`));

/** Encabezado y avisos comunes al calendario y a la agenda. */
export function VisitsHeader({ info, onSchedule }: { info: ScheduleInfo; onSchedule: () => void }) {
  const { can } = useAuth();
  return (
    <>
      <PageHead title="Visitas"
        subtitle={can("visit.view_all")
          ? "Las empresas agendan sus visitas; aquí ves cuándo y dónde te esperan. Registra cada visita al terminarla para poder evaluar."
          : "Agenda la visita del ingeniero en una de tus sedes. Los horarios ocupados aparecen en gris."}
        action={info.can_schedule ? <Button onClick={onSchedule}><Icon name="plus" />Agendar visita</Button> : null} />
      {info.blocker ? (
        <Notice tone="amber">{info.blocker}</Notice>
      ) : info.schedules ? (
        info.contract ? (
          <Notice tone="neutral" icon="file-signature">
            Contrato {info.contract.code}: puedes agendar visitas entre el {formatLongDate(info.contract.start_date)} y el {formatLongDate(info.contract.end_date)}.
          </Notice>
        ) : <Notice tone="amber">Tu empresa no tiene un contrato vigente. Comunícate con el ingeniero para renovarlo antes de agendar.</Notice>
      ) : null}
    </>
  );
}

function Notice({ tone, icon = "circle-exclamation-point", children }: { tone: "amber" | "neutral"; icon?: string; children: ReactNode }) {
  return (
    <div role="status" className={`mb-4 flex gap-2.5 rounded-2xl px-4 py-3 text-sm ${tone === "amber" ? "bg-amber-50 text-amber-900" : "bg-ink-100 text-ink-700"}`}>
      <Icon name={icon} className="mt-0.5 size-4" /><span>{children}</span>
    </div>
  );
}

export function LevelBadge({ level }: { level: Level }) {
  return <Badge tone={level.tone} dot>{level.label}</Badge>;
}

type Dialog = { type: "visit"; id: number } | { type: "new"; date?: string; hour?: number } | null;

export function VisitsCalendarPage() {
  usePageTitle("Visitas");
  const [params, setParams] = useSearchParams();
  const view = params.get("vista") === "semana" ? "semana" : "mes";
  const date = params.get("fecha") ?? "";
  const [resource, retry, refresh] = useResource((signal) => visitsApi.calendar({ view, date }, signal), [view, date]);
  const opened = Number(params.get("visita") ?? "") || null;
  const [dialog, setDialog] = useState<Dialog>(null);
  const active: Dialog = dialog ?? (opened ? { type: "visit", id: opened } : null);

  const go = (nextView: string, nextDate?: string) => {
    const values: Record<string, string> = {};
    if (nextView === "semana") values.vista = "semana";
    if (nextDate) values.fecha = nextDate;
    setParams(values);
  };
  const close = () => {
    setDialog(null);
    if (opened) {
      const next = new URLSearchParams(params);
      next.delete("visita");
      setParams(next, { replace: true });
    }
  };
  // Tras agendar o reprogramar, el calendario va a la fecha de la visita para que se vea dónde quedó.
  const saved = (startsAt?: string) => {
    if (startsAt) {
      setDialog(null);
      go(view, startsAt.slice(0, 10));
    }
    refresh();
  };

  if (resource.state === "loading") return <Spinner />;
  if (resource.state === "error") return <ErrorState error={resource.error} onRetry={retry} />;
  const cal = resource.data;

  return (
    <>
      <VisitsHeader info={cal} onSchedule={() => setDialog({ type: "new" })} />
      <div className="grid gap-5 2xl:grid-cols-[minmax(0,1fr)_18rem]">
        <Card className="p-0!">
          <div className="flex flex-wrap items-center gap-2 border-b border-ink-200 p-4">
            <Button variant="secondary" onClick={() => go(view)}>Hoy</Button>
            <div className="flex">
              <button type="button" className="grid size-9 place-items-center hover:bg-ink-100" aria-label={view === "semana" ? "Semana anterior" : "Mes anterior"}
                onClick={() => go(view, cal.previous)}><Icon name="chevron-right" className="size-5 rotate-180" /></button>
              <button type="button" className="grid size-9 place-items-center hover:bg-ink-100" aria-label={view === "semana" ? "Semana siguiente" : "Mes siguiente"}
                onClick={() => go(view, cal.next)}><Icon name="chevron-right" className="size-5" /></button>
            </div>
            <h2 className="min-w-0 flex-1 text-lg font-semibold" aria-live="polite">{cal.title}</h2>
            <nav aria-label="Vista del calendario" className="flex border border-ink-950 text-sm font-semibold">
              {(["mes", "semana"] as const).map((option) => (
                <button key={option} type="button" aria-current={view === option ? "page" : undefined}
                  onClick={() => go(option, option === "semana" ? (cal.contains_today ? cal.today : cal.anchor) : cal.anchor)}
                  className={`px-4 py-2 transition-colors ${view === option ? "bg-ink-950 text-white" : "text-ink-700 hover:bg-ink-100"}`}>
                  {option === "mes" ? "Mes" : "Semana"}
                </button>
              ))}
              <Link to="/visitas/agenda" className="px-4 py-2 text-ink-700 hover:bg-ink-100">Agenda</Link>
            </nav>
          </div>
          {cal.view === "semana"
            ? <WeekGrid cal={cal} onOpen={(id) => setDialog({ type: "visit", id })} onAdd={(d, hour) => setDialog({ type: "new", date: d, hour })} />
            : <MonthGrid cal={cal} onOpen={(id) => setDialog({ type: "visit", id })} onAdd={(d) => setDialog({ type: "new", date: d })} onWeek={(d) => go("semana", d)} />}
          <Footer cal={cal} />
        </Card>
        <SidePanel cal={cal} onOpen={(id) => setDialog({ type: "visit", id })} />
      </div>
      {active?.type === "visit" ? <VisitDetailModal id={active.id} onClose={close} onChanged={saved} /> : null}
      {active?.type === "new" ? (
        <VisitFormModal preset={{ ...(active.date ? { date: active.date } : {}), ...(active.hour !== undefined ? { hour: active.hour } : {}) }}
          onClose={close} onSaved={saved} />
      ) : null}
    </>
  );
}

function Chip({ event, onOpen }: { event: CalendarEvent; onOpen: (id: number) => void }) {
  const time = formatTime(event.starts_at);
  if (event.busy) {
    return (
      <span title={`${time} · Horario ocupado`} className="flex items-center gap-1.5 truncate rounded bg-ink-100 px-1.5 py-0.5 text-xs text-ink-500">
        <span className="size-1.5 shrink-0 rounded-full bg-ink-400" /><b className="font-semibold">{time}</b><span className="truncate">Ocupado</span>
      </span>
    );
  }
  const color = colorOf(event.color);
  const cancelled = event.level?.key === "cancelada";
  return (
    <button type="button" onClick={() => event.id && onOpen(event.id)} title={`${time} · ${event.company ?? ""} · ${event.level?.label ?? ""}`}
      className={`flex w-full items-center gap-1.5 truncate rounded px-1.5 py-0.5 text-left text-xs hover:brightness-95 ${cancelled ? "line-through opacity-60" : ""}`}
      style={{ background: color.bg, color: color.fg }}>
      <span className="size-1.5 shrink-0 rounded-full" style={{ background: color.fg }} />
      <b className="font-semibold">{time}</b><span className="truncate">{event.title}</span>
    </button>
  );
}

function MonthGrid({ cal, onOpen, onAdd, onWeek }: { cal: Calendar; onOpen: (id: number) => void; onAdd: (date: string) => void; onWeek: (date: string) => void }) {
  const names = cal.days.slice(0, 7).map((d) => d.weekday);
  return (
    <div role="grid" aria-label={cal.title}>
      <div role="row" className="grid grid-cols-7 border-b border-ink-200 text-center text-xs font-medium text-ink-500 capitalize">
        {names.map((name) => (
          <div role="columnheader" key={name} className="py-2"><span className="hidden sm:inline">{name}</span><span className="sm:hidden" aria-hidden="true">{name.slice(0, 3)}</span></div>
        ))}
      </div>
      <div className="grid grid-cols-7">
        {cal.days.map((day) => <MonthDay key={day.date} day={day} cal={cal} onOpen={onOpen} onAdd={onAdd} onWeek={onWeek} />)}
      </div>
    </div>
  );
}

function MonthDay({ day, cal, onOpen, onAdd, onWeek }: { day: CalendarDay; cal: Calendar; onOpen: (id: number) => void; onAdd: (date: string) => void; onWeek: (date: string) => void }) {
  const hidden = day.events.length - cal.max_chips;
  const canAdd = cal.can_schedule && !day.is_past && new Date(`${day.date}T12:00:00Z`).getUTCDay() !== 0;
  return (
    <div role="gridcell" className={`group min-h-24 min-w-0 border-b border-r border-ink-100 p-1 sm:min-h-28 sm:p-1.5 ${day.in_period ? "" : "bg-ink-50/70"} ${day.is_past ? "text-ink-400" : ""}`}>
      <div className="mb-1 flex items-center justify-between">
        <button type="button" onClick={() => onWeek(day.date)} aria-label={`Ver la semana del ${labelOf(day.date)}`} aria-current={day.is_today ? "date" : undefined}
          className={`grid size-7 place-items-center text-sm font-semibold hover:bg-ink-100 ${day.is_today ? "bg-brand-700 text-white hover:bg-brand-800" : day.in_period ? "" : "text-ink-400"}`}>
          {dayNumber(day.date)}
        </button>
        {canAdd ? (
          <button type="button" onClick={() => onAdd(day.date)} title="Agendar visita" aria-label={`Agendar visita el ${labelOf(day.date)}`}
            className="rounded p-0.5 text-brand-700 opacity-60 hover:bg-brand-50 hover:opacity-100 group-hover:opacity-100"><Icon name="plus" className="size-4" /></button>
        ) : null}
      </div>
      <div className="space-y-0.5">
        {day.events.slice(0, cal.max_chips).map((event, index) => <Chip key={event.id ?? `o${index}`} event={event} onOpen={onOpen} />)}
        {hidden > 0 ? <button type="button" onClick={() => onWeek(day.date)} className="px-1.5 text-xs font-semibold text-ink-500 hover:underline">{hidden} más</button> : null}
      </div>
    </div>
  );
}

function WeekGrid({ cal, onOpen, onAdd }: { cal: Calendar; onOpen: (id: number) => void; onAdd: (date: string, hour: number) => void }) {
  const h = cal.hour_height;
  return (
    <div className="relative overflow-x-auto">
      <div className="min-w-[760px]">
        <div className="grid grid-cols-[3.5rem_repeat(7,minmax(0,1fr))] border-b border-ink-200">
          <div />
          {cal.days.map((day) => (
            <div key={day.date} className={`py-2 text-center ${day.is_past ? "text-ink-400" : ""}`}>
              <small className="block text-xs font-medium capitalize text-ink-500">{day.weekday.slice(0, 3)}</small>
              <strong aria-current={day.is_today ? "date" : undefined}
                className={`mx-auto grid size-8 place-items-center text-base ${day.is_today ? "bg-brand-700 text-white" : ""}`}>{dayNumber(day.date)}</strong>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-[3.5rem_repeat(7,minmax(0,1fr))]" style={{ height: cal.grid_height }}>
          <div className="relative" aria-hidden="true">
            {cal.hours.map((label, row) => (
              <span key={label} className="absolute right-2 -translate-y-1/2 text-[11px] text-ink-400" style={{ top: row * h }}>{row ? label : ""}</span>
            ))}
          </div>
          {cal.days.map((day) => (
            <div key={day.date} aria-label={`${day.weekday} ${labelOf(day.date)}`}
              className={`relative border-l border-ink-100 ${day.is_past ? "bg-ink-50/60" : ""} ${day.is_today ? "bg-brand-50/40" : ""}`}
              style={{ backgroundImage: `repeating-linear-gradient(to bottom, transparent 0 ${h - 1}px, #eef0f5 ${h - 1}px ${h}px)` }}>
              {cal.can_schedule ? day.open_hours.map((hour) => (
                <button key={hour} type="button" onClick={() => onAdd(day.date, hour)} aria-label={`Agendar visita el ${labelOf(day.date)} a las ${hour}:00`}
                  className="absolute inset-x-0 hover:bg-brand-50" style={{ top: (hour - cal.first_hour) * h, height: h }} />
              )) : null}
              {day.events.map((event, index) => <WeekEvent key={event.id ?? `o${index}`} event={event} onOpen={onOpen} />)}
              {day.is_today && cal.now_top !== null ? (
                <div className="pointer-events-none absolute inset-x-0 z-10 border-t-2 border-red-500" style={{ top: cal.now_top }} aria-hidden="true" />
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function WeekEvent({ event, onOpen }: { event: CalendarEvent; onOpen: (id: number) => void }) {
  const style = { top: event.top, height: event.height, left: `${event.left}%`, width: `calc(${event.width}% - 4px)` };
  const span = `${formatTime(event.starts_at)} – ${formatTime(event.ends_at)}`;
  if (event.busy) {
    return (
      <div className="absolute z-[1] overflow-hidden rounded-md border border-dashed border-ink-300 bg-ink-100 px-1.5 py-1 text-xs text-ink-500" style={style}>
        <strong className="block">Ocupado</strong><small>{span}</small>
      </div>
    );
  }
  const color = colorOf(event.color);
  return (
    <button type="button" onClick={() => event.id && onOpen(event.id)}
      className={`absolute z-[2] overflow-hidden border border-white px-1.5 py-1 text-left text-xs hover:brightness-95 ${event.level?.key === "cancelada" ? "line-through opacity-60" : ""}`}
      style={{ ...style, background: color.bg, color: color.fg }}>
      <strong className="flex items-center gap-1.5 truncate"><span className="size-1.5 shrink-0 rounded-full" style={{ background: color.fg }} aria-hidden="true" />{event.title}</strong>
      <small className="block truncate">{span}</small>
      <small className="block truncate font-semibold">{event.level?.label}</small>
    </button>
  );
}

function Footer({ cal }: { cal: Calendar }) {
  const empty = cal.days.every((day) => day.events.length === 0);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-ink-200 p-4 text-xs">
      {empty ? <p className="text-ink-500">No hay visitas en este periodo.</p> : <span />}
      <ul aria-label="Niveles de las visitas" className="flex flex-wrap gap-1.5">
        {cal.levels.map((level) => <li key={level.key}><LevelBadge level={level} /></li>)}
      </ul>
    </div>
  );
}

function SidePanel({ cal, onOpen }: { cal: Calendar; onOpen: (id: number) => void }) {
  return (
    <Card>
      {cal.to_close.length ? (
        <div className="mb-5 rounded-2xl bg-red-50 p-4">
          <h2 className="font-semibold text-red-900">Por cerrar</h2>
          <p className="mb-2 text-xs text-red-800">Ya pasaron: registra si se hicieron.</p>
          {cal.to_close.slice(0, 4).map((visit) => (
            <button key={visit.id} type="button" onClick={() => onOpen(visit.id)} className="block w-full rounded px-2 py-1.5 text-left text-sm hover:bg-red-100">
              <strong className="block">{visit.company.name}</strong>
              <small className="text-red-800">{formatLongDate(visit.starts_at.slice(0, 10))} · {formatTime(visit.starts_at)}</small>
            </button>
          ))}
          {cal.to_close.length > 4 ? <Link to="/visitas/agenda?ver=por_cerrar" className={linkButtonClass()}>Ver las {cal.to_close.length}</Link> : null}
        </div>
      ) : null}
      <SectionHead title="Próximas visitas" subtitle={cal.upcoming.length ? `Las ${cal.upcoming.length} más cercanas` : undefined} />
      {cal.upcoming.length === 0 ? (
        <p className="py-6 text-center text-sm text-ink-500">No hay visitas programadas</p>
      ) : <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{cal.upcoming.map((visit) => <UpcomingItem key={visit.id} visit={visit} onOpen={onOpen} />)}</div>}
      <Link to="/visitas/agenda" className={`${linkButtonClass()} mt-2`}>Ver la agenda completa</Link>
    </Card>
  );
}

function UpcomingItem({ visit, onOpen }: { visit: VisitRow; onOpen: (id: number) => void }) {
  const start = new Date(visit.starts_at);
  return (
    <button type="button" onClick={() => onOpen(visit.id)} className="flex w-full gap-3.5 border-t-2 border-ink-950 py-3 text-left transition-colors hover:bg-ink-50">
      <span className="flex w-12 shrink-0 flex-col items-center overflow-hidden border border-ink-950 bg-white">
        <small className="w-full bg-brand-700 py-0.5 text-center text-[10px] font-semibold text-white">{shortMonth.format(start).replace(".", "")}</small>
        <strong className="font-display text-lg leading-none tabular">{dayNumber(visit.starts_at)}</strong>
      </span>
      <span className="min-w-0 text-sm">
        <strong className="block truncate">{visit.company.name}</strong>
        <small className="block text-ink-500">{capitalize(weekdayLong.format(start))}, {formatTime(visit.starts_at)}</small>
        <small className="mb-1 block truncate text-ink-500">{visit.site}</small>
        <LevelBadge level={visit.level} />
      </span>
    </button>
  );
}

const capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
