import type { ReactNode } from "react";

export const Err = ({ e }: { e: string | null }) => (e ? <p role="alert" className="notice notice--wait">{e}</p> : null);
export const Cap = ({ children }: { children: ReactNode }) => <span className="wob-cap">{children}</span>;
