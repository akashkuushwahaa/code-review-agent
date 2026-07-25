import { getReviews } from "@/lib/api";
import {
  EmptyState,
  Link,
  RepoRef,
  SeverityCounts,
  relativeTime,
} from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function ReviewsPage() {
  const data = await getReviews();
  const reviews = data?.items ?? [];

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Review history</div>
        <h1>Reviewed pull requests</h1>
        <p>
          Every PR the agent has scanned for security issues, most recent first.
          Findings are deduplicated across re-runs.
        </p>
      </div>

      {data === null ? (
        <EmptyState mark="⚠" title="Can't reach the API">
          Start it with <code>uvicorn api.main:app</code> (or{" "}
          <code>docker compose up</code>).
        </EmptyState>
      ) : reviews.length === 0 ? (
        <EmptyState mark="○" title="No reviews yet">
          Run <code>python review.py &lt;pr-url&gt;</code> and findings will show
          up here.
        </EmptyState>
      ) : (
        <div className="panel">
          <table>
            <thead>
              <tr>
                <th>Pull request</th>
                <th>Findings</th>
                <th className="cell-num hide-sm">Files</th>
                <th className="cell-num hide-sm">Posted</th>
                <th className="cell-num">Reviewed</th>
              </tr>
            </thead>
            <tbody>
              {reviews.map((r) => (
                <tr className="row" key={r.pr_url}>
                  <td>
                    <Link
                      href={`/review?pr=${encodeURIComponent(r.pr_url)}`}
                      style={{ display: "block" }}
                    >
                      <RepoRef repo={r.repo} prNumber={r.pr_number} />
                    </Link>
                  </td>
                  <td>
                    <SeverityCounts high={r.high} medium={r.medium} low={r.low} />
                  </td>
                  <td className="cell-num nums mono dim hide-sm">{r.files}</td>
                  <td className="cell-num nums mono dim hide-sm">
                    {r.posted}/{r.total_findings}
                  </td>
                  <td className="cell-num nums dim" style={{ whiteSpace: "nowrap" }}>
                    {relativeTime(r.last_reviewed)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
