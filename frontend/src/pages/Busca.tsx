import { useEffect, useState } from "react";
import { CardsSkeleton, Err, FilterPanel, Loadable, ResultsGrid, SearchBar, StoreBadge } from "../components";
import { useSearch } from "../hooks/useSearch";
import { NO_FILTERS, type Filters } from "../types";

// Busca em todas as plataformas conectadas: o termo vem da URL (#/busca?q=...), os filtros ficam no estado.
export default function Busca({ q }: { q: string }) {
  const [f, setF] = useState<Filters>(NO_FILTERS);
  useEffect(() => setF(NO_FILTERS), [q]); // novo termo = filtros limpos
  const { data, err, loading } = useSearch(q, f);
  const go = (t: string) => { location.hash = `#/busca?q=${encodeURIComponent(t)}`; };
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
          <h1 className="t-display-md">{q ? `Resultados para “${q}”` : "Catálogo"}{data && <span className="wob-cap"> · {data.count} {data.count === 1 ? "jogo" : "jogos"}</span>}</h1>
          {data && data.discovered > 0 && <p role="status" className="notice notice--buy">Encontramos {data.discovered} {data.discovered === 1 ? "jogo novo" : "jogos novos"} nas lojas conectadas e já adicionamos ao catálogo.</p>}
          {data?.live_error && <p role="status" className="notice notice--info">{data.live_error}</p>}
          {f.stores.length > 0 && data && <p className="wob-hint">Mostrando só ofertas de: {data.facets.filter((s) => f.stores.includes(s.store_id)).map((s) => <StoreBadge key={s.store_id} id={s.store_id} name={s.name} />)}</p>}
          <Loadable ready={!loading} skeleton={<CardsSkeleton />}>{() => data && <ResultsGrid results={data.results} />}</Loadable>
        </section>
      </div>
    </div>
  );
}
