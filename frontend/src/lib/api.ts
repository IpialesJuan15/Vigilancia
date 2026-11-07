export type User = {
  id: string;
  email: string | null;
  name: string;
  role: "admin" | "curator" | "subscriber";
  email_verified: boolean;
  orcid_id: string | null;
};
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

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
  const multipart = body instanceof FormData;
  const response = await fetch(`/api${path}`, {
    method: method ?? (body === undefined ? "GET" : "POST"),
    credentials: "same-origin",
    cache: "no-store",
    headers:
      body === undefined
        ? {}
        : {
            ...(multipart ? {} : { "Content-Type": "application/json" }),
            "X-CSRF-Token": token,
          },
    body:
      body === undefined ? undefined : multipart ? body : JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401 && path !== "/me" && path !== "/auth/login") {
      window.dispatchEvent(new Event("session-expired"));
    }
    throw new ApiError(
      result.message ?? "No pudimos completar la solicitud",
      response.status,
    );
  }
  return result;
}
