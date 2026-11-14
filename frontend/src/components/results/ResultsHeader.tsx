import type { SearchResponse } from "../../types";

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

// Título da listagem e avisos da busca (parecidos, jogos novos, lojas fora do ar).
export function ResultsHeader({ q, data }: { q: string; data: SearchResponse | null }) {
  return (
    <>
      <h1 className="t-display-md">{q ? `Resultados para “${q}”` : "Catálogo"}{data && <span className="wob-cap"> · {plural(data.count, "jogo", "jogos")}</span>}</h1>
      {data?.fuzzy && data.count > 0 && <p role="status" className="notice notice--info">Não achamos “{q}” exatamente. {data.did_you_mean && <>Você quis dizer <a href={`#/busca?q=${encodeURIComponent(data.did_you_mean)}`}>{data.did_you_mean}</a>? </>}Mostrando jogos com nome parecido.</p>}
      {data && data.discovered > 0 && <p role="status" className="notice notice--buy">Encontramos {plural(data.discovered, "jogo novo", "jogos novos")} nas lojas conectadas e já adicionamos ao catálogo.</p>}
      {data?.live_error && <p role="status" className="notice notice--info">{data.live_error}</p>}
    </>
  );
}
