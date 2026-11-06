"use client";
import Link from "next/link";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  BookOpen,
  Moon,
  Sun,
  ChevronDown,
  LogOut,
  LayoutDashboard,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";

function subscribeTheme(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener("theme-changed", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("theme-changed", callback);
  };
}
function getTheme() {
  try {
    return localStorage.getItem("theme") === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}
export function Header() {
  const { user, status, refresh, signOut } = useAuth();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const menu = useRef<HTMLDetailsElement>(null);
  const pathname = usePathname();
  const router = useRouter();
  const theme = useSyncExternalStore(subscribeTheme, getTheme, () => "light");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  useEffect(() => {
    if (menu.current) menu.current.open = false;
  }, [pathname]);
  useEffect(() => {
    function close(event: PointerEvent) {
      if (menu.current && !menu.current.contains(event.target as Node))
        menu.current.open = false;
    }
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);
  function toggle() {
    try {
      localStorage.setItem("theme", theme === "dark" ? "light" : "dark");
    } catch {
      return;
    }
    window.dispatchEvent(new Event("theme-changed"));
  }
  async function logout() {
    setError("");
    setBusy(true);
    try {
      await signOut();
      router.replace("/login");
    } catch {
      setError("No pudimos cerrar tu sesión. Inténtalo de nuevo.");
    } finally {
      setBusy(false);
    }
  }
  const initials = user?.name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toLocaleUpperCase("es");
  return (
    <>
      <div className="staging">
        <span className="staging-dot" aria-hidden="true" />
        Entorno de prueba — DOIs no oficiales
      </div>
      <header className="site-header">
        <div className="header-inner">
          <Link className="brand" href="/" aria-label="LiveSRL — Inicio">
            <span className="brand-icon">
              <BookOpen aria-hidden="true" size={22} />
            </span>
            <span className="brand-wordmark">
              Live<span>SRL</span>
            </span>
          </Link>
          <nav className="header-nav" aria-label="Navegación principal">
            <Link
              className="nav-link"
              href="/catalogo"
              aria-current={pathname === "/catalogo" ? "page" : undefined}
            >
              Explorar
            </Link>
            <Link
              className="nav-link"
              href="/mis-revisiones"
              aria-current={pathname === "/mis-revisiones" ? "page" : undefined}
            >
              Mi espacio
            </Link>
            {status === "loading" && (
              <span
                className="session-placeholder"
                aria-label="Comprobando sesión"
              />
            )}
            {status === "anonymous" && (
              <Link className="button outline login-link" href="/login">
                Iniciar sesión
              </Link>
            )}
            {status === "error" && (
              <Button variant="outline" onClick={() => void refresh()}>
                Comprobar sesión
              </Button>
            )}
            {status === "authenticated" && user && (
              <details
                className="account-menu"
                ref={menu}
                onKeyDown={(event) => {
                  if (event.key === "Escape" && menu.current) {
                    menu.current.open = false;
                    menu.current.querySelector("summary")?.focus();
                  }
                }}
              >
                <summary aria-label={`Tu cuenta: ${user.name}`}>
                  <span className="avatar" aria-hidden="true">
                    {initials}
                  </span>
                  <span className="account-name">{user.name}</span>
                  <ChevronDown size={14} aria-hidden="true" />
                </summary>
                <div className="account-panel">
                  <div className="account-info">
                    <strong>{user.name}</strong>
                    <span>{user.email || "Cuenta conectada con ORCID"}</span>
                  </div>
                  <Link href="/mis-revisiones">
                    <LayoutDashboard size={16} aria-hidden="true" />
                    Mi espacio
                  </Link>
                  {user.role === "admin" && (
                    <Link href="/administracion">
                      <ShieldCheck size={16} aria-hidden="true" />
                      Administración
                    </Link>
                  )}
                  <button
                    className="signout-button"
                    disabled={busy}
                    onClick={logout}
                  >
                    <LogOut size={16} aria-hidden="true" />
                    {busy ? "Cerrando sesión…" : "Cerrar sesión"}
                  </button>
                  {error && (
                    <p role="alert" className="help">
                      {error}
                    </p>
                  )}
                </div>
              </details>
            )}
            <Button
              className="theme-button"
              variant="outline"
              onClick={toggle}
              aria-label={
                theme === "dark" ? "Activar modo claro" : "Activar modo oscuro"
              }
              aria-pressed={theme === "dark"}
            >
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </Button>
          </nav>
        </div>
      </header>
    </>
  );
}
