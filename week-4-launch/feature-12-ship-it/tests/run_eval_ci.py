"""
CI eval quality gate for Feature 12: Ship It

This script is called by GitHub Actions after the smoke tests pass.
It loads the golden test set, runs the eval harness, and exits with
code 1 if the pass rate falls below 0.7 (70%).

Why a standalone script instead of a pytest test?
  - pytest collects tests in parallel and doesn't guarantee run order
  - This script is a single sequential gate: run → score → pass/fail
  - It mirrors how production teams run evals in CI: one job, one verdict

Usage:
    python week-4-launch/feature-12-ship-it/tests/run_eval_ci.py

Environment variables required:
    LLM_PROVIDER   — e.g. groq
    GROQ_API_KEY   — your Groq API key (set as a GitHub secret)
    GROQ_MODEL     — e.g. llama-3.3-70b-versatile
    VECTOR_DB_PATH — path for Chroma to store its data (e.g. /tmp/ci-chroma)
"""
import asyncio
import json
import sys
from pathlib import Path

# Add repo root so shared/ is importable.
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

CASES_PATH = Path(__file__).parent / "eval_cases_example.json"

PASS_RATE_THRESHOLD = 0.7


async def main() -> int:
    from shared.eval_harness import EvalCase, run_eval

    if not CASES_PATH.exists():
        print(f"[eval-ci] ERROR: eval cases file not found at {CASES_PATH}", flush=True)
        return 1

    raw = json.loads(CASES_PATH.read_text())
    cases = [EvalCase(**c) for c in raw]

    print(f"[eval-ci] Running {len(cases)} eval cases ...", flush=True)
    report = await run_eval(cases)

    print(f"[eval-ci] Results: {report.passed}/{report.total} passed  (pass_rate={report.pass_rate:.2f})", flush=True)

    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {result.case_id}", flush=True)
        if not result.passed and result.failure_reasons:
            for reason in result.failure_reasons:
                print(f"         - {reason}", flush=True)

    if report.pass_rate < PASS_RATE_THRESHOLD:
        print(
            f"\n[eval-ci] FAILED — pass rate {report.pass_rate:.2f} is below threshold {PASS_RATE_THRESHOLD:.2f}",
            flush=True,
        )
        return 1

    print(
        f"\n[eval-ci] PASSED — pass rate {report.pass_rate:.2f} meets threshold {PASS_RATE_THRESHOLD:.2f}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
