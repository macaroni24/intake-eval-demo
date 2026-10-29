"""Versioned eval set + CI gate.

A change ships only if accuracy is >= MIN_SCORE and not worse than
the last recorded baseline. Measure first; do not guess.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from intake.pipeline import run_intake  # noqa: E402

SET_PATH = Path(__file__).parent / "sets" / "v1.jsonl"
BASELINE_PATH = Path(__file__).parent / "baseline.json"
MIN_SCORE = 0.85


def load_cases() -> list[dict]:
    cases = []
    for line in SET_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(json.loads(line))
    return cases


def score_case(case: dict) -> tuple[bool, dict]:
    result = run_intake(case["text"])
    expect = case["expect"]
    ok = result.status == expect["status"]
    details = {"id": case["id"], "got_status": result.status, "ok": ok}

    if result.extracted and "category" in expect:
        cat_ok = result.extracted.category.value == expect["category"]
        ok = ok and cat_ok
        details["got_category"] = result.extracted.category.value
        details["category_ok"] = cat_ok
    if result.extracted and "language" in expect:
        lang_ok = result.extracted.language.value == expect["language"]
        ok = ok and lang_ok
        details["got_language"] = result.extracted.language.value
        details["language_ok"] = lang_ok

    details["ok"] = ok
    return ok, details


def main() -> int:
    cases = load_cases()
    rows = []
    passed = 0
    for case in cases:
        ok, details = score_case(case)
        rows.append(details)
        passed += int(ok)

    total = len(cases)
    accuracy = passed / total if total else 0.0
    report = {
        "eval_set": "v1",
        "passed": passed,
        "total": total,
        "accuracy": round(accuracy, 3),
        "min_score": MIN_SCORE,
        "cases": rows,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if accuracy < MIN_SCORE:
        print(f"GATE FAIL: accuracy {accuracy:.3f} < {MIN_SCORE}", file=sys.stderr)
        return 1

    if BASELINE_PATH.exists():
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        previous = float(baseline.get("accuracy", 0))
        if accuracy + 1e-9 < previous:
            print(
                f"GATE FAIL: accuracy {accuracy:.3f} is worse than baseline {previous:.3f}",
                file=sys.stderr,
            )
            return 1

    BASELINE_PATH.write_text(
        json.dumps({"eval_set": "v1", "accuracy": accuracy, "passed": passed, "total": total}, indent=2),
        encoding="utf-8",
    )
    print("GATE PASS", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
