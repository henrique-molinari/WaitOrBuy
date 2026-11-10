// Componentes da identidade WaitOrBuy (classes wob-* de design/components.css). Só tokens.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { brl } from "./api";

export type Offer = { store_id: number; store_name: string; price_brl: number; normal_price_brl: number | null; discount_pct: number; price_origin: string; is_estimated: boolean; deal_url: string | null };
export type Point = { date: string; price_brl: number };

export const Mark = ({ size = 28 }: { size?: number }) => (
  <svg className="wob-mark" width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
    <path d="M7 13 L22 51 L32 25 L42 51 L57 13" fill="none" stroke="var(--ink)" strokeWidth="7" strokeMiterlimit="4" />
    <circle cx="42" cy="51" r="8" fill="var(--buy)" stroke="var(--ink)" strokeWidth="3.5" />
  </svg>
);

export const Wordmark = ({ size = 28 }: { size?: number }) => (
  <span className="brand"><Mark size={size} /><span className="wob-word" style={{ fontSize: size }}>Wait<i>Or</i><u>Buy</u></span></span>
);

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

// Escalonamento: --i limitado a 8 para listas longas não demorarem a aparecer.
export const stag = (i: number) => ({ "--i": Math.min(i, 8) }) as React.CSSProperties;

// Título palavra a palavra (máscara). Texto acessível fica no aria-label.
export const Words = ({ text }: { text: string }) => (
  <span className="words" aria-label={text}>{text.split(" ").map((w, i) => <span key={i} aria-hidden="true"><span className="w" style={stag(i)}><span>{w}</span></span>{" "}</span>)}</span>
);

// Skeletons com a forma do conteúdo real (evita salto de layout).
export const CardsSkeleton = ({ n = 6 }: { n?: number }) => (
  <div className="grid" aria-hidden="true">{Array.from({ length: n }, (_, i) => (
    <div key={i} className="sk-card rise" style={stag(i)}><div className="sk sk-img" /><div className="sk sk-t" /><div className="sk sk-p" /><div className="sk sk-c" /></div>
  ))}</div>
);
export const GameSkeleton = () => (
  <div className="stack" role="status" aria-label="Carregando jogo">
    <div className="tight" style={{ alignItems: "center" }}><div className="sk sk-line" style={{ width: 72 }} /><div className="sk" style={{ height: 60, width: "min(420px,80%)" }} /><div className="sk sk-line" style={{ width: 220 }} /></div>
    <div className="sk sk--card" style={{ width: "100%", maxWidth: 460, aspectRatio: "460/215", margin: "0 auto" }} />
    <div className="tight" style={{ alignItems: "center" }}><div className="sk sk-line" style={{ width: 180 }} /><div className="sk" style={{ height: 80, width: 260 }} /><div className="sk" style={{ height: 40, width: 180, borderRadius: "var(--radius-pill)" }} /></div>
    <div className="sk-rows">{[0, 1, 2, 3].map((i) => <div key={i} className="sk" />)}</div>
  </div>
);

// Botão de tema: sol ↔ lua em traço reto, girando e trocando de escala (sem preenchimento).
export const ThemeToggle = ({ dark, onClick }: { dark: boolean; onClick: () => void }) => (
  <button type="button" className="icon-btn theme-btn" aria-pressed={dark} aria-label={dark ? "Tema Noite ativo. Trocar para Papel" : "Tema Papel ativo. Trocar para Noite"} title={dark ? "Tema Papel" : "Tema Noite"} onClick={onClick}>
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="miter">
      <g className="ti ti-sun" data-on={!dark}><circle cx="12" cy="12" r="4" />{[0, 45, 90, 135, 180, 225, 270, 315].map((a) => <path key={a} d="M12 2.5v3" transform={`rotate(${a} 12 12)`} />)}</g>
      <g className="ti ti-moon" data-on={dark}><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z" /></g>
    </svg>
  </button>
);

