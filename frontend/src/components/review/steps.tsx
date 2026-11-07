export function ReviewSteps() {
  return (
    <ol className="review-steps" aria-label="Pasos de tu revisión">
      {[
        "Cargar revisión",
        "Confirmar método",
        "Revisar candidatos",
        "Publicar actualización",
      ].map((title, i) => (
        <li key={title} aria-current={i === 0 ? "step" : undefined}>
          <span>{i + 1}</span>
          {title}
        </li>
      ))}
    </ol>
  );
}
