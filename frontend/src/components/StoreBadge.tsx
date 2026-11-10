// Selo de loja: marca se o preço é real em R$ (Steam, Nuuvem, Instant Gaming) ou estimado pelo dólar PTAX.
const REAL = new Set([1, 100, 101]);
export const isRealBrl = (storeId: number) => REAL.has(storeId);

export function StoreBadge({ id, name }: { id: number; name: string }) {
  return <span className={`sbadge${isRealBrl(id) ? " sbadge--real" : ""}`} title={isRealBrl(id) ? "Preço real em R$" : "Preço estimado (USD → BRL pelo PTAX)"}>{name}</span>;
}
