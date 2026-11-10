import { Cap, Err, Loadable, StoreBadge } from "../components";
import { usePlatforms } from "../hooks/usePlatforms";

const KIND_LABEL = { brl_real: "PREÇO REAL EM R$", mixed: "R$ REAL + PARTE ESTIMADA", usd_converted: "ESTIMADO (USD→BRL)" } as const;
const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "—");

// Transparência: quais lojas e provedores alimentam os preços, e como cada preço é obtido.
export default function Plataformas() {
  const { data, err } = usePlatforms();
  return (
    <div className="stack">
      <div className="tight"><a className="plain" href="#/">← Voltar</a><h1 className="t-display-lg">Lojas conectadas</h1>
        <p className="wob-hint">Preços reais em reais vêm direto da loja (Steam, Epic, GOG, Nuuvem, Instant Gaming). As demais lojas, e as ofertas que essas lojas não confirmaram, vêm em dólar pela CheapShark e são convertidas pelo PTAX do Banco Central.</p></div>
      <Err e={err} />
      <Loadable ready={!!data || !!err} skeleton={<div className="sk sk--card" style={{ height: 240 }} />}>{() => data && <>
        <section className="tight" aria-label="Lojas">
          <h2 className="t-display-md">{data.count} lojas · {data.total_games} jogos no catálogo</h2>
          <ul className="plist">{data.platforms.map((p) => (
            <li key={p.store_id} className="item">
              <div className="grow"><StoreBadge id={p.store_id} name={p.name} estimated={p.price_kind === "usd_converted" ? true : p.price_kind === "brl_real" ? false : undefined} /><small>{p.source}</small></div>
              <span className="wob-data">{p.games} jogos</span><Cap>{KIND_LABEL[p.price_kind]} · {when(p.last_captured_at)}</Cap>
            </li>))}</ul>
        </section>
        <section className="tight" aria-label="Provedores de dados">
          <h2 className="t-display-md">Provedores de dados</h2>
          <ul className="plist">{data.providers.map((p) => (
            <li key={p.name} className="item"><div className="grow"><b>{p.name}</b><small>{p.role}</small></div>
              <Cap>{p.enabled ? "ATIVO" : p.needs_key ? "PRECISA DE CHAVE" : "INATIVO"}</Cap></li>))}</ul>
        </section>
      </>}</Loadable>
    </div>
  );
}