// Campo de senha com olho: a barra "risca" o olho (traço desenhado), a pupila encolhe. Um só gesto contínuo.
export function PasswordField({ id, label, value, onChange, autoComplete, minLength, describedBy }: { id: string; label: string; value: string; onChange: (v: string) => void; autoComplete: string; minLength?: number; describedBy?: string }) {
  const [show, setShow] = useState(false);
  return (
    <div className="wob-field"><label htmlFor={id}>{label}</label>
      <div className="wob-input wob-input--text">
        <input id={id} type={show ? "text" : "password"} autoComplete={autoComplete} value={value} onChange={(e) => onChange(e.target.value)} required minLength={minLength} aria-describedby={describedBy} />
        <button type="button" className="eye-btn" aria-label={show ? "Ocultar senha" : "Mostrar senha"} aria-pressed={show} aria-controls={id} onClick={() => setShow(!show)}>
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="miter" data-off={!show}>
            <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" />
            <circle className="eye-pupil" cx="12" cy="12" r="3" />
            <path className="eye-cut" pathLength={1} d="M4 4L20 20" />
            <path className="eye-slash" pathLength={1} d="M4 4L20 20" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// Evita o flicker do skeleton: só aparece se a resposta passar de `delay`; uma vez visível, fica ao menos `min`;
// na saída dissolve para o conteúdo (os dois ocupam a mesma célula). Resposta rápida = nenhum skeleton.
export function Loadable({ ready, skeleton, children, delay = 160, min = 500 }: { ready: boolean; skeleton: ReactNode; children: () => ReactNode; delay?: number; min?: number }) {
  const [phase, setPhase] = useState<"wait" | "skel" | "out" | "done">(ready ? "done" : "wait"); const at = useRef(0);
  useEffect(() => {
    if (phase === "wait") { if (ready) { setPhase("done"); return; } const t = setTimeout(() => { at.current = Date.now(); setPhase("skel"); }, delay); return () => clearTimeout(t); }
    if (phase === "skel" && ready) { const t = setTimeout(() => setPhase("out"), Math.max(0, min - (Date.now() - at.current))); return () => clearTimeout(t); }
    if (phase === "out") { const t = setTimeout(() => setPhase("done"), 240); return () => clearTimeout(t); }
  }, [phase, ready, delay, min]);
  if (phase === "wait") return <div style={{ minHeight: "50vh" }} />;
  if (phase === "done") return <>{children()}</>;
  return <div className="xf">{phase === "out" && <div>{children()}</div>}<div className={phase === "out" ? "xf-leave" : undefined}>{skeleton}</div></div>;
}

// Aviso na tela: entra por baixo, some sozinho em 8s, sai pelo mesmo caminho. Fecha com Esc.
export function Toast({ n, onClose }: { n: { game_id: number; title: string; body: string }; onClose: () => void }) {
  const [out, setOut] = useState(false);
  const close = () => { setOut(true); setTimeout(onClose, 220); };
  useEffect(() => { setOut(false); const t = setTimeout(close, 8000); const k = (e: KeyboardEvent) => e.key === "Escape" && close(); addEventListener("keydown", k); return () => { clearTimeout(t); removeEventListener("keydown", k); }; }, [n]);
  return (
    <div className={`toast${out ? " toast--out" : ""}`} role="status">
      <Verdict verdict="COMPRAR_AGORA" small />
      <div className="toast-t"><b>{n.title}</b><small>{n.body}</small></div>
      <a className="wob-btn wob-btn--primary tbtn" href={`#/jogo/${n.game_id}`} onClick={close}>Ver jogo</a>
      <button className="wob-btn wob-btn--text" onClick={close} aria-label="Fechar aviso">Fechar</button>
    </div>
  );
}

export const Err = ({ e }: { e: string | null }) => (e ? <p role="alert" className="notice notice--wait">{e}</p> : null);
export const Cap = ({ children }: { children: ReactNode }) => <span className="wob-cap">{children}</span>;

// Ranking de lojas: 1º é o menor preço (ponto do logo); número = posição; diferença para o menor à direita.
export function StoreRows({ offers }: { offers: Offer[] }) {
  if (!offers.length) return <p className="wob-hint">Sem ofertas no momento.</p>;
  const best = offers[0].price_brl;
  return (
    <ol className="rank">
      {offers.map((o, i) => {
        const off = Math.round(o.discount_pct) > 0 ? ` · −${Math.round(o.discount_pct)}%` : "";
        return (
          <li key={o.store_id} className={`rk rise${i === 0 ? " rk--best" : ""}`} style={stag(i)}>
            <span className="rk-n" aria-label={`${i + 1}º lugar`}>{i + 1}</span>
            <div className="rk-store">
              {o.deal_url ? <a className="plain" href={o.deal_url} target="_blank" rel="sponsored noopener">{o.store_name}</a> : <b>{o.store_name}</b>}
              <small>{o.is_estimated ? "Preço estimado" : "Preço real em R$"}{off}</small>
            </div>
            <div className="rk-price">
              <span className="wob-num">{brl(o.price_brl)}</span>
              <small>{i === 0 ? "MENOR PREÇO" : `+${brl(o.price_brl - best)}`}</small>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

// Histórico: degraus retos (o preço vale até a próxima leitura). Leituras (AGORA, MENOR, MÉDIA) em HTML acima do SVG,
// sem rótulos brigando com a linha; arrastar/passar o mouse (ou ← →) mostra o preço de qualquer dia.
const nice = (raw: number) => { const p = 10 ** Math.floor(Math.log10(raw)), f = raw / p; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p; };
export function PriceChart({ points }: { points: Point[] }) {
  const box = useRef<HTMLDivElement>(null); const [W, setW] = useState(720); const [sel, setSel] = useState<number | null>(null);
  useEffect(() => { const el = box.current; if (!el) return; const ro = new ResizeObserver(() => setW(Math.max(260, el.clientWidth))); ro.observe(el); setW(Math.max(260, el.clientWidth)); return () => ro.disconnect(); }, [points.length < 2]); // o contêiner só existe depois de haver dados
  useEffect(() => setSel(null), [points]);
  if (points.length < 2) return <p className="wob-hint">Histórico ainda curto: volte em alguns dias.</p>;
  const sm = W < 520, H = sm ? 220 : 300, L = sm ? 56 : 60, R = 12, T = 16, B = 28, last = points.length - 1;
  const vals = points.map((p) => p.price_brl), min = Math.min(...vals), avg = vals.reduce((a, b) => a + b, 0) / vals.length;
  const step = nice((Math.max(...vals, avg) - Math.min(min, avg) || 1) / (sm ? 3 : 4));
  const y0 = Math.floor(Math.min(min, avg) / step) * step, y1 = Math.ceil(Math.max(...vals, avg) / step) * step || step;
  const ticks: number[] = []; for (let t = y0; t <= y1 + 1e-6; t += step) ticks.push(t);
  const x = (i: number) => L + (i / last) * (W - L - R), y = (v: number) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B), base = H - B;
  let d = `M${x(0)} ${y(vals[0])}`; for (let i = 1; i <= last; i++) d += ` H${x(i)} V${y(vals[i])}`;
  const li = vals.lastIndexOf(min), dt = (i: number) => points[i].date.split("-").reverse().slice(0, 2).join("/");
  const xt = sm ? [0, Math.round(last / 2), last] : [0, 1, 2, 3, 4].map((k) => Math.round((last * k) / 4));
  const at = (e: React.PointerEvent<SVGRectElement>) => { const r = e.currentTarget.getBoundingClientRect(); setSel(Math.max(0, Math.min(last, Math.round(((e.clientX - r.left) / r.width) * last)))); };
  const key = (e: React.KeyboardEvent) => { if (e.key === "ArrowLeft") { e.preventDefault(); setSel((v) => Math.max(0, (v ?? last) - 1)); } else if (e.key === "ArrowRight") { e.preventDefault(); setSel((v) => Math.min(last, (v ?? last) + 1)); } else if (e.key === "Escape") setSel(null); };
  const nowSel = sel ?? last;
  return (
    <div className="chartbox">
      <dl className="cstats">
        <div className={sel !== null ? "cs cs--sel" : "cs"}><dt className="wob-cap">{sel !== null ? `EM ${dt(sel)}` : "AGORA"}</dt><dd className="wob-num">{brl(vals[nowSel])}</dd></div>
        <div className="cs"><dt className="wob-cap"><i className="sw sw--low" />MENOR</dt><dd className="wob-num">{brl(min)}</dd></div>
        <div className="cs"><dt className="wob-cap"><i className="sw sw--avg" />MÉDIA</dt><dd className="wob-num">{brl(avg)}</dd></div>
      </dl>
      <div ref={box} className="chartbox-in" style={{ height: H }}>
        <svg className="wob-chart" width={W} height={H} role="slider" tabIndex={0} aria-label="Histórico de preços. Use as setas para ver cada dia" aria-valuemin={0} aria-valuemax={last} aria-valuenow={nowSel} aria-valuetext={`${dt(nowSel)}: ${brl(vals[nowSel])}`} onKeyDown={key} onBlur={() => setSel(null)}>
          {ticks.map((t) => <g key={t}><line className="grid" x1={L} x2={W - R} y1={y(t)} y2={y(t)} /><text x={L - 8} y={y(t) + 4} textAnchor="end">R$ {Math.round(t)}</text></g>)}
          <path key={`a${points.length}${points[0].date}`} className="area late" d={`${d} V${base} H${x(0)} Z`} />
          <path className="avg" d={`M${L} ${y(avg)} H${W - R}`} />
          <path key={`${points.length}${points[0].date}`} className="line" pathLength={1} d={d} />
          <circle className="low late" cx={x(li)} cy={y(min)} r="8" />
          {sel === null && li !== last && <circle className="now late" cx={x(last)} cy={y(vals[last])} r="5" />}
          {sel !== null && <g className="scrub" pointerEvents="none"><line x1={x(sel)} x2={x(sel)} y1={T} y2={base} /><circle cx={x(sel)} cy={y(vals[sel])} r="6" /></g>}
          {xt.map((i, k) => <text key={i} x={x(i)} y={H - 8} textAnchor={k === 0 ? "start" : i === last ? "end" : "middle"}>{dt(i)}</text>)}
          <rect className="hit" x={L} y={T} width={W - L - R} height={H - T - B} onPointerDown={at} onPointerMove={at} onPointerLeave={(e) => e.pointerType === "mouse" && setSel(null)} />
        </svg>
      </div>
    </div>
  );
}
