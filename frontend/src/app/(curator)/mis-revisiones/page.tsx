"use client";
import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  BookOpen,
  Check,
  FileText,
  FolderOpen,
  ShieldCheck,
  Quote,
  Search,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";

export default function Workspace() {
  const { user, status, refresh } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);
  if (status === "error")
    return (
      <section className="card empty">
        <ShieldCheck size={32} aria-hidden="true" />
        <h1 className="dashboard-title">No pudimos comprobar tu sesión</h1>
        <p>Comprueba tu conexión e inténtalo de nuevo.</p>
        <Button onClick={() => void refresh()}>Intentar de nuevo</Button>
      </section>
    );
  if (!user)
    return (
      <section
        className="workspace-loading"
        role="status"
        aria-label="Preparando tu espacio"
      >
        <div className="skeleton" />
        <p>Preparando tu espacio…</p>
      </section>
    );
  const role = {
    subscriber: "Suscriptor",
    curator: "Curador",
    admin: "Administrador",
  }[user.role];
  return (
    <div className="workspace">
      <div className="workspace-heading">
        <div>
          <span className="eyebrow">Tu espacio de investigación</span>
          <h1 className="dashboard-title">Mis revisiones</h1>
          <p>
            Hola, {user.name}. Este es el lugar donde tu evidencia seguirá
            creciendo.
          </p>
        </div>
        <span className="role-badge">
          <ShieldCheck size={15} aria-hidden="true" />
          {role}
        </span>
      </div>
      <aside className="next-step workspace-next">
        <div className="next-icon">
          <Search size={23} aria-hidden="true" />
        </div>
        <div>
          <span className="eyebrow">Siguiente paso</span>
          <h2>Conoce el catálogo de revisiones</h2>
          <p>Consulta las revisiones públicas cuando estén disponibles.</p>
        </div>
        <Link className="button primary" href="/catalogo">
          Explorar revisiones
          <ArrowRight size={17} aria-hidden="true" />
        </Link>
      </aside>
      <div className="workspace-grid">
        <section
          className="card review-collection"
          aria-labelledby="reviews-heading"
        >
          <div className="collection-heading">
            <h2 id="reviews-heading">Tu biblioteca</h2>
            <span className="collection-label">Revisiones que administras</span>
          </div>
          <div className="empty workspace-empty">
            <div className="empty-illustration" aria-hidden="true">
              <span className="paper paper-back" />
              <span className="paper paper-front">
                <FileText size={35} />
              </span>
              <span className="folder-symbol">
                <FolderOpen size={25} />
              </span>
            </div>
            <h2>Aún no tienes revisiones</h2>
            <p>
              Cuando administres una revisión, encontrarás aquí su evidencia,
              sus novedades y el siguiente paso.
            </p>
            <div className="availability-note">
              <span className="availability-dot" aria-hidden="true" />
              <span>La carga de artículos todavía no está disponible.</span>
            </div>
          </div>
        </section>
        <aside className="workspace-sidebar">
          <section className="card account-card">
            <span className="eyebrow">Tu cuenta</span>
            <div className="account-card-title">
              <span className="account-check">
                <Check size={20} aria-hidden="true" />
              </span>
              <h2>
                {user.email_verified ? "Cuenta verificada" : "Cuenta conectada"}
              </h2>
            </div>
            <p>Ya tienes acceso a tu espacio de investigación.</p>
            <div className="account-fact">
              <span>Acceso</span>
              <strong>
                {user.email_verified
                  ? "Correo verificado"
                  : "Conectado con ORCID"}
              </strong>
            </div>
            <div className="account-fact">
              <span>Perfil</span>
              <strong>{role}</strong>
            </div>
          </section>
          <section className="trust-note">
            <BookOpen size={19} aria-hidden="true" />
            <div>
              <strong>La evidencia, siempre primero</strong>
              <p>
                Cada dato conservará su fuente. Cada actualización pasará por
                revisión humana.
              </p>
            </div>
          </section>
        </aside>
      </div>
      <div className="workspace-footnote">
        <Quote size={17} aria-hidden="true" />
        <p>
          El conocimiento avanza. El reconocimiento a sus autores permanece.
        </p>
      </div>
      {user.role === "admin" && (
        <p>
          <Link href="/administracion">Administrar usuarios →</Link>
        </p>
      )}
    </div>
  );
}
