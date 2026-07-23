"""
Eval Harness for the Security Review Agent
------------------------------------------
Measures how well the agent actually performs, instead of eyeballing output.

Runs the agent's review step against a labeled set of diffs (`eval/cases/`)
and scores detected findings against the expected ones, reporting precision,
recall, and F1.

Matching is deliberately *not* exact-line: a finding counts as a true positive
when it has the same issue CATEGORY and lands within a few lines of the label
(a hardcoded-secret flagged one line off is still a correct catch).

The labeled set includes clean/safe cases with zero expected findings — those
exist to measure false positives, which precision would otherwise hide.

Usage:
    python eval.py                     # score the whole set
    python eval.py --verbose           # also list every FP and FN
    python eval.py --case 03-sql-injection-fstring
    python eval.py --json baseline.json
"""

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import review

EVAL_DIR = Path(__file__).parent / "eval"
CASES_DIR = EVAL_DIR / "cases"

# Default line tolerance — the phase spec calls exact-line matching too strict.
DEFAULT_TOLERANCE = 3

# The five categories the agent is scoped to. Order matters: the first match
# wins, so more specific patterns must come before more general ones (e.g.
# "command injection ... unsanitized input" must resolve to command_injection,
# not missing_input_validation).
# Word-boundary regexes, not plain substrings: a bare "eval" needle would also
# match "evaluated" and silently misfile a hardcoded-secret finding.
CATEGORY_PATTERNS = [
    ("sql_injection", r"sql\s*inject|\bsqli\b"),
    ("command_injection", r"command\s*inject|shell\s*inject|os\.system|"
                          r"shell\s*=\s*true|shell command|subprocess"),
    ("unsafe_deserialization", r"deserial|pickle|yaml\.load|marshal|"
                               r"\beval\b|\bexec\b"),
    ("hardcoded_secret", r"hardcod|secret|credential|api[\s_-]*key|password|"
                         r"private key|\btokens?\b"),
    ("missing_input_validation", r"validat|unvalidated|sanitiz"),
]


def categorize(finding: dict) -> str:
    """Map a model finding's free-text title/explanation to a known category."""
    text = f"{finding.get('issue', '')} {finding.get('explanation', '')}".lower()
    for category, pattern in CATEGORY_PATTERNS:
        if re.search(pattern, text):
            return category
    return "other"


# ---------- Loading cases ----------

