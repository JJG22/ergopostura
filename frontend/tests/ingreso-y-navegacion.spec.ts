import { expect, test, type Page } from "@playwright/test";

/** Cuentas de `python manage.py seed_demo`. La contraseña se puede cambiar con E2E_PASSWORD. */
const PASSWORD = process.env.E2E_PASSWORD ?? "ErgoDemo2026!";
const USERS = {
  ingeniero: "ingeniero@ergopostura.test",
  empresa: "empresa@ergopostura.test",
  soporte: "admin@ergopostura.test",
} as const;

async function login(page: Page, email: string, password = PASSWORD) {
  await page.goto("/app/ingresar");
  await page.getByLabel("Correo electrónico").fill(email);
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
}

/** La barra superior se muestra en pantallas anchas; en el teléfono, el menú se abre con un botón. */
async function openNavigation(page: Page) {
  const menu = page.getByRole("button", { name: "Abrir menú" });
  if (await menu.isVisible()) await menu.click();
  return page.getByRole("navigation", { name: "Navegación principal" }).filter({ visible: true });
}

test.describe("Portada pública", () => {
  test("presenta el servicio y lleva al ingreso", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: "Evaluación ergonómica para empresas" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "La escala RULA y sus cuatro niveles" })).toBeAttached();
    // La portada no ofrece un correo de contacto: el servicio lo prestan varios ingenieros.
    await expect(page.locator('a[href^="mailto:"]')).toHaveCount(0);
    await page.locator('a[href="/app/ingresar"]').filter({ visible: true }).first().click();
    await expect(page).toHaveURL(/\/app\/ingresar/);
  });
});

test.describe("Ingreso", () => {
  test("muestra el formulario y el regreso a la portada", async ({ page }) => {
    await page.goto("/app/ingresar");
    await expect(page.getByRole("heading", { name: "Ingresar" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Volver a la portada" })).toHaveAttribute("href", "/");
  });

  test("rechaza una contraseña incorrecta sin salir de la página", async ({ page }) => {
    await login(page, USERS.ingeniero, "contraseña-equivocada");
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page).toHaveURL(/\/app\/ingresar/);
  });

  test("una ruta protegida sin sesión lleva al ingreso", async ({ page }) => {
    await page.goto("/app/empresas");
    await expect(page).toHaveURL(/\/app\/ingresar/);
  });
});

test.describe("Ingeniero industrial", () => {
  test("entra al panel y navega a Empresas", async ({ page }) => {
    await login(page, USERS.ingeniero);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Andrés");
    await expect(page.getByText("Próxima visita")).toBeVisible();

    const nav = await openNavigation(page);
    await nav.getByRole("link", { name: /Empresas/ }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Empresas" })).toBeVisible();
  });
});

test.describe("Empresa cliente", () => {
  test("ve su contrato y no tiene acceso a la gestión del ingeniero", async ({ page }) => {
    await login(page, USERS.empresa);
    await expect(page.getByText("Contrato de servicio")).toBeVisible();

    const nav = await openNavigation(page);
    await expect(nav.getByRole("link", { name: /Visitas/ })).toBeVisible();
    await expect(nav.getByRole("link", { name: /Empresas/ })).toHaveCount(0);
    await expect(nav.getByRole("link", { name: /Contratos/ })).toHaveCount(0);
  });
});

test.describe("Soporte técnico", () => {
  test("solo gestiona cuentas", async ({ page }) => {
    await login(page, USERS.soporte);
    await expect(page.getByText("Estado del sistema")).toBeVisible();

    const nav = await openNavigation(page);
    await expect(nav.getByRole("link", { name: /Usuarios/ })).toBeVisible();
    await expect(nav.getByRole("link", { name: /Evaluaciones/ })).toHaveCount(0);
  });
});
