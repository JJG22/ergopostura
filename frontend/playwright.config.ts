import { defineConfig, devices } from "@playwright/test";

/**
 * Pruebas de extremo a extremo del cliente React.
 *
 * Corren contra un servidor ya encendido que tenga los datos de demostración (`seed_demo`):
 * por defecto, el de desarrollo en http://localhost:5173. Para otro, define E2E_BASE_URL.
 * No crean ni modifican datos: solo ingresan y navegan.
 *
 * En este equipo no hay Node fuera de Docker; se ejecutan con la imagen oficial, dentro de la
 * red del contenedor del cliente para que "localhost:5173" sea el servidor de desarrollo
 * (Django solo acepta localhost). Un volumen aparte guarda node_modules de Linux:
 *   docker run --rm --network container:proyectonucleari-frontend-1 \
 *     -v "C:/Proyectos/ergopostura/frontend:/web" -v ergopostura-pw-nm:/web/node_modules -w /web \
 *     mcr.microsoft.com/playwright:v1.65.1-noble sh -c "npm ci && npx playwright test"
 */
export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    locale: "es-CO",
    timezoneId: "America/Bogota",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "escritorio", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    { name: "movil", use: { ...devices["Pixel 7"] } },
  ],
});
