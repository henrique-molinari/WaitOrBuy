import { useEffect, useState } from "react";
import { api } from "../api";
import type { Filters, SearchResponse } from "../types";

export function searchPath(q: string, f: Filters) {
  const p = new URLSearchParams({ q, sort: f.sort, limit: "48" });
  f.stores.forEach((s) => p.append("store", String(s)));
  const max = Number(f.maxPrice.replace(",", "."));
  if (max > 0) p.set("max_price", String(max));
  if (f.minDiscount) p.set("min_discount", String(f.minDiscount));
  return `/api/search?${p}`;
}

// Busca com filtros. Descarta respostas atrasadas. O backend só consulta as lojas ao vivo uma vez por termo (cache de 6 h).
export function useSearch(q: string, f: Filters) {
  const [data, setData] = useState<SearchResponse | null>(null); const [err, setErr] = useState<string | null>(null); const [loading, setLoading] = useState(true);
  const key = JSON.stringify([q, f]);
  useEffect(() => {
    let dead = false; setLoading(true); setErr(null);
    api<SearchResponse>(searchPath(q, f)).then((d) => { if (!dead) { setData(d); setLoading(false); } }).catch((e) => { if (!dead) { setErr(e.message); setLoading(false); } });
    return () => { dead = true; };
  }, [key]);
  return { data, err, loading };
}
