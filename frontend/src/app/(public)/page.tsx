import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  ShieldCheck,
  RefreshCw,
  Quote,
} from "lucide-react";
const steps = [
  ["Cargar revisión", "Parte de una revisión publicada en acceso abierto."],
  ["Confirmar método", "Verifica el método extraído y su evidencia."],
  ["Revisar candidatos", "Decide qué estudios cumplen tus criterios."],
  ["Publicar actualización", "Comparte tablas actualizadas con atribución."],
];
export default function Home() {
  return (
    <>
      <section className="hero">
        <div>
          <span className="eyebrow">
            Conocimiento abierto · Revisión humana
          </span>
          <h1>
            La investigación avanza.
            <br />
            <span className="accent">Tu revisión también.</span>
          </h1>
          <p>
            Transforma una revisión sistemática publicada en un recurso vivo.
            Nueva evidencia, tablas actualizadas y reconocimiento para sus
            autores.
          </p>
          <Link className="button primary" href="/catalogo">
            Explorar revisiones <ArrowRight size={18} />
          </Link>
        </div>
        <div className="hero-visual" aria-label="Principios de LiveSRL">
          <span className="eyebrow">Evidencia que sigue viva</span>
          {[
            [BookOpen, "Una revisión como punto de partida"],
            [RefreshCw, "Vigilancia de fuentes abiertas"],
            [ShieldCheck, "Cada cambio, revisado por personas"],
            [Quote, "La atribución siempre permanece"],
          ].map(([Icon, text], i) => {
            const Component = Icon as typeof BookOpen;
            return (
              <div className="visual-row" key={i}>
                <Component size={22} aria-hidden="true" />
                <span>{text as string}</span>
              </div>
            );
          })}
        </div>
      </section>
      <section>
        <div className="section-head">
          <h2>De una publicación a una revisión viva</h2>
          <span className="help">Un proceso claro, en cuatro pasos</span>
        </div>
        <div className="steps">
          {steps.map(([title, description], i) => (
            <article key={title}>
              <span className="visual-number">{i + 1}</span>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="card">
        <h2>Construida para investigar con confianza</h2>
        <p>
          Solo fuentes de acceso abierto. Cada dato debe estar acompañado de una
          cita verificable. Cada actualización requiere revisión humana antes de
          publicarse.
        </p>
        <Link href="/registro">Crear mi cuenta →</Link>
      </section>
    </>
  );
}
