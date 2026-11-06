import { BookOpen } from "lucide-react";
export default function Catalog() {
  return (
    <>
      <span className="eyebrow">Conocimiento abierto</span>
      <h1 className="dashboard-title">Explorar revisiones</h1>
      <p>Encuentra revisiones sistemáticas vivas y consulta su evidencia.</p>
      <section className="card empty">
        <BookOpen size={36} aria-hidden="true" />
        <h2>Aún no hay revisiones publicadas</h2>
        <p>
          Cuando se publique la primera revisión, podrás consultar aquí sus
          tablas, novedades y referencias.
        </p>
      </section>
    </>
  );
}
