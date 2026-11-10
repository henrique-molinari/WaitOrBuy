// Push no navegador (FCM). Pede permissão com contexto antes do prompt do navegador; registra o token em /api/me/devices.
import { useState } from "react";
import { api } from "./api";
import { MOCK } from "./session";
import { Cap } from "./ui";

export type PushStatus = "unsupported" | "unconfigured" | "off" | "on" | "denied";
const VAPID = import.meta.env.VITE_FCM_VAPID_KEY as string | undefined;
const REG = "wob-push-uid", ASKED = "wob-push-asked", COOLDOWN = 14 * 864e5;
const ls = { get: (k: string) => { try { return localStorage.getItem(k); } catch { return null; } }, set: (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* sem storage */ } } };

export function pushStatus(uid: string): PushStatus {
  if (typeof Notification === "undefined" || !("serviceWorker" in navigator) || !("PushManager" in window)) return "unsupported";
  if (!MOCK && !VAPID) return "unconfigured";
  if (Notification.permission === "denied") return "denied";
  return Notification.permission === "granted" && ls.get(REG) === uid ? "on" : "off";
}
const askedRecently = () => Date.now() - Number(ls.get(ASKED) ?? 0) < COOLDOWN;

async function enablePush(uid: string): Promise<PushStatus> {
  const perm = await Notification.requestPermission();
  if (perm !== "granted") return perm === "denied" ? "denied" : "off";
  const reg = await navigator.serviceWorker.register("/push-sw.js"); await navigator.serviceWorker.ready;
  let token = `mock-${uid}`;
  if (!MOCK) { const [{ getMessaging, getToken }, { app }] = await Promise.all([import("firebase/messaging"), import("./firebase")]); token = await getToken(getMessaging(app), { vapidKey: VAPID, serviceWorkerRegistration: reg }); }
  await api("/api/me/devices", { method: "POST", body: { token, platform: "web" }, authed: true });
  ls.set(REG, uid); return "on";
}
async function testPush() {
  const reg = await navigator.serviceWorker.ready;
  await reg.showNotification("WaitOrBuy", { body: "Pronto: os avisos chegam assim neste dispositivo.", icon: "/favicon.svg", data: { url: "/#/avisos" }, tag: "teste" });
}

function usePush(uid: string) {
  const [st, setSt] = useState<PushStatus>(() => pushStatus(uid)); const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null); const [fresh, setFresh] = useState(false);
  const enable = async () => { setBusy(true); setErr(null); try { const s = await enablePush(uid); setSt(s); setFresh(s === "on"); if (s === "off") ls.set(ASKED, String(Date.now())); } catch { setErr("Não foi possível ativar agora. Tente de novo em instantes."); } finally { setBusy(false); } };
  const test = () => testPush().catch(() => setErr("Não foi possível mostrar o teste."));
  return { st, busy, err, fresh, enable, test };
}

const Bell = () => (
  <svg className="bell" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="miter">
    <path d="M6 17v-6a6 6 0 1 1 12 0v6M4 17h16M10 20.5h4" />
  </svg>
);

// Cartão de pedido de permissão, mostrado num momento de valor. Texto vem de quem chama (cita jogo e preço).
export function PushPrompt({ uid, title, body }: { uid: string; title: string; body: string }) {
  const { st, busy, err, fresh, enable, test } = usePush(uid); const [hide, setHide] = useState(() => askedRecently());
  if (fresh && st === "on") return (
    <div className="notice notice--buy pushcard rise" role="status"><Cap>NOTIFICAÇÕES ATIVAS</Cap><p className="body">Pronto. Avisamos neste dispositivo quando chegar ao seu preço.</p><button className="wob-btn wob-btn--secondary" onClick={test}>Testar neste dispositivo</button></div>);
  if (st !== "off" || hide) return null;
  return (
    <div className="wob-card pushcard rise" role="region" aria-label="Ativar notificações">
      <Bell /><h3 className="t-price-md wob-num">{title}</h3><p className="wob-hint">{body}</p>
      {err && <p role="alert" className="notice notice--wait">{err}</p>}
      <div className="line">
        <button className="wob-btn wob-btn--primary" disabled={busy} onClick={enable}>{busy ? "Aguardando o navegador…" : "Ativar notificações"}</button>
        <button className="wob-btn wob-btn--text" onClick={() => { ls.set(ASKED, String(Date.now())); setHide(true); }}>Agora não</button>
      </div>
      <p className="wob-hint pushnote">Depois do seu aceite, o navegador pede uma confirmação. Você pode desligar quando quiser nas permissões do site.</p>
    </div>);
}

// Estado do push neste dispositivo, sempre visível na tela de Avisos.
export function PushStatusPanel({ uid }: { uid: string }) {
  const { st, busy, err, enable, test } = usePush(uid);
  const MSG: Record<PushStatus, string> = {
    on: "Notificações ativas neste dispositivo.", off: "Notificações desligadas neste dispositivo.",
    denied: "Notificações bloqueadas no navegador. Libere nas permissões do site (ícone de cadeado) e recarregue.",
    unsupported: "Este navegador não recebe notificações push. Os avisos continuam aparecendo aqui.",
    unconfigured: "Push ainda não configurado neste ambiente. Os avisos continuam aparecendo aqui.",
  };
  return (
    <div className="wob-card pushstatus rise" role="status">
      <span className={`dot dot--${st}`} aria-hidden="true" /><span className="wob-hint">{err ?? MSG[st]}</span>
      {st === "off" && <button className="wob-btn wob-btn--primary tbtn" disabled={busy} onClick={enable}>{busy ? "Aguardando…" : "Ativar"}</button>}
      {st === "on" && <button className="wob-btn wob-btn--secondary tbtn" onClick={test}>Testar</button>}
    </div>);
}
