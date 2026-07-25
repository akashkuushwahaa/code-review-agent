import { getEval } from "@/lib/api";
import { EmptyState } from "@/components/ui";

export const dynamic = "force-dynamic";

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

function Metric({ label, value, fraction }: { label: string; value: string; fraction: number }) {
  return (
    <div className="metric">
      <div className="label">{label}</div>
      <div className="value nums">{value}</div>
      <div className="meter">
        <span style={{ width: `${Math.max(0, Math.min(1, fraction)) * 100}%` }} />
      </div>
    </div>
  );
}

export default async function EvalPage() {
  const data = await getEval();

  if (!data) {
    return (
      <>
        <div className="page-head">
          <div className="eyebrow">Evaluation</div>
          <h1>Eval metrics</h1>
        </div>
        <EmptyState mark="○" title="No eval snapshot available">
          Generate one with{" "}
          <code>python eval.py --json api/eval_snapshot.json</code>.
        </EmptyState>
      </>
    );
  }

  const s = data.summary;
  const passed = data.cases.filter((c) => c.fp === 0 && c.fn === 0).length;

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Evaluation</div>
        <h1>Eval metrics</h1>
        <p>
          Accuracy against a labeled set of {s.cases} diffs — measured, not
          eyeballed. A detection counts when it matches the expected category
          within ±{s.tolerance ?? 3} lines.
        </p>
      </div>

      <div className="metric-row">
        <Metric label="Precision" value={pct(s.precision)} fraction={s.precision} />
        <Metric label="Recall" value={pct(s.recall)} fraction={s.recall} />
        <Metric label="F1 score" value={s.f1.toFixed(3)} fraction={s.f1} />
      </div>

      <div className="context-strip">
        <span>model <b>{data.model ?? "—"}</b></span>
        <span>cases <b className="nums">{s.cases}</b></span>
        <span>true pos <b className="nums">{s.tp}</b></span>
        <span>false pos <b className="nums">{s.fp}</b></span>
        <span>false neg <b className="nums">{s.fn}</b></span>
        {data.full_file_context && <span className="chip ok">full-file context</span>}
        {data.cross_file_retrieval && <span className="chip ok">cross-file retrieval</span>}
      </div>

      <div className="section-label">
        Per-case results — {passed}/{data.cases.length} clean
      </div>
      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Case</th>
              <th className="cell-num">Expected</th>
              <th className="cell-num">TP</th>
              <th className="cell-num">FP</th>
              <th className="cell-num">FN</th>
              <th className="cell-num">Result</th>
            </tr>
          </thead>
          <tbody>
            {data.cases.map((c) => {
              const clean = c.fp === 0 && c.fn === 0;
              return (
                <tr className="row" key={c.id}>
                  <td className="mono" style={{ fontSize: 12.5, color: "var(--text)" }}>
                    {c.id}
                  </td>
                  <td className="cell-num nums mono dim">{c.expected}</td>
                  <td className="cell-num nums mono dim">{c.tp}</td>
                  <td className="cell-num nums mono" style={{ color: c.fp ? "var(--sev-high)" : "var(--text-faint)" }}>
                    {c.fp}
                  </td>
                  <td className="cell-num nums mono" style={{ color: c.fn ? "var(--sev-high)" : "var(--text-faint)" }}>
                    {c.fn}
                  </td>
                  <td className="cell-num">
                    <span className={`tag ${clean ? "pass" : "fail"}`}>
                      {clean ? "PASS" : "FAIL"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
