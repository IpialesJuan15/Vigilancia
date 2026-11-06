"use client";
import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { api, User } from "@/lib/api";
type Mode =
  | "login"
  | "registro"
  | "recuperar"
  | "restablecer"
  | "verificar-correo"
  | "reenviar";
const labels = {
  login: ["Bienvenido de nuevo", "Iniciar sesión"],
  registro: ["Crea tu cuenta", "Crear cuenta"],
  recuperar: ["Recupera tu acceso", "Enviar enlace"],
  restablecer: ["Elige una nueva contraseña", "Restablecer contraseña"],
  "verificar-correo": ["Confirma tu correo", "Verificar correo"],
  reenviar: ["Verifica tu cuenta", "Reenviar enlace"],
};
export function AuthForm({ mode }: { mode: Mode }) {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [orcid, setOrcid] = useState(false);
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token");
  useEffect(() => {
    if (mode === "login")
      api<{ orcid: boolean }>("/auth/capabilities")
        .then((x) => setOrcid(x.orcid))
        .catch(() => {});
  }, [mode]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    const form = new FormData(event.currentTarget);
    const data = Object.fromEntries(form.entries());
    const paths = {
      login: "/auth/login",
      registro: "/auth/register",
      recuperar: "/auth/password/forgot",
      restablecer: "/auth/password/reset",
      "verificar-correo": "/auth/verify-email",
      reenviar: "/auth/verification/resend",
    };
    try {
      if (mode === "login") {
        await api<User>(paths[mode], data);
        router.push("/mis-revisiones");
        router.refresh();
      } else {
        const result = await api<{ message: string }>(
          paths[mode],
          token ? { ...data, token } : data,
        );
        setMessage(result.message);
      }
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "No pudimos conectar. Inténtalo de nuevo",
      );
    } finally {
      setBusy(false);
    }
  }
  const needsToken = mode === "restablecer" || mode === "verificar-correo";
  return (
    <section className="auth card">
      <span className="eyebrow">Tu espacio de investigación</span>
      <h1>{labels[mode][0]}</h1>
      <p>
        {mode === "login"
          ? "Continúa trabajando con tu evidencia."
          : "Un paso más para investigar con confianza."}
      </p>
      <form onSubmit={submit}>
        {mode === "registro" && (
          <label>
            Nombre completo
            <input
              name="name"
              autoComplete="name"
              required
              minLength={2}
              maxLength={120}
            />
          </label>
        )}
        {["login", "registro", "recuperar", "reenviar"].includes(mode) && (
          <label>
            Correo electrónico
            <input
              name="email"
              type="email"
              autoComplete="email"
              required
              maxLength={254}
            />
          </label>
        )}
        {["login", "registro", "restablecer"].includes(mode) && (
          <label>
            Contraseña
            <input
              aria-label="Contraseña"
              aria-describedby={mode === "login" ? undefined : "password-help"}
              name="password"
              type="password"
              required
              minLength={mode === "login" ? 1 : 12}
              maxLength={128}
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
            />
            {mode !== "login" && (
              <span id="password-help" className="help">
                Usa al menos 12 caracteres.
              </span>
            )}
          </label>
        )}
        {error && (
          <p className="message error" role="alert">
            {error}
          </p>
        )}
        {message && (
          <p className="message" role="status">
            {message}
          </p>
        )}
        <Button disabled={busy || (needsToken && !token)}>
          {busy ? "Un momento…" : labels[mode][1]}
        </Button>
        {needsToken && !token && (
          <p className="help">
            Abre el enlace que recibiste en tu correo para continuar.
          </p>
        )}
      </form>
      {mode === "login" && (
        <>
          <div className="divider">o</div>
          {orcid ? (
            <a className="button outline full" href="/api/auth/orcid/login">
              Continuar con ORCID
            </a>
          ) : (
            <>
              <Button className="full" variant="outline" disabled>
                Continuar con ORCID
              </Button>
              <p className="help">
                El acceso con ORCID estará disponible cuando se configure la
                conexión.
              </p>
            </>
          )}
          <div className="auth-links">
            <Link href="/registro">Crear cuenta</Link>
            <Link href="/recuperar">Olvidé mi contraseña</Link>
          </div>
          <p className="help">
            <Link href="/reenviar">Reenviar correo de verificación</Link>
          </p>
        </>
      )}
      {mode !== "login" && (
        <p className="help">
          <Link href="/login">Volver a iniciar sesión</Link>
        </p>
      )}
    </section>
  );
}
