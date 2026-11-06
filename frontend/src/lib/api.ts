export type User = {
  id: string;
  email: string | null;
  name: string;
  role: "admin" | "curator" | "subscriber";
  email_verified: boolean;
  orcid_id: string | null;
};
export async function api<T>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  let token = "";
  if (body !== undefined) {
    const response = await fetch("/api/auth/csrf", {
      credentials: "same-origin",
      cache: "no-store",
    });
    if (!response.ok)
      throw new Error("No se pudo conectar. Inténtalo de nuevo");
    token = (await response.json()).token;
  }
  const response = await fetch(`/api${path}`, {
    method: method ?? (body === undefined ? "GET" : "POST"),
    credentials: "same-origin",
    cache: "no-store",
    headers:
      body === undefined
        ? {}
        : { "Content-Type": "application/json", "X-CSRF-Token": token },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok)
    throw new Error(result.message ?? "No pudimos completar la solicitud");
  return result;
}