def load_cases(case_filter=None) -> list:
    if not CASES_DIR.exists():
        sys.exit(f"No cases directory at {CASES_DIR}")
    cases = []
    for path in sorted(CASES_DIR.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        if case_filter and case_filter not in case["id"]:
            continue
        cases.append(case)
    if not cases:
        sys.exit("No cases matched.")
    return cases


def full_file_for_case(case: dict):
    """The file's full contents, for cases that exercise full-file context.

    An explicit `source_file` wins. Otherwise the fixture is reconstructed from
    the patch itself — cases 01-15 are whole-new-file diffs, so every line of
    the file is present in the hunk and reconstruction is exact.
    """
    if case.get("source_file"):
        return (EVAL_DIR / case["source_file"]).read_text(encoding="utf-8")

    lines = []
    for raw in patch_for_case(case).splitlines():
        if raw.startswith("@@") or raw.startswith(("---", "+++")):
            continue
        if raw.startswith("-"):
            continue  # removed: not part of the new file
        lines.append(raw[1:] if raw[:1] in ("+", " ") else raw)
    return "\n".join(lines) + "\n"


def patch_for_case(case: dict) -> str:
    """Local diff fixture, or fetch the diff from a real PR if given a URL."""
    if case.get("patch_file"):
        return (EVAL_DIR / case["patch_file"]).read_text(encoding="utf-8")

    # Optional: a case can reference a live PR instead of a local fixture.
    pr_url = case.get("pr_url")
    if not pr_url:
        raise ValueError(f"Case {case['id']} has neither patch_file nor pr_url")
    repo_name, pr_number = review.parse_pr_url(pr_url)
    pr = review.get_gh().get_repo(repo_name).get_pull(pr_number)
    for f in review.get_reviewable_files(pr):
        if f.filename == case["filename"]:
            return f.patch
    raise ValueError(f"{case['filename']} not found in {pr_url}")


# ---------- Scoring ----------

def score_case(case: dict, tolerance: int, use_context: bool = True) -> dict:
    """Run the agent on one case and match findings against the labels."""
    patch = patch_for_case(case)
    full_file = full_file_for_case(case) if use_context else None
    detected = review.review_file(case["filename"], patch, full_file=full_file)

    for d in detected:
        d["category"] = categorize(d)

    expected = [dict(e) for e in case["expected"]]
    unmatched_detected = list(detected)
    true_positives, false_negatives = [], []

    for exp in expected:
        # Among same-category detections in range, take the closest line.
        candidates = [
            d for d in unmatched_detected
            if d["category"] == exp["category"]
            and abs(_line_of(d) - exp["line"]) <= tolerance
        ]
        if candidates:
            best = min(candidates, key=lambda d: abs(_line_of(d) - exp["line"]))
            unmatched_detected.remove(best)
            true_positives.append({"expected": exp, "detected": best})
        else:
            false_negatives.append(exp)

    return {
        "id": case["id"],
        "description": case.get("description", ""),
        "filename": case["filename"],
        "expected_count": len(expected),
        "detected_count": len(detected),
        "tp": true_positives,
        "fp": unmatched_detected,
        "fn": false_negatives,
        "is_clean_case": not expected,
    }


def _line_of(finding: dict) -> int:
    try:
        return int(finding.get("line", -999))
    except (TypeError, ValueError):
        return -999


def prf(tp: int, fp: int, fn: int):
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


# ---------- Reporting ----------

def report(results: list, tolerance: int, verbose: bool):
    tp = sum(len(r["tp"]) for r in results)
    fp = sum(len(r["fp"]) for r in results)
    fn = sum(len(r["fn"]) for r in results)
    precision, recall, f1 = prf(tp, fp, fn)

    print("\n" + "=" * 68)
    print(f"EVAL RESULTS  —  {len(results)} case(s), line tolerance ±{tolerance}")
    print("=" * 68)

    print(f"\n{'CASE':<34} {'EXP':>4} {'TP':>4} {'FP':>4} {'FN':>4}   RESULT")
    print("-" * 68)
    for r in results:
        ok = not r["fp"] and not r["fn"]
        label = "pass" if ok else "FAIL"
        print(f"{r['id']:<34} {r['expected_count']:>4} {len(r['tp']):>4} "
              f"{len(r['fp']):>4} {len(r['fn']):>4}   {label}")

    print("\n" + "-" * 68)
    print(f"True positives : {tp}")
    print(f"False positives: {fp}")
    print(f"False negatives: {fn}")
    print(f"\nPrecision: {precision:.3f}   Recall: {recall:.3f}   F1: {f1:.3f}")

    # Per-category breakdown — where the agent is strong vs. weak.
    cats = {}
    for r in results:
        for m in r["tp"]:
            cats.setdefault(m["expected"]["category"], [0, 0, 0])[0] += 1
        for d in r["fp"]:
            cats.setdefault(d["category"], [0, 0, 0])[1] += 1
        for e in r["fn"]:
            cats.setdefault(e["category"], [0, 0, 0])[2] += 1
    if cats:
        print(f"\n{'CATEGORY':<28} {'TP':>4} {'FP':>4} {'FN':>4}   {'P':>6} {'R':>6} {'F1':>6}")
        print("-" * 68)
        for name in sorted(cats):
            c_tp, c_fp, c_fn = cats[name]
            p, rc, cf1 = prf(c_tp, c_fp, c_fn)
            print(f"{name:<28} {c_tp:>4} {c_fp:>4} {c_fn:>4}   {p:>6.2f} {rc:>6.2f} {cf1:>6.2f}")

    # Clean cases isolate false-positive behavior.
    clean = [r for r in results if r["is_clean_case"]]
    if clean:
        silent = sum(1 for r in clean if not r["fp"])
        print(f"\nClean/safe cases with zero findings: {silent}/{len(clean)}"
              f"   (measures false-positive resistance)")

    if verbose:
        print("\n" + "=" * 68)
        print("FALSE POSITIVES  (flagged, but not in the labels)")
        print("=" * 68)
        any_fp = False
        for r in results:
            for d in r["fp"]:
                any_fp = True
                tag = " [CLEAN CASE]" if r["is_clean_case"] else ""
                print(f"\n- {r['id']}{tag}  {r['filename']}:{d.get('line')}")
                print(f"  [{d.get('severity')}] {d.get('issue')}  (category: {d['category']})")
                print(f"  {d.get('explanation', '')}")
        if not any_fp:
            print("\n  none")

        print("\n" + "=" * 68)
        print("FALSE NEGATIVES  (in the labels, but missed)")
        print("=" * 68)
        any_fn = False
        for r in results:
            for e in r["fn"]:
                any_fn = True
                print(f"\n- {r['id']}  {r['filename']}:{e['line']}  "
                      f"expected category: {e['category']}")
                print(f"  case: {r['description']}")
        if not any_fn:
            print("\n  none")

    print("\nNote: the model is non-deterministic, so scores drift a little")
    print("between runs. Compare trends, not single-run decimals.\n")

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "tolerance": tolerance,
        "cases": len(results),
    }


def main():
    parser = argparse.ArgumentParser(description="Score the security review agent.")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="list every false positive and false negative")
    parser.add_argument("--tolerance", type=int, default=DEFAULT_TOLERANCE,
                        help=f"line-match tolerance (default {DEFAULT_TOLERANCE})")
    parser.add_argument("--case", help="run only cases whose id contains this string")
    parser.add_argument("--workers", type=int, default=4,
                        help="parallel review calls (default 4)")
    parser.add_argument("--json", dest="json_out",
                        help="write the summary to a JSON file (for before/after comparison)")
    parser.add_argument("--no-context", action="store_true",
                        help="review the diff alone, without full-file context "
                             "(the pre-Phase-3 behavior; use for A/B comparison)")
    args = parser.parse_args()

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set (put it in .env or the environment).")

    cases = load_cases(args.case)
    use_context = not args.no_context
    mode = "diff + full-file context" if use_context else "diff only (no context)"
    print(f"Running {len(cases)} case(s) against model '{review.MODEL}'  [{mode}]...")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(
            lambda c: score_case(c, args.tolerance, use_context), cases))

    summary = report(results, args.tolerance, args.verbose)

    if args.json_out:
        payload = {
            "model": review.MODEL,
            "full_file_context": use_context,
            "summary": summary,
            "cases": [
                {
                    "id": r["id"],
                    "expected": r["expected_count"],
                    "tp": len(r["tp"]), "fp": len(r["fp"]), "fn": len(r["fn"]),
                }
                for r in results
            ],
        }
        Path(args.json_out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote summary to {args.json_out}")


if __name__ == "__main__":
    main()
