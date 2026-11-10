// Vistos recentemente: só no navegador (localStorage), sem API. Funciona logado ou não.
export type Recent = { id: number; title: string; thumb: string | null };
const KEY = "wob-recent";
export const getRecent = (): Recent[] => { try { return JSON.parse(localStorage.getItem(KEY) ?? "[]"); } catch { return []; } };
export const pushRecent = (r: Recent) => { try { localStorage.setItem(KEY, JSON.stringify([r, ...getRecent().filter((x) => x.id !== r.id)].slice(0, 8))); } catch { /* sem storage */ } };
export const clearRecent = () => { try { localStorage.removeItem(KEY); } catch { /* sem storage */ } };
