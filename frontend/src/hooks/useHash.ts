import { useEffect, useState } from "react";

// Rota por hash (#/busca?q=hades): devolve o caminho e os parâmetros; rola ao topo na mudança.
export function useHash() {
  const [h, setH] = useState(location.hash || "#/");
  useEffect(() => { const f = () => { setH(location.hash || "#/"); scrollTo(0, 0); }; addEventListener("hashchange", f); return () => removeEventListener("hashchange", f); }, []);
  const [path, query = ""] = h.replace(/^#\//, "").split("?");
  return { hash: h, path, params: new URLSearchParams(query) };
}
