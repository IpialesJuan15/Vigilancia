"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { BookOpen, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
export function Header() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const value = localStorage.getItem("theme") === "dark";
    document.documentElement.dataset.theme = value ? "dark" : "light";
  }, []);
  function toggle() {
    const value = document.documentElement.dataset.theme !== "dark";
    setDark(value);
    document.documentElement.dataset.theme = value ? "dark" : "light";
    localStorage.setItem("theme", value ? "dark" : "light");
  }
  return (
    <>
      <div className="staging">Entorno de prueba — DOIs no oficiales</div>
      <header>
        <Link className="brand" href="/">
          <BookOpen aria-hidden="true" /> Live<span>SRL</span>
        </Link>
        <nav aria-label="Navegación principal">
          <Link href="/catalogo">Explorar</Link>
          <Link href="/mis-revisiones">Mi espacio</Link>
          <Link href="/login">Iniciar sesión</Link>
          <Button variant="outline" onClick={toggle} aria-label="Cambiar tema">
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </Button>
        </nav>
      </header>
    </>
  );
}
