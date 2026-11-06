"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FolderOpen } from "lucide-react";
import { api, User } from "@/lib/api";
import { Button } from "@/components/ui/button";
export default function Workspace() {
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");
  const router = useRouter();
  useEffect(() => {
    api<User>("/me")
      .then(setUser)
      .catch(() => router.replace("/login"));
  }, [router]);
  async function logout() {
    try {
      await api("/auth/logout", {});
      router.replace("/login");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Inténtalo de nuevo");
    }
  }
  if (!user) return <p role="status">Preparando tu espacio…</p>;
  return (
    <>
      <div className="toolbar">
        <div>
          <span className="eyebrow">Mi espacio</span>
          <h1 className="dashboard-title">Mis revisiones</h1>
          <p>Hola, {user.name}.</p>
        </div>
        <Button variant="outline" onClick={logout}>
          Cerrar sesión
        </Button>
      </div>
      {error && <p role="alert">{error}</p>}
      <aside className="next-step">
        <strong>Siguiente paso</strong>
        <p>
          {user.role === "subscriber"
            ? "Tu cuenta ya está lista. Explora el catálogo de revisiones públicas."
            : "Tu espacio está listo. La carga de revisiones se habilitará en la siguiente etapa."}
        </p>
        <Link className="button primary" href="/catalogo">
          Explorar revisiones
        </Link>
      </aside>
      <section className="card empty">
        <FolderOpen size={36} aria-hidden="true" />
        <h2>Aún no tienes revisiones</h2>
        <p>
          Las revisiones que administres aparecerán aquí con su siguiente
          acción.
        </p>
        {user.role !== "subscriber" && (
          <>
            <Button variant="outline" disabled>
              Cargar revisión
            </Button>
            <p className="help">
              La carga de artículos todavía no está disponible.
            </p>
          </>
        )}
      </section>
      {user.role === "admin" && (
        <p>
          <Link href="/administracion">Administrar usuarios →</Link>
        </p>
      )}
    </>
  );
}
