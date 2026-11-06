"use client";
import { Button } from "@/components/ui/button";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <section className="empty">
      <h1 className="dashboard-title">Algo salió mal</h1>
      <p>No pudimos mostrar esta página.</p>
      <Button onClick={reset}>Intentar de nuevo</Button>
    </section>
  );
}
