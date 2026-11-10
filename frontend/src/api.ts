import { getToken, MOCK } from "./session";
import { mockApi } from "./mock";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8001";

// Só usado quando a resposta não traz `error.message` (ex.: proxy ou servidor fora do ar).
const friendly = (status: number) =>
  status === 401 ? "Você precisa entrar na sua conta para fazer isso."
    : status === 404 ? "Não encontramos o que você procurou."
    : status === 429 ? "Muitas requisições; tente novamente em instantes."
    : status >= 500 ? "Alguns serviços estão fora do ar agora. Tente novamente em instantes."
    : "Não foi possível concluir a ação. Tente novamente.";

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown; authed?: boolean } = {}): Promise<T> {
  if (MOCK) return (await mockApi(path, opts)) as T;
  const headers: Record<string, string> = {};
  if (opts.body) headers["Content-Type"] = "application/json";
  if (opts.authed) {
    const token = await getToken();
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
  if (!res.ok) throw new Error(data?.error?.message ?? friendly(res.status));
  return data as T;
}

export const brl = (v: number | null | undefined) => (v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }));
