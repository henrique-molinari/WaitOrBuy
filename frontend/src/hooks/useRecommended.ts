import { useEffect, useState } from "react";
import { api } from "../api";
import type { RecommendedItem } from "../types";

// Recomendações para a tela de resultados. Falha silenciosa: é complemento, não pode atrapalhar a busca.
export function useRecommended(exclude: number[], limit = 8) {
  const [items, setItems] = useState<RecommendedItem[]>([]);
  const key = exclude.join(",");
  useEffect(() => {
    let dead = false;
    const p = new URLSearchParams({ limit: String(limit) });
    exclude.slice(0, 60).forEach((id) => p.append("exclude", String(id)));
    api(`/api/recommended?${p}`).then((d) => { if (!dead) setItems(d.items); }).catch(() => { if (!dead) setItems([]); });
    return () => { dead = true; };
  }, [key, limit]);
  return items;
}
