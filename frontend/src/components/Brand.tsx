// Marca WaitOrBuy (logo + wordmark).
export const Mark = ({ size = 28 }: { size?: number }) => (
  <svg className="wob-mark" width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
    <path d="M7 13 L22 51 L32 25 L42 51 L57 13" fill="none" stroke="var(--ink)" strokeWidth="7" strokeMiterlimit="4" />
    <circle cx="42" cy="51" r="8" fill="var(--buy)" stroke="var(--ink)" strokeWidth="3.5" />
  </svg>
);

export const Wordmark = ({ size = 28 }: { size?: number }) => (
  <span className="brand"><Mark size={size} /><span className="wob-word" style={{ fontSize: size }}>Wait<i>Or</i><u>Buy</u></span></span>
);

