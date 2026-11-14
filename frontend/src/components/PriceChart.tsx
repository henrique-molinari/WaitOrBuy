import { useEffect, useRef, useState } from "react";
import { brl } from "../api";
import type { Point } from "../types";

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
