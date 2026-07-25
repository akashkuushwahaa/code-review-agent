// Server-side data access. Pages are server components, so they fetch directly
// from the API (no client JS, no CORS). API_URL is the internal address:
// localhost in dev, the `api` service name in Docker.

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export type ReviewSummary = {
  pr_url: string;
  repo: string;
  pr_number: number | null;
  files: number;
  total_findings: number;
  high: number;
  medium: number;
  low: number;
  posted: number;
  last_reviewed: string | null;
};

export type Finding = {
  id: number;
  file: string;
  line: number | null;
  severity: "high" | "medium" | "low" | string | null;
  issue: string | null;
  explanation: string | null;
  commit_sha: string | null;
  posted: boolean;
  created_at: string | null;
};

export type ReviewDetail = {
  pr_url: string;
  repo: string;
  pr_number: number | null;
  total_findings: number;
  high: number;
  medium: number;
  low: number;
  findings: Finding[];
};

export type EvalResults = {
  model: string | null;
  full_file_context: boolean | null;
  cross_file_retrieval: boolean | null;
  summary: {
    precision: number;
    recall: number;
    f1: number;
    tp: number;
    fp: number;
    fn: number;
    cases: number;
    tolerance: number | null;
  };
  cases: { id: string; expected: number; tp: number; fp: number; fn: number }[];
};

async function get<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    // API down or unreachable — pages render a friendly empty state.
    return null;
  }
}

export const getReviews = () =>
  get<{ total: number; items: ReviewSummary[] }>("/api/reviews");

export const getReviewDetail = (prUrl: string) =>
  get<ReviewDetail>(`/api/reviews/detail?pr_url=${encodeURIComponent(prUrl)}`);

export const getEval = () => get<EvalResults>("/api/eval");
