import { api, brl } from "../api";
import { PushStatusPanel } from "../push";
import type { User } from "../session";

export default function Avisos({ items, user }: { items: any[]; user: User }) {
  const read = (id: string) => api(`/api/me/notifications/${id}/read`, { method: "POST", authed: true }).catch(() => {});
  return (
    <div className="stack">
      <h1 className="t-display-lg">Avisos</h1>
      <PushStatusPanel uid={user.uid} />
      {items.length === 0 ? <p className="body">Nenhum aviso ainda. Quando um jogo chegar ao seu preço, ele aparece aqui.</p> : <div role="list" aria-live="polite">
        {items.map((n) => (
          <div role="listitem" key={n.id} className={`item${n.read ? "" : " unread item--hit"}`}>
            <div className="grow"><a className="plain" href={`#/jogo/${n.game_id}`}><strong>{n.title}</strong></a><small>{n.body}</small></div>
            <span className="t-price-md wob-num">{brl(n.price_brl)}</span>
            {!n.read && <button className="wob-btn wob-btn--text" onClick={() => read(n.id)}>Marcar como lido</button>}
          </div>))}
      </div>}
    </div>
  );
}
