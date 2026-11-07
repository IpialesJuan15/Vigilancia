"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, FileText, Plus, ShieldCheck } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";
import { type Review, stateLabel } from "@/lib/reviews";
import { Button } from "@/components/ui/button";
export default function Workspace() {
  const { user, status, refresh } = useAuth();
  const router = useRouter();
  const [reviews, setReviews] = useState<Review[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);
  useEffect(() => {
    if (!user) return;
    let active = true;
    api<{ items: Review[] }>("/reviews")
      .then((x) => {
        if (active) setReviews(x.items);
      })
      .catch(() => {
        if (active)
          setError(
            "No pudimos cargar tus revisiones. Recarga la página para intentar de nuevo",
          );
      });
    return () => {
      active = false;
    };
  }, [user]);
  if (status === "error")
    return (
      <section className="card empty">
        <h1 className="dashboard-title">No pudimos comprobar tu sesión</h1>
        <Button onClick={() => void refresh()}>Intentar de nuevo</Button>
      </section>
    );
  if (!user) return <p role="status">Preparando tu espacio…</p>;
  const canCreate = user.role !== "subscriber";
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
          <ShieldCheck size={15} />
          {
            {
              subscriber: "Suscriptor",
              curator: "Curador",
              admin: "Administrador",
            }[user.role]
          }
        </span>
      </div>
      <aside className="next-step workspace-next">
        <div>
          <span className="eyebrow">Siguiente paso</span>
          <h2>
            {canCreate
              ? "Carga una revisión publicada"
              : "Conoce el catálogo de revisiones"}
          </h2>
          <p>
            {canCreate
              ? "Comienza con su DOI. Puedes añadir el PDF del artículo."
              : "Consulta las revisiones públicas cuando estén disponibles."}
          </p>
        </div>
        <Link
          className="button primary"
          href={canCreate ? "/revisiones/nueva" : "/catalogo"}
        >
          {canCreate ? (
            <>
              <Plus size={17} />
              Cargar revisión
            </>
          ) : (
            <>
              Explorar revisiones
              <ArrowRight size={17} />
            </>
          )}
        </Link>
      </aside>
      {error && (
        <p role="alert" className="message error">
          {error}
        </p>
      )}
      <section className="card review-collection">
        <div className="collection-heading">
          <h2>Tu biblioteca</h2>
          <span className="collection-label">Revisiones que administras</span>
        </div>
        {reviews.length ? (
          <div className="review-list">
            {reviews.map((review) => (
              <article className="review-card" key={review.id}>
                <span className="tag">
                  {stateLabel[review.status] || review.stage}
                </span>
                <h2>
                  <Link href={`/revisiones/${review.id}`}>
                    {review.original_title}
                  </Link>
                </h2>
                <p>
                  {review.journal} {review.year ? `· ${review.year}` : ""}
                </p>
                <Link href={`/revisiones/${review.id}`}>Abrir revisión →</Link>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty workspace-empty">
            <FileText size={38} aria-hidden="true" />
            <h2>Aún no tienes revisiones</h2>
            <p>
              {canCreate
                ? "Carga tu primer artículo para comprobar su licencia y leer su contenido."
                : "Cuando administres una revisión, encontrarás aquí su evidencia, sus novedades y el siguiente paso."}
            </p>
            {!canCreate && (
              <div className="availability-note">
                Tu perfil permite consultar revisiones. Un administrador puede
                darte acceso como curador.
              </div>
            )}
          </div>
        )}
      </section>
      {user.role === "admin" && (
        <p>
          <Link href="/administracion">Administrar usuarios →</Link>
        </p>
      )}
    </div>
  );
}
