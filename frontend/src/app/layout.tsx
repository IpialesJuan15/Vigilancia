import type { Metadata } from "next";
import Link from "next/link";
import { AuthProvider } from "@/components/auth-provider";
import { Header } from "@/components/header";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/inter/latin-700.css";
import "./globals.css";
export const metadata: Metadata = {
  title: "LiveSRL · Evidencia que sigue viva",
  description:
    "Revisiones sistemáticas de literatura vivas sobre fuentes de acceso abierto.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>
        <a className="skip" href="#contenido">
          Ir al contenido
        </a>
        <AuthProvider>
          <Header />
          <main id="contenido">{children}</main>
        </AuthProvider>
        <footer>
          <strong>LiveSRL</strong>
          <span>La evidencia evoluciona. La atribución permanece.</span>
          <Link href="/privacidad">Privacidad</Link>
          <Link href="/terminos">Términos</Link>
        </footer>
      </body>
    </html>
  );
}
