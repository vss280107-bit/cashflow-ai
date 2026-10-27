export function BrandMark({ className = "" }) {
  return <svg className={`brand-mark ${className}`} viewBox="0 0 32 32" fill="none" aria-hidden="true">
    <path d="M23.5 7.1A11.1 11.1 0 1 0 23.7 24.8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    <path d="M11.2 12.7h8m0 0-2-2m2 2-2 2M11.2 19.2h5.6" stroke="currentColor" strokeWidth="1.55" strokeLinecap="round" strokeLinejoin="round" />
  </svg>;
}

export function NavigationIcon({ kind }) {
  const common = { width: 18, height: 18, viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.5, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true };
  if (kind === "dashboard") return <svg {...common}><rect x="2.5" y="2.5" width="6" height="6" rx="1"/><rect x="11.5" y="2.5" width="6" height="6" rx="1"/><rect x="2.5" y="11.5" width="6" height="6" rx="1"/><rect x="11.5" y="11.5" width="6" height="6" rx="1"/></svg>;
  if (kind === "transactions") return <svg {...common}><path d="M4 6h11m0 0-2.5-2.5M15 6l-2.5 2.5M16 14H5m0 0 2.5-2.5M5 14l2.5 2.5"/></svg>;
  return <svg {...common}><path d="M2.5 15.5 7 11l3 2.5 6.5-7"/><path d="M12.5 6.5h4v4"/><path d="M2.5 17.5h15"/></svg>;
}
