import { test, expect } from "@playwright/test";

test("páginas públicas accesibles y sin jerga", async ({ page }) => {
  for (const path of ["/", "/catalogo", "/login", "/registro", "/recuperar"]) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("lang", "es");
    await expect(page.locator("body")).not.toContainText(
      /TF-IDF|embeddings|prompt|SHA-256|API key/i,
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
});

test("registro, verificación real por correo, sesión y cierre", async ({
  page,
  request,
}) => {
  const email = `reader-${Date.now()}-${test.info().project.name}@example.org`;
  await page.goto("/registro");
  await page.getByLabel("Nombre completo").fill("Investigadora de prueba");
  await page.getByLabel("Correo electrónico").fill(email);
  await page
    .getByLabel("Contraseña", { exact: true })
    .fill("e2e-secure-password-123");
  await page.getByRole("button", { name: "Crear cuenta", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("enviaremos un enlace");
  let verifyUrl = "";
  await expect
    .poll(
      async () => {
        const listing = await request.get(
          `${process.env.MAILPIT_URL || "http://localhost:8025"}/api/v1/messages`,
        );
        const messages = (await listing.json()).messages;
        const entry = messages.find((m: { To: { Address: string }[] }) =>
          m.To.some((t) => t.Address === email),
        );
        if (!entry) return false;
        const message = await request.get(
          `${process.env.MAILPIT_URL || "http://localhost:8025"}/api/v1/message/${entry.ID}`,
        );
        verifyUrl = (await message.json()).Text.match(/http[^\s]+/)[0];
        return true;
      },
      { timeout: 30000 },
    )
    .toBeTruthy();
  await page.goto(verifyUrl);
  await page
    .getByRole("button", { name: "Verificar correo", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Correo verificado");
  await page.goto("/login");
  await page.getByLabel("Correo electrónico").fill(email);
  await page
    .getByLabel("Contraseña", { exact: true })
    .fill("e2e-secure-password-123");
  await page
    .getByRole("button", { name: "Iniciar sesión", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Mis revisiones", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Hola, Investigadora de prueba.")).toBeVisible();
  await expect(page.getByText("Siguiente paso", { exact: true })).toBeVisible();
  const navigation = page.getByRole("navigation", {
    name: "Navegación principal",
  });
  await expect(
    navigation.getByRole("link", { name: "Iniciar sesión", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByLabel("Tu cuenta: Investigadora de prueba", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Tu perfil permite consultar revisiones. Un administrador puede darte acceso como curador.",
    ),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: test.info().outputPath("workspace.png"),
    fullPage: true,
  });

  // The shared header survives client navigation, a full reload and a second tab.
  await navigation.getByRole("link", { name: "Explorar", exact: true }).click();
  await page.reload();
  await expect(
    page.getByLabel("Tu cuenta: Investigadora de prueba", { exact: true }),
  ).toBeVisible();
  await expect(
    navigation.getByRole("link", { name: "Iniciar sesión", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Activar modo oscuro", exact: true })
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Activar modo claro", exact: true }),
  ).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await navigation
    .getByRole("link", { name: "Mi espacio", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Mis revisiones", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath("workspace-dark.png"),
    fullPage: true,
  });

  const secondTab = await page.context().newPage();
  await secondTab.goto("/catalogo");
  await expect(
    secondTab.getByLabel("Tu cuenta: Investigadora de prueba", { exact: true }),
  ).toBeVisible();
  await page.bringToFront();
  await page
    .getByLabel("Tu cuenta: Investigadora de prueba", { exact: true })
    .click();
  await page
    .getByRole("button", { name: "Cerrar sesión", exact: true })
    .click();
  await expect(page).toHaveURL(/\/login$/);
  expect((await page.request.get("/api/me")).status()).toBe(401);
  await expect(
    navigation.getByRole("link", { name: "Iniciar sesión", exact: true }),
  ).toBeVisible();
  await expect(
    secondTab
      .getByRole("navigation")
      .getByRole("link", { name: "Iniciar sesión", exact: true }),
  ).toBeVisible();
  await secondTab.close();
});

test("protección del espacio privado y error de página", async ({ page }) => {
  await page.goto("/mis-revisiones");
  await expect(page).toHaveURL(/\/login$/);
  await page.goto("/pagina-inexistente");
  await expect(
    page.getByRole("heading", { name: "No encontramos esta página" }),
  ).toBeVisible();
});

test("no muestra acceso anónimo mientras comprueba la sesión", async ({
  page,
}) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/me", async (route) => {
    await gate;
    await route.fulfill({ status: 401, json: { message: "Inicia sesión" } });
  });
  await page.goto("/catalogo");
  const nav = page.getByRole("navigation");
  await expect(nav.getByLabel("Comprobando sesión")).toBeVisible();
  await expect(
    nav.getByRole("link", { name: "Iniciar sesión", exact: true }),
  ).toHaveCount(0);
  release();
  await expect(
    nav.getByRole("link", { name: "Iniciar sesión", exact: true }),
  ).toBeVisible();
});

test("permite reintentar un fallo de conexión sin simular una sesión cerrada", async ({
  page,
}) => {
  let recovered = false;
  await page.route("**/api/me", (route) =>
    route.fulfill({
      status: recovered ? 401 : 503,
      json: { message: "Servicio no disponible" },
    }),
  );
  await page.goto("/mis-revisiones");
  await expect(
    page.getByRole("heading", { name: "No pudimos comprobar tu sesión" }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/mis-revisiones$/);
  await expect(
    page
      .getByRole("navigation")
      .getByRole("link", { name: "Iniciar sesión", exact: true }),
  ).toHaveCount(0);
  recovered = true;
  await page
    .getByRole("button", { name: "Intentar de nuevo", exact: true })
    .click();
  await expect(page).toHaveURL(/\/login$/);
});

test("actualiza el menú y protege el espacio cuando la sesión caduca", async ({
  page,
}) => {
  let expired = false;
  await page.route("**/api/me", (route) =>
    route.fulfill({
      status: expired ? 401 : 200,
      json: expired
        ? { message: "Sesión caducada" }
        : {
            id: "test-user",
            name: "Investigadora",
            email: "reader@example.org",
            role: "subscriber",
            email_verified: true,
            orcid_id: null,
          },
    }),
  );
  await page.goto("/mis-revisiones");
  await expect(
    page.getByLabel("Tu cuenta: Investigadora", { exact: true }),
  ).toBeVisible();
  expired = true;
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(page).toHaveURL(/\/login$/);
  await expect(
    page
      .getByRole("navigation")
      .getByRole("link", { name: "Iniciar sesión", exact: true }),
  ).toBeVisible();
});

test("mostrar contraseña conserva el valor y no envía el formulario", async ({
  page,
}) => {
  await page.goto("/login");
  const input = page.getByLabel("Contraseña", { exact: true });
  await input.fill("a-test-password-123");
  await page
    .getByRole("button", { name: "Mostrar contraseña", exact: true })
    .click();
  await expect(input).toHaveAttribute("type", "text");
  await expect(input).toHaveValue("a-test-password-123");
  await page
    .getByRole("button", { name: "Ocultar contraseña", exact: true })
    .click();
  await expect(input).toHaveAttribute("type", "password");
  await expect(page).toHaveURL(/\/login$/);
});

test("el menú de cuenta cabe y funciona en una pantalla estrecha", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.route("**/api/me", (route) =>
    route.fulfill({
      status: 200,
      json: {
        id: "test-user",
        name: "Investigadora",
        email: "reader@example.org",
        role: "subscriber",
        email_verified: true,
        orcid_id: null,
      },
    }),
  );
  await page.goto("/mis-revisiones");
  await page.getByLabel("Tu cuenta: Investigadora", { exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Cerrar sesión", exact: true }),
  ).toBeVisible();
  const panel = await page.locator(".account-panel").boundingBox();
  expect(panel).not.toBeNull();
  expect(panel!.x).toBeGreaterThanOrEqual(0);
  expect(panel!.x + panel!.width).toBeLessThanOrEqual(320);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page
    .getByLabel("Tu cuenta: Investigadora", { exact: true })
    .press("Escape");
  await expect(
    page.getByRole("button", { name: "Cerrar sesión", exact: true }),
  ).not.toBeVisible();
});
