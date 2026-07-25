// Small shared presentation pieces. Kept tiny and prop-driven.

import Link from "next/link";

const SEV_ORDER = ["high", "medium", "low"] as const;

export function SeverityChip({
  severity,
  count,
}: {
  severity: string;
  count?: number;
}) {
  const cls = SEV_ORDER.includes(severity as (typeof SEV_ORDER)[number])
    ? severity
    : "muted";
  return (
    <span className={`chip ${cls}`}>
      <span className="dot" />
      {count !== undefined ? `${count} ${severity}` : severity}
    </span>
  );
}

// Compact severity breakdown, hiding zero-count severities so the row stays quiet.
export function SeverityCounts({
  high,
  medium,
  low,
}: {
  high: number;
  medium: number;
  low: number;
}) {
  const entries: [string, number][] = [
    ["high", high],
    ["medium", medium],
    ["low", low],
  ];
  const shown = entries.filter(([, n]) => n > 0);
  if (shown.length === 0) {
    return <span className="chip muted">none</span>;
  }
  return (
    <span className="sev-counts">
      {shown.map(([sev, n]) => (
        <SeverityChip key={sev} severity={sev} count={n} />
      ))}
    </span>
  );
}

// Renders "owner/repo #123" with the PR number accented.
export function RepoRef({
  repo,
  prNumber,
}: {
  repo: string;
  prNumber: number | null;
}) {
  const slash = repo.lastIndexOf("/");
  const owner = slash >= 0 ? repo.slice(0, slash + 1) : "";
  const name = slash >= 0 ? repo.slice(slash + 1) : repo;
  return (
    <span className="repo">
      <span className="owner">{owner}</span>
      {name}
      {prNumber !== null && <span className="pr"> #{prNumber}</span>}
    </span>
  );
}

export function EmptyState({
  mark,
  title,
  children,
}: {
  mark: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="panel">
      <div className="empty">
        <div className="mark">{mark}</div>
        <div style={{ color: "var(--head)", fontWeight: 600, marginBottom: 6 }}>
          {title}
        </div>
        <div>{children}</div>
      </div>
    </div>
  );
}

export function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const secs = Math.round((Date.now() - then) / 1000);
  const table: [number, string][] = [
    [60, "s"],
    [60, "m"],
    [24, "h"],
    [7, "d"],
  ];
  let value = secs;
  let unit = "s";
  for (const [step, label] of table) {
    if (Math.abs(value) < step) break;
    value = Math.round(value / step);
    unit = label;
  }
  return value <= 0 ? "just now" : `${value}${unit} ago`;
}

export { Link };
