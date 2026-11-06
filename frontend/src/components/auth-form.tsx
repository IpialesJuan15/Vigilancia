"use client";
import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";
import {
  BookOpenCheck,
  ShieldCheck,
  Quote,
  Eye,
  EyeOff,
  ArrowRight,
} from "lucide-react";
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
  const { signIn } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
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
        const user = await api<User>(paths[mode], data);
        signIn(user);
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
    <div className="auth-shell">
      <aside className="auth-intro">
        <span className="eyebrow">Investigar con confianza</span>
        <h2>
          Tu evidencia.
          <br />
          Siempre <span className="accent">en movimiento.</span>
        </h2>
        <p>
          Un espacio para dar continuidad a las revisiones y conservar el valor
          de cada hallazgo.
        </p>
        <div className="auth-principles">
          <div>
            <BookOpenCheck size={20} aria-hidden="true" />
            <span>Fuentes de acceso abierto</span>
          </div>
          <div>
            <ShieldCheck size={20} aria-hidden="true" />
            <span>Revisión humana en cada paso</span>
          </div>
          <div>
            <Quote size={20} aria-hidden="true" />
            <span>Atribución a sus autores</span>
          </div>
        </div>
      </aside>
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
            <div className="form-field">
              <label htmlFor="password">Contraseña</label>
              <span className="password-field">
                <input
                  aria-label="Contraseña"
                  aria-describedby={
                    mode === "login" ? undefined : "password-help"
                  }
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={mode === "login" ? 1 : 12}
                  maxLength={128}
                  autoComplete={
                    mode === "login" ? "current-password" : "new-password"
                  }
                />
                <button
                  type="button"
                  className="password-toggle"
                  aria-label={
                    showPassword ? "Ocultar contraseña" : "Mostrar contraseña"
                  }
                  aria-pressed={showPassword}
                  onClick={() => setShowPassword((value) => !value)}
                >
                  {showPassword ? (
                    <EyeOff size={18} aria-hidden="true" />
                  ) : (
                    <Eye size={18} aria-hidden="true" />
                  )}
                </button>
              </span>
              {mode !== "login" && (
                <span id="password-help" className="help">
                  Usa al menos 12 caracteres.
                </span>
              )}
            </div>
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
            {!busy && <ArrowRight size={17} aria-hidden="true" />}
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
    </div>
  );
}
