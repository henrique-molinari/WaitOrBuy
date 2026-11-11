import { useEffect, useState } from "react";
import { CardsSkeleton, Err, FilterPanel, GameResultList, Loadable, RecommendedSection, ResultsHeader, SearchBar, StoreBadge } from "../components";
import { useSearch } from "../hooks/useSearch";
import { NO_FILTERS, type Filters } from "../types";

// Tela de resultados (Enter na busca): todos os jogos achados, cada um com o menor preço, e recomendados embaixo.
// O termo vem da URL (#/busca?q=...), os filtros ficam no estado.
export default function Busca({ q }: { q: string }) {
  const [f, setF] = useState<Filters>(NO_FILTERS);
  useEffect(() => setF(NO_FILTERS), [q]); // novo termo = filtros limpos
  const { data, err, loading } = useSearch(q, f);
  const go = (t: string) => { location.hash = `#/busca?q=${encodeURIComponent(t)}`; };
  const ids = (data?.results ?? []).map((r) => r.game_id);
  return (
    <div className="stack">
      <section className="tight">
        <a className="plain" href="#/">← Início</a>
        <SearchBar initial={q} onSubmit={go} />
      </section>
      <Err e={err} />
      <div className="busca">
        <FilterPanel f={f} facets={data?.facets ?? []} onChange={setF} />
        <section className="tight" aria-live="polite" aria-busy={loading}>
          <ResultsHeader q={q} data={data} />
          {f.stores.length > 0 && data && <p className="wob-hint">Mostrando só ofertas de: {data.facets.filter((s) => f.stores.includes(s.store_id)).map((s) => <StoreBadge key={s.store_id} id={s.store_id} name={s.name} />)}</p>}
          <Loadable ready={!loading} skeleton={<CardsSkeleton />}>{() => data && <GameResultList results={data.results} />}</Loadable>
        </section>
      </div>
      {!loading && data && <RecommendedSection exclude={ids} />}
    </div>
  );
}
