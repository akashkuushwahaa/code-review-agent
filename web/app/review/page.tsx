import { getReviewDetail, type Finding } from "@/lib/api";
import { EmptyState, Link, RepoRef, SeverityCounts } from "@/components/ui";

export const dynamic = "force-dynamic";

function groupByFile(findings: Finding[]): [string, Finding[]][] {
  const map = new Map<string, Finding[]>();
  for (const f of findings) {
    const list = map.get(f.file) ?? [];
    list.push(f);
    map.set(f.file, list);
  }
  return [...map.entries()];
}

export default async function ReviewPage({
  searchParams,
}: {
  searchParams: Promise<{ pr?: string }>;
}) {
  const { pr } = await searchParams;

  if (!pr) {
    return (
      <EmptyState mark="○" title="No pull request selected">
        Pick one from the <Link href="/">reviews list</Link>.
      </EmptyState>
    );
  }

  const detail = await getReviewDetail(pr);

  return (
    <>
      <Link href="/" className="back">
        ← All reviews
      </Link>

      {!detail ? (
        <EmptyState mark="○" title="No findings recorded for that PR">
          It may not have been reviewed yet.
        </EmptyState>
      ) : (
        <>
          <div className="page-head">
            <div className="eyebrow">Review detail</div>
            <h1 style={{ fontFamily: "var(--font-mono)", fontSize: 21 }}>
              <RepoRef repo={detail.repo} prNumber={detail.pr_number} />
            </h1>
            <div style={{ marginTop: 12, display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
              <span className="dim nums">
                {detail.total_findings} finding{detail.total_findings === 1 ? "" : "s"}
              </span>
              <SeverityCounts high={detail.high} medium={detail.medium} low={detail.low} />
              <a
                href={detail.pr_url}
                target="_blank"
                rel="noreferrer"
                className="chip muted"
                style={{ textDecoration: "none" }}
              >
                open on GitHub ↗
              </a>
            </div>
          </div>

          {groupByFile(detail.findings).map(([file, findings]) => (
            <div className="file-group" key={file}>
              <div className="file-name">
                <span className="icon" aria-hidden>▤</span>
                {file}
              </div>
              {findings.map((f) => {
                const sev = ["high", "medium", "low"].includes(f.severity ?? "")
                  ? (f.severity as string)
                  : "low";
                return (
                  <div className={`finding ${sev}`} key={f.id}>
                    <div className="stripe" />
                    <div className="line">L{f.line ?? "?"}</div>
                    <div className="body">
                      <div className="issue">{f.issue ?? "Security finding"}</div>
                      {f.explanation && (
                        <div className="explanation">{f.explanation}</div>
                      )}
                    </div>
                    <div className="meta">
                      <span className={`chip ${sev}`}>
                        <span className="dot" />
                        {sev}
                      </span>
                      {f.posted && <span className="chip ok">posted</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          ))}

          <p className="dim" style={{ fontSize: 12, marginTop: 18, textWrap: "pretty" }}>
            Findings are shown as line-anchored annotations. The raw diff isn't
            stored (the agent persists findings, not patches), so this view lists
            each finding against its file and line rather than rendering the full
            diff.
          </p>
        </>
      )}
    </>
  );
}
