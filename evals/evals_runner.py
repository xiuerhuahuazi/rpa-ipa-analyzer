#!/usr/bin/env python3
"""Evals runner for rpa-ipa-analyzer regression testing."""
import argparse, json, subprocess, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
BASELINE = SCRIPT_DIR / "golden" / "baseline_project"
GOLDEN_MANIFEST = BASELINE / "golden_manifest.json"
COUNTS_FILE = SKILL_DIR / "component_usage_counts.json"
EXTRACT_SCRIPT = SKILL_DIR / "scripts" / "extract_nodes.py"


def run_extract(force=True):
    result = subprocess.run(
        [sys.executable, str(EXTRACT_SCRIPT), "extract", str(BASELINE)] + (["--force"] if force else []),
        capture_output=True, text=True, timeout=120, cwd=str(SKILL_DIR)
    )
    return BASELINE / ".extracted_nodes" / "manifest.json"


def cmd_all():
    from assertions import assert_manifest_diff, assert_promotion_status
    print("=== EVAL: extract_golden_diff ===")
    mf = run_extract(force=True)
    new_m = json.loads(mf.read_text(encoding="utf-8"))
    golden_m = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))
    r1 = assert_manifest_diff(new_m, golden_m)
    print(f"  Score: {r1['score']}/{r1['max_score']} -- {'PASS' if r1['pass'] else 'FAIL'}")
    if r1["failures"]:
        for f in r1["failures"]:
            print(f"    - {f}")

    print("\n=== EVAL: promotion_mechanism ===")
    r2 = assert_promotion_status(str(COUNTS_FILE))
    print(f"  Score: {r2['score']}/{r2['max_score']} -- {'PASS' if r2['pass'] else 'FAIL'}")
    if r2["failures"]:
        for f in r2["failures"]:
            print(f"    - {f}")

    total = r1["score"] + r2["score"]
    max_total = r1["max_score"] + r2["max_score"]
    pct = (total / max_total) * 100 if max_total > 0 else 0
    threshold = 70
    print(f"\n=== TOTAL: {total}/{max_total} ({pct:.0f}%) -- {'PASS' if pct >= threshold else 'FAIL'} ===")


def cmd_regenerate_golden():
    print("Regenerating golden manifest...")
    run_extract(force=True)
    manifest = BASELINE / ".extracted_nodes" / "manifest.json"
    GOLDEN_MANIFEST.write_text(manifest.read_text(encoding="utf-8"))
    print(f"Golden manifest updated: {GOLDEN_MANIFEST}")


def main():
    parser = argparse.ArgumentParser(description="rpa-ipa-analyzer evals runner")
    parser.add_argument("--all", action="store_true", help="Run all eval cases")
    parser.add_argument("--regenerate-golden", action="store_true", help="Regenerate golden manifest")
    args = parser.parse_args()
    if args.regenerate_golden:
        cmd_regenerate_golden()
    elif args.all:
        cmd_all()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
