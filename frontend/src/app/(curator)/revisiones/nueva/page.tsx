"use client";
import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { ReviewSteps } from "@/components/review/steps";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { Review } from "@/lib/reviews";
export default function NewReview() {
  const { user, status } = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = new FormData(event.currentTarget);
      const pdf = data.get("pdf");
      if (pdf instanceof File && !pdf.size) data.delete("pdf");
      const review = await api<Review>("/reviews", data);
      router.push(
        `/revisiones/${review.id}${review.duplicate ? "?existente=1" : ""}`,
      );
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "No pudimos cargar la revisión",
      );
      setBusy(false);
    }
  }
  if (!user) return <p role="status">Comprobando tu acceso…</p>;
  if (user.role === "subscriber")
    return (
      <section className="card">
        <h1 className="dashboard-title">Necesitas acceso como curador</h1>
        <p>
          Un administrador puede habilitar tu cuenta para cargar revisiones.
        </p>
        <Link href="/mis-revisiones">Volver a mi espacio</Link>
      </section>
    );
  return (
    <>
      <ReviewSteps />
      <span className="eyebrow">Siguiente paso · Cargar revisión</span>
      <h1 className="dashboard-title">Empieza con una revisión publicada</h1>
      <p>
        Comprobaremos su acceso abierto y licencia antes de leer el documento.
        Tu revisión permanecerá privada.
      </p>
      <form className="card review-form" onSubmit={submit}>
        <label>
          DOI del artículo
          <input
            name="doi"
            required
            maxLength={255}
            placeholder="10.1234/articulo"
            autoComplete="off"
          />
        </label>
        <p className="help">
          Puedes pegar también el enlace completo que empieza por
          https://doi.org/.
        </p>
        <details>
          <summary>Añadir el PDF del artículo (opcional)</summary>
          <label className="upload-label">
            Documento PDF
            <input name="pdf" type="file" accept="application/pdf,.pdf" />
          </label>
          <p className="help">
            Hasta 20 MB. El DOI y la licencia se verificarán aunque adjuntes un
            archivo.
          </p>
        </details>
        {error && (
          <p className="message error" role="alert">
            {error}
          </p>
        )}
        <Button disabled={busy}>
          {busy ? "Preparando la lectura…" : "Comprobar y leer revisión"}
        </Button>
      </form>
      <p>
        <Link href="/mis-revisiones">Volver a mis revisiones</Link>
      </p>
    </>
  );
}
