import type { PlatformsResponse } from "../types";
import { StoreBadge } from "./StoreBadge";

// Faixa "lojas conectadas": mostra de onde vêm os preços (BRL real × estimado).
export function PlatformsStrip({ data }: { data: PlatformsResponse | null }) {
  if (!data) return null;
  return (
    <section className="tight" aria-label="Lojas conectadas">
      <div className="head"><h2 className="t-display-md">{data.count} lojas conectadas</h2><a className="plain" href="#/plataformas">Ver detalhes</a></div>
      <p className="wob-hint">Em destaque, as que informam o preço real em reais. As demais são convertidas do dólar.</p>
      <div className="line">{data.platforms.map((p) => <StoreBadge key={p.store_id} id={p.store_id} name={p.name} />)}</div>
    </section>
  );
}
