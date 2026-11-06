import Link from "next/link";
export default function NotFound() {
  return (
    <section className="empty">
      <h1 className="dashboard-title">No encontramos esta página</h1>
      <p>El enlace puede haber cambiado.</p>
      <Link className="button primary" href="/">
        Volver al inicio
      </Link>
    </section>
  );
}
