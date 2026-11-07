import { test, expect } from "@playwright/test";
const user = {
  id: "curator-test",
  name: "Curadora de prueba",
  email: "curator@example.org",
  role: "curator",
  email_verified: true,
  orcid_id: null,
};
const review = {
  id: "review-test",
  original_doi: "10.1234/test",
  original_title: "Revisión sistemática de prueba",
  original_authors: [{ fullName: "Autora de prueba" }],
  journal: "Revista de prueba",
  year: 2024,
  license: "CC BY",
  status: "parsed",
  progress: 100,
  stage: "Documento leído",
  warnings: [],
  error_message: null,
  document: {
    sections: [
      {
        title: "Métodos",
        paragraphs: [
          {
            text: "Texto literal de los métodos.",
            location: "Sección 1, párrafo 1",
            page: null,
          },
        ],
      },
    ],
    tables: [
      {
        caption: "Tabla 1",
        location: "Tabla 1",
        header: [["Estudio", "Resultado"]],
        rows: [
          [
            { text: "Autor", rowspan: "1", colspan: "1" },
            { text: "Valor literal", rowspan: "1", colspan: "1" },
          ],
        ],
        needs_review: false,
      },
    ],
    references: [
      {
        text: "Referencia literal",
        location: "Referencia 1",
        doi: "10.1234/reference",
      },
    ],
  },
};
test("curador carga un DOI y comprueba secciones, tablas y referencias", async ({
  page,
}) => {
  await page.route("**/api/me", (r) => r.fulfill({ json: user }));
  await page.route("**/api/reviews", async (route) => {
    if (route.request().method() === "POST") {
      expect(route.request().headers()["content-type"]).toContain(
        "multipart/form-data",
      );
      expect(route.request().postData()).toContain("10.1234/test");
      await route.fulfill({
        status: 202,
        json: { ...review, document: null, status: "queued" },
      });
    } else
      await route.fulfill({
        json: { items: [], total: 0, ingestion_available: true },
      });
  });
  await page.route("**/api/reviews/review-test", (r) =>
    r.fulfill({ json: review }),
  );
  await page.goto("/mis-revisiones");
  await page
    .getByRole("link", { name: "Cargar revisión", exact: true })
    .click();
  await expect(
    page.getByRole("list", { name: "Pasos de tu revisión" }),
  ).toBeVisible();
  await page.getByLabel("DOI del artículo").fill("10.1234/test");
  await page.getByRole("button", { name: "Comprobar y leer revisión" }).click();
  await expect(
    page.getByRole("heading", { name: review.original_title, exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Texto literal de los métodos.")).toBeVisible();
  await page.getByRole("tab", { name: "Tablas (1)", exact: true }).click();
  await expect(
    page.getByRole("cell", { name: "Valor literal", exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Referencias (1)", exact: true }).click();
  await expect(
    page.getByText("Referencia literal", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});
test("suscriptor no puede abrir el formulario de carga", async ({ page }) => {
  await page.route("**/api/me", (r) =>
    r.fulfill({ json: { ...user, role: "subscriber" } }),
  );
  await page.goto("/revisiones/nueva");
  await expect(
    page.getByRole("heading", { name: "Necesitas acceso como curador" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Comprobar y leer revisión" }),
  ).toHaveCount(0);
});
test("licencia restrictiva exige marcar la confirmación", async ({ page }) => {
  await page.route("**/api/me", (r) => r.fulfill({ json: user }));
  await page.route("**/api/reviews/review-test", (r) =>
    r.fulfill({
      json: {
        ...review,
        status: "license_review",
        document: null,
        license: "CC BY-NC-ND",
      },
    }),
  );
  await page.goto("/revisiones/review-test");
  const action = page.getByRole("button", {
    name: "Confirmar y continuar la lectura",
  });
  await expect(action).toBeDisabled();
  await page.getByRole("checkbox").check();
  await expect(action).toBeEnabled();
});
