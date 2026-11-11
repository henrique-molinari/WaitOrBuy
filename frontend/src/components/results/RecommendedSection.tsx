import { useRecommended } from "../../hooks/useRecommended";
import { GameResultCard } from "./GameResultCard";

// "Você também pode gostar": mesmo gênero dos jogos listados, depois as maiores promoções. Some sozinho se não houver nada.
export function RecommendedSection({ exclude }: { exclude: number[] }) {
  const items = useRecommended(exclude);
  if (!items.length) return null;
  return (
    <section className="tight" aria-label="Recomendados">
      <h2 className="t-display-md">Você também pode gostar</h2>
      <ul className="rlist">{items.map((r, i) => (
        <li key={r.game_id}><GameResultCard i={i} g={{ game_id: r.game_id, title: r.title, thumb: r.thumb, offer: r.offer, tag: r.reason === "genero" ? "MESMO GÊNERO" : "EM PROMOÇÃO" }} /></li>))}</ul>
    </section>
  );
}
