import { Suspense } from "react";
import { AuthForm } from "@/components/auth-form";
export default function Page() {
  return (
    <Suspense fallback={<p role="status">Cargando…</p>}>
      <AuthForm mode="verificar-correo" />
    </Suspense>
  );
}
