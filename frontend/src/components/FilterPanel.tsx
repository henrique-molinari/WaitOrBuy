import type { Facet, Filters, SortKey } from "../types";
import { Cap } from "./Text";

const SORTS: [SortKey, string][] = [["relevance", "Relevância"], ["price", "Menor preço"], ["discount", "Maior desconto"], ["stores", "Mais lojas"], ["title", "A–Z"]];

// Filtros da busca: lojas (com contagem), preço máximo, desconto mínimo e ordenação.
export function FilterPanel({ f, facets, onChange }: { f: Filters; facets: Facet[]; onChange: (f: Filters) => void }) {
  const toggle = (id: number) => onChange({ ...f, stores: f.stores.includes(id) ? f.stores.filter((s) => s !== id) : [...f.stores, id] });
  const active = f.stores.length > 0 || f.maxPrice !== "" || f.minDiscount > 0;
  return (
    <aside className="filters wob-card" aria-label="Filtros da busca">
      <div className="head"><h2 className="t-price-md wob-num">Filtros</h2>
        {active && <button className="wob-btn wob-btn--text" onClick={() => onChange({ ...f, stores: [], maxPrice: "", minDiscount: 0 })}>Limpar</button>}</div>
      <div className="wob-field"><label htmlFor="sort">Ordenar por</label>
        <div className="wob-input"><select id="sort" value={f.sort} onChange={(e) => onChange({ ...f, sort: e.target.value as SortKey })}>{SORTS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></div></div>
      <div className="wob-field"><label htmlFor="maxp">Preço máximo</label>
        <div className="wob-input"><span>R$</span><input id="maxp" inputMode="decimal" value={f.maxPrice} onChange={(e) => onChange({ ...f, maxPrice: e.target.value.replace(/[^\d.,]/g, "") })} /></div></div>
      <div className="wob-field"><label htmlFor="mind">Desconto mínimo</label>
        <div className="wob-input"><select id="mind" value={f.minDiscount} onChange={(e) => onChange({ ...f, minDiscount: Number(e.target.value) })}>{[0, 10, 25, 50, 75].map((d) => <option key={d} value={d}>{d === 0 ? "Qualquer" : `${d}% ou mais`}</option>)}</select></div></div>
      <fieldset className="stores"><legend><Cap>LOJAS</Cap></legend>
        {facets.length === 0 && <p className="wob-hint">Faça uma busca para filtrar por loja.</p>}
        {facets.map((s) => (
          <label key={s.store_id} className="chk"><input type="checkbox" checked={f.stores.includes(s.store_id)} onChange={() => toggle(s.store_id)} /><span>{s.name}</span><small>{s.count}</small></label>))}
      </fieldset>
    </aside>
  );
}
