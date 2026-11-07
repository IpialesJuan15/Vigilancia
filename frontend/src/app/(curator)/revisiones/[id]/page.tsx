"use client";
import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { type Review, stateLabel } from "@/lib/reviews";
import { ReviewSteps } from "@/components/review/steps";
import { Button } from "@/components/ui/button";
export default function DocumentPage() {
  const { id } = useParams<{ id: string }>();
  const params = useSearchParams();
  const [review, setReview] = useState<Review | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("Secciones");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const value = await api<Review>(`/reviews/${id}`);
        if (!active) return;
        setReview(value);
        setError("");
        if (!["parsed", "failed", "license_review"].includes(value.status))
          timer = setTimeout(load, 2000);
      } catch {
        if (active)
          setError(
            "No pudimos cargar esta revisión. Comprueba tu sesión y vuelve a intentar",
          );
      }
    }
    void load();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [id]);
  async function act(action: string) {
    setBusy(true);
    setError("");
    try {
      await api(`/reviews/${id}/${action}`, {});
      window.location.reload();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "No pudimos completar la acción",
      );
    } finally {
      setBusy(false);
    }
  }
  if (!review)
    return (
      <section>
        <p role={error ? "alert" : "status"}>
          {error || "Abriendo la revisión…"}
        </p>
        <Link href="/mis-revisiones">Volver a mis revisiones</Link>
      </section>
    );
  const doc = review.document;
  return (
    <>
      <ReviewSteps />
      {params.has("existente") && (
        <p className="message" role="status">
          Esta revisión ya existe. Hemos abierto su registro.
        </p>
      )}
      <span className="eyebrow">{stateLabel[review.status]}</span>
      <h1 className="document-title">{review.original_title}</h1>
      <p>
        {review.original_authors
          .map(
            (a) =>
              a.fullName ||
              [a.first_name, a.last_name].filter(Boolean).join(" "),
          )
          .join(", ")}
      </p>
      <p>
        {review.journal} {review.year ? `· ${review.year}` : ""}{" "}
        {review.license ? `· ${review.license}` : ""}
      </p>
      <a
        href={`https://doi.org/${review.original_doi}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        Artículo original ↗
      </a>
      <aside className="next-step">
        <strong>Siguiente paso</strong>
        <p>{review.stage}</p>
        {!["parsed", "failed", "license_review"].includes(review.status) && (
          <progress
            value={review.progress}
            max={100}
            aria-label="Progreso de lectura"
          />
        )}
        {review.status === "parsed" && (
          <p className="help">
            Comprueba la lectura del documento. La extracción del método se
            habilitará en la siguiente etapa.
          </p>
        )}
        {review.status === "parsed" && (
          <Button
            onClick={() => {
              setTab("Tablas");
              requestAnimationFrame(() =>
                document
                  .getElementById("document-panel")
                  ?.scrollIntoView({ block: "start" }),
              );
            }}
          >
            Comprobar tablas
          </Button>
        )}
      </aside>
      {error && (
        <p role="alert" className="message error">
          {error}
        </p>
      )}
      {review.status === "failed" && (
        <section className="card">
          <p role="alert">{review.error_message}</p>
          <Button disabled={busy} onClick={() => void act("retry")}>
            Volver a intentar
          </Button>
        </section>
      )}
      {review.warnings.map((w) => (
        <p className="availability-note" key={w}>
          {w}
        </p>
      ))}
      {review.status === "license_review" && (
        <section className="card">
          <h2>Confirma el uso permitido</h2>
          <p>
            Una licencia con restricciones exige revisar sus condiciones. Para
            licencias que prohíben derivados, las tablas solo podrán tratarse
            como datos reextraídos con atribución, sujetos a revisión humana.
          </p>
          <label className="consent">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            He revisado la licencia y confirmo estas condiciones de uso.
          </label>
          <Button
            disabled={!confirmed || busy}
            onClick={() => void act("confirm-license")}
          >
            Confirmar y continuar la lectura
          </Button>
          {!confirmed && (
            <p className="help">
              Revisa las condiciones y marca la confirmación para continuar.
            </p>
          )}
        </section>
      )}
      {doc && (
        <section className="card document-view">
          <div
            className="document-tabs"
            role="tablist"
            aria-label="Contenido del documento"
          >
            {["Secciones", "Tablas", "Referencias"].map((name) => (
              <button
                key={name}
                id={`tab-${name}`}
                role="tab"
                aria-selected={tab === name}
                aria-controls="document-panel"
                onClick={() => setTab(name)}
              >
                {name} (
                {name === "Secciones"
                  ? doc.sections.length
                  : name === "Tablas"
                    ? doc.tables.length
                    : doc.references.length}
                )
              </button>
            ))}
          </div>
          <div
            id="document-panel"
            role="tabpanel"
            aria-labelledby={`tab-${tab}`}
          >
            {tab === "Secciones" &&
              doc.sections.map((section, i) => (
                <details className="document-section" key={i} open={i === 0}>
                  <summary>{section.title}</summary>
                  {section.paragraphs.map((p, j) => (
                    <div key={j}>
                      <span className="help">{p.location}</span>
                      <p className="source-paragraph">{p.text}</p>
                    </div>
                  ))}
                </details>
              ))}
            {tab === "Tablas" &&
              (doc.tables.length ? (
                doc.tables.map((table, i) => (
                  <article className="parsed-table" key={i}>
                    <h2>{table.caption}</h2>
                    <p className="help">
                      {table.location}
                      {table.needs_review
                        ? " · Revisar estructura de la tabla"
                        : ""}
                    </p>
                    <div
                      className="table-scroll"
                      tabIndex={0}
                      role="region"
                      aria-label={table.caption}
                    >
                      <table>
                        <thead>
                          {(
                            table.header_cells ??
                            table.header.map((row) =>
                              row.map((value) => ({
                                text: value,
                                rowspan: "1",
                                colspan: "1",
                              })),
                            )
                          ).map((row, j) => (
                            <tr key={j}>
                              {row.map((c, k) => (
                                <th
                                  key={k}
                                  rowSpan={Math.min(
                                    100,
                                    Math.max(1, Number(c.rowspan) || 1),
                                  )}
                                  colSpan={Math.min(
                                    100,
                                    Math.max(1, Number(c.colspan) || 1),
                                  )}
                                >
                                  {c.text}
                                </th>
                              ))}
                            </tr>
                          ))}
                        </thead>
                        <tbody>
                          {table.rows.map((row, j) => (
                            <tr key={j}>
                              {row.map((c, k) => (
                                <td
                                  key={k}
                                  rowSpan={Math.min(
                                    100,
                                    Math.max(1, Number(c.rowspan) || 1),
                                  )}
                                  colSpan={Math.min(
                                    100,
                                    Math.max(1, Number(c.colspan) || 1),
                                  )}
                                >
                                  {c.text}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {table.footnotes?.map((note, j) => (
                      <p className="help" key={j}>
                        {note}
                      </p>
                    ))}
                  </article>
                ))
              ) : (
                <p>No se encontraron tablas legibles en el documento.</p>
              ))}
            {tab === "Referencias" &&
              (doc.references.length ? (
                doc.references.map((ref, i) => (
                  <article className="reference" key={i}>
                    <span className="help">{ref.location}</span>
                    <p>{ref.text}</p>
                    {ref.doi && (
                      <a
                        href={`https://doi.org/${ref.doi}`}
                        rel="noopener noreferrer"
                        target="_blank"
                      >
                        Ver referencia ↗
                      </a>
                    )}
                  </article>
                ))
              ) : (
                <p>
                  No se encontraron referencias estructuradas. Comprueba el
                  documento original.
                </p>
              ))}
          </div>
          <p>
            <a href={`/api/reviews/${id}/source`}>
              Descargar documento original
            </a>
          </p>
        </section>
      )}
      <p>
        <Link href="/mis-revisiones">Volver a mis revisiones</Link>
      </p>
    </>
  );
}
