"""Carrinho da wishlist: total por loja (lojas completas primeiro) e melhor combinação entre lojas."""


def build_cart(games: dict[int, str], offers: dict[int, list[dict]]) -> dict:
    """games: {game_id: título}; offers: {game_id: [ofertas com store_id/store_name/price_brl/...]}."""
    stores: dict[int, dict] = {}
    for gid, offs in offers.items():
        for o in offs:
            stores.setdefault(o["store_id"], {"store_id": o["store_id"], "store_name": o["store_name"], "by_game": {}})
            cur = stores[o["store_id"]]["by_game"].get(gid)
            if cur is None or o["price_brl"] < cur["price_brl"]:
                stores[o["store_id"]]["by_game"][gid] = o

    def item(gid: int, o: dict) -> dict:
        return {"game_id": gid, "title": games[gid], "price_brl": o["price_brl"], "price_origin": o["price_origin"],
                "deal_url": o["deal_url"]}

    rows = []
    for s in stores.values():
        missing = [{"game_id": g, "title": t} for g, t in games.items() if g not in s["by_game"]]
        rows.append({
            "store_id": s["store_id"], "store_name": s["store_name"],
            "total_brl": round(sum(o["price_brl"] for o in s["by_game"].values()), 2),
            "complete": not missing, "missing_games": missing, "game_count": len(s["by_game"]),
            "items": [item(g, o) for g, o in s["by_game"].items()],
        })
    rows.sort(key=lambda r: (not r["complete"], r["total_brl"], r["store_id"]))

    mix_items, mix_missing = [], []
    for gid, title in games.items():
        offs = offers.get(gid) or []
        if not offs:
            mix_missing.append({"game_id": gid, "title": title})
            continue
        b = min(offs, key=lambda o: o["price_brl"])
        mix_items.append({**item(gid, b), "store_id": b["store_id"], "store_name": b["store_name"]})
    mix_total = round(sum(i["price_brl"] for i in mix_items), 2)
    best_complete = next((r for r in rows if r["complete"]), None)
    savings = round(best_complete["total_brl"] - mix_total, 2) if best_complete else None
    return {
        "game_count": len(games), "stores": rows,
        "best_mix": {"total_brl": mix_total, "items": mix_items, "missing_games": mix_missing,
                     "savings_vs_best_store_brl": savings},
    }
