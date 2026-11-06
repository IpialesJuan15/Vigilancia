"use client";
import { useEffect, useState } from "react";
import { api, User } from "@/lib/api";
export default function Admin() {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api<User[]>("/admin/users")
      .then(setUsers)
      .catch((e) => setError(e.message));
  }, []);
  return (
    <>
      <span className="eyebrow">Administración</span>
      <h1 className="dashboard-title">Usuarios y roles</h1>
      {error ? (
        <p role="alert">{error}</p>
      ) : (
        <section className="card">
          {users.map((user) => (
            <article key={user.id}>
              <h2>{user.name}</h2>
              <p>
                {user.email ?? "Cuenta ORCID"} ·{" "}
                {user.role === "admin"
                  ? "Administrador"
                  : user.role === "curator"
                    ? "Curador"
                    : "Suscriptor"}
              </p>
            </article>
          ))}
        </section>
      )}
    </>
  );
}
