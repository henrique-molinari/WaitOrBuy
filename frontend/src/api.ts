import { auth } from "./firebase";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown; authed?: boolean } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (opts.body) headers["Content-Type"] = "application/json";
  if (opts.authed) {
    const token = await auth.currentUser?.getIdToken();
    if (!token) throw new Error("Faça login para continuar.");
    headers.Authorization = `Bearer ${token}`;
  }
  let res: Response;
  try {
    res = await fetch(BASE + path, { method: opts.method ?? "GET", headers, body: opts.body ? JSON.stringify(opts.body) : undefined });
  } catch {
    throw new Error("Não foi possível falar com a API.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.error?.message ?? `Erro ${res.status}`);
  return data as T;
}

export const brl = (v: number | null | undefined) => (v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }));
