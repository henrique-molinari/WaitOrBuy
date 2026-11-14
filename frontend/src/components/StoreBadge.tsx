// Selo de loja: marca se o preço é real em R$ ou estimado pelo dólar PTAX.
// Com `estimated` (vindo da oferta) vale o que a API diz; sem ele, só as lojas que SEMPRE trazem R$ real (Steam, Nuuvem, Instant Gaming).
// Epic e GOG variam (real quando a loja respondeu, estimado quando não), então dependem da oferta.
const ALWAYS_REAL = new Set([1, 100, 101]);
export const isRealBrl = (storeId: number, estimated?: boolean) => (estimated === undefined ? ALWAYS_REAL.has(storeId) : !estimated);

export function StoreBadge({ id, name, estimated }: { id: number; name: string; estimated?: boolean }) {
  const real = isRealBrl(id, estimated);
  return <span className={`sbadge${real ? " sbadge--real" : ""}`} title={real ? "Preço real em R$" : "Preço estimado (USD → BRL pelo PTAX)"}>{name}</span>;
}
