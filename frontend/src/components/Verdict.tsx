// Veredito: COMPRAR_AGORA | ESPERAR | NEUTRO | INSUFICIENTE.
const ICON = {
  buy: <path d="M9 2v11M3 8l6 6 6-6" fill="none" stroke="currentColor" strokeWidth="3" />,
  wait: <path d="M5 2v14M13 2v14" fill="none" stroke="currentColor" strokeWidth="3.5" />,
};

// API: COMPRAR_AGORA | ESPERAR | NEUTRO | INSUFICIENTE. NEUTRO/INSUFICIENTE não ganham verde nem vermelho.
export function Verdict({ verdict, small }: { verdict: string; small?: boolean }) {
  const sm = small ? " wob-verdict--sm" : "";
  if (verdict === "COMPRAR_AGORA") return <span className={`wob-verdict wob-verdict--buy${sm}`}><svg viewBox="0 0 18 18" aria-hidden="true">{ICON.buy}</svg>{small ? "Compre" : "Compre agora"}</span>;
  if (verdict === "ESPERAR") return <span className={`wob-verdict wob-verdict--wait${sm}`}><svg viewBox="0 0 18 18" aria-hidden="true">{ICON.wait}</svg>{small ? "Espere" : "Vale esperar"}</span>;
  return <span className={`wob-verdict wob-verdict--none${sm}`}>{verdict === "INSUFICIENTE" ? "Pouco histórico" : "Sem veredito claro"}</span>;
}

