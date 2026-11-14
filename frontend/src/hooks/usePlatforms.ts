import { useEffect, useState } from "react";
import { api } from "../api";
import type { PlatformsResponse } from "../types";

export function usePlatforms() {
  const [data, setData] = useState<PlatformsResponse | null>(null); const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api<PlatformsResponse>("/api/platforms").then(setData).catch((e) => setErr(e.message)); }, []);
  return { data, err };
}
