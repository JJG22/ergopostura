/** Fechas en español de Colombia y hora de Bogotá, igual que la aplicación actual. */
const ZONE = "America/Bogota";

const dayFormat = new Intl.DateTimeFormat("es-CO", { timeZone: ZONE, weekday: "long", day: "numeric", month: "long" });
const shortFormat = new Intl.DateTimeFormat("es-CO", { timeZone: ZONE, day: "2-digit", month: "2-digit", year: "numeric" });
const timeFormat = new Intl.DateTimeFormat("es-CO", { timeZone: ZONE, hour: "numeric", minute: "2-digit" });
const longDate = new Intl.DateTimeFormat("es-CO", { timeZone: "UTC", day: "numeric", month: "long", year: "numeric" });

const capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

export const formatDay = (iso: string) => capitalize(dayFormat.format(new Date(iso)));
export const formatTime = (iso: string) => timeFormat.format(new Date(iso));
export const formatShortDate = (iso: string) => shortFormat.format(new Date(`${iso}T12:00:00`));
/** Fechas sin hora (AAAA-MM-DD): se leen en UTC para que no cambien de día. */
export const formatLongDate = (iso: string) => longDate.format(new Date(`${iso}T00:00:00Z`));

export function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

/** Las pantallas aún no migradas viven en Django. En desarrollo, en otro puerto. */
export function legacyUrl(path: string): string {
  const origin = (import.meta.env.VITE_BACKEND_ORIGIN as string | undefined) ?? "";
  return `${origin}${path}`;
}
