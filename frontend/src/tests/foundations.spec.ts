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
  await expect(page.getByText("Siguiente paso")).toBeVisible();
  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect((await page.request.get("/api/me")).status()).toBe(401);
});

test("protección del espacio privado y error de página", async ({ page }) => {
  await page.goto("/mis-revisiones");
  await expect(page).toHaveURL(/\/login$/);
  await page.goto("/pagina-inexistente");
  await expect(
    page.getByRole("heading", { name: "No encontramos esta página" }),
  ).toBeVisible();
});
