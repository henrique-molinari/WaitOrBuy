import type { Facet, Filters, SortKey } from "../types";
import { Cap } from "./Text";

const SORTS: [SortKey, string][] = [["relevance", "Relevância"], ["price", "Menor preço"], ["discount", "Maior desconto"], ["stores", "Mais lojas"], ["title", "A–Z"]];

// Atalhos de um clique. "50%/90% off" e "Até R$10/R$20" são pares: ligar um desliga o outro (mesmo campo do filtro).
const QUICK = [
  { id: "buy", label: "Compre agora", on: (f: Filters) => f.buyNow, set: (f: Filters, on: boolean): Filters => ({ ...f, buyNow: on }) },
  { id: "d90", label: "90% off", on: (f: Filters) => f.minDiscount === 90, set: (f: Filters, on: boolean): Filters => ({ ...f, minDiscount: on ? 90 : 0 }) },
  { id: "d50", label: "50% off", on: (f: Filters) => f.minDiscount === 50, set: (f: Filters, on: boolean): Filters => ({ ...f, minDiscount: on ? 50 : 0 }) },
  { id: "p10", label: "Até R$10", on: (f: Filters) => f.maxPrice === "10", set: (f: Filters, on: boolean): Filters => ({ ...f, maxPrice: on ? "10" : "" }) },
  { id: "p20", label: "Até R$20", on: (f: Filters) => f.maxPrice === "20", set: (f: Filters, on: boolean): Filters => ({ ...f, maxPrice: on ? "20" : "" }) },
];

// Filtros da busca: atalhos, lojas (com contagem), preço máximo, desconto mínimo e ordenação.
export function FilterPanel({ f, facets, onChange }: { f: Filters; facets: Facet[]; onChange: (f: Filters) => void }) {
  const toggle = (id: number) => onChange({ ...f, stores: f.stores.includes(id) ? f.stores.filter((s) => s !== id) : [...f.stores, id] });
  const active = f.stores.length > 0 || f.maxPrice !== "" || f.minDiscount > 0 || f.buyNow;
  return (
    <aside className="filters wob-card" aria-label="Filtros da busca">
      <div className="head"><h2 className="t-price-md wob-num">Filtros</h2>
        {active && <button className="wob-btn wob-btn--text" onClick={() => onChange({ ...f, stores: [], maxPrice: "", minDiscount: 0, buyNow: false })}>Limpar</button>}</div>
      <div className="qchips" role="group" aria-label="Atalhos de filtro">
        {QUICK.map((c) => { const on = c.on(f); return <button key={c.id} type="button" className="qchip" aria-pressed={on} onClick={() => onChange(c.set(f, !on))}>{c.label}</button>; })}
      </div>
      <div className="wob-field"><label htmlFor="sort">Ordenar por</label>
        <div className="wob-input"><select id="sort" value={f.sort} onChange={(e) => onChange({ ...f, sort: e.target.value as SortKey })}>{SORTS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></div></div>
      <div className="wob-field"><label htmlFor="maxp">Preço máximo</label>
        <div className="wob-input"><span>R$</span><input id="maxp" inputMode="decimal" value={f.maxPrice} onChange={(e) => onChange({ ...f, maxPrice: e.target.value.replace(/[^\d.,]/g, "") })} /></div></div>
      <div className="wob-field"><label htmlFor="mind">Desconto mínimo</label>
        <div className="wob-input"><select id="mind" value={f.minDiscount} onChange={(e) => onChange({ ...f, minDiscount: Number(e.target.value) })}>{[0, 10, 25, 50, 75, 90].map((d) => <option key={d} value={d}>{d === 0 ? "Qualquer" : `${d}% ou mais`}</option>)}</select></div></div>
      <fieldset className="stores"><legend><Cap>LOJAS</Cap></legend>
        {facets.length === 0 && <p className="wob-hint">Faça uma busca para filtrar por loja.</p>}
        {facets.map((s) => (
          <label key={s.store_id} className="chk"><input type="checkbox" checked={f.stores.includes(s.store_id)} onChange={() => toggle(s.store_id)} /><span>{s.name}</span><small>{s.count}</small></label>))}
      </fieldset>
    </aside>
  );
}
