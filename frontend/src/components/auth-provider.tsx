"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { usePathname } from "next/navigation";
import { api, ApiError, type User } from "@/lib/api";

type Session = {
  status: "loading" | "authenticated" | "anonymous" | "error";
  user: User | null;
};
type AuthContextValue = Session & {
  refresh: () => Promise<void>;
  signIn: (user: User) => void;
  signOut: () => Promise<void>;
};
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session>({
    status: "loading",
    user: null,
  });
  const revision = useRef(0);
  const channel = useRef<BroadcastChannel | null>(null);
  const pathname = usePathname();
  const refresh = useCallback(async () => {
    const request = ++revision.current;
    try {
      const user = await api<User>("/me");
      if (request === revision.current)
        setSession({ status: "authenticated", user });
    } catch (error) {
      if (request !== revision.current) return;
      setSession({
        status:
          error instanceof ApiError && error.status === 401
            ? "anonymous"
            : "error",
        user: null,
      });
    }
  }, []);
  const signIn = useCallback((user: User) => {
    ++revision.current; // Discard any older check started before the cookie changed.
    setSession({ status: "authenticated", user });
    channel.current?.postMessage("changed");
  }, []);
  const signOut = useCallback(async () => {
    await api("/auth/logout", {});
    ++revision.current;
    setSession({ status: "anonymous", user: null });
    channel.current?.postMessage("changed");
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [pathname, refresh]);
  useEffect(() => {
    const onFocus = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    const onExpired = () => {
      ++revision.current;
      setSession({ status: "anonymous", user: null });
    };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onFocus);
    window.addEventListener("session-expired", onExpired);
    if (typeof BroadcastChannel !== "undefined") {
      const connection = new BroadcastChannel("livesrl-session");
      channel.current = connection;
      connection.onmessage = () => {
        void refresh();
      };
    }
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onFocus);
      window.removeEventListener("session-expired", onExpired);
      channel.current?.close();
      channel.current = null;
    };
  }, [refresh]);
  return (
    <AuthContext.Provider value={{ ...session, refresh, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("AuthProvider is required");
  return context;
}
