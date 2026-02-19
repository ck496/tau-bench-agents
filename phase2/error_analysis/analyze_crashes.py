#!/usr/bin/env python3
"""
analyze_crashes.py — Scan tau-bench trajectory JSONs for crashed runs.

Finds entries that crashed during Phase 1 execution (context window overflow,
API timeouts, code bugs) and produces summary tables. These entries have
`info.error` + `info.traceback` instead of the normal `info.task` structure,
and an empty `traj: []`.

How it works:
─────────────
1. DISCOVERY: Walks the trajectory directory and finds all .json files.
   Extracts model size (4B/8B/14B/32B), strategy (ACT/ReAct/FC), and
   domain (airline/retail) from the filename/directory name.

2. SCANNING: For each file, loads the JSON array and checks every entry:
   - Normal entry: has `info.task`, non-empty `traj` → skip
   - Crashed entry: has `info.error` → categorize the crash type

3. CRASH CATEGORIZATION: Reads the `info.error` string and classifies:
   - "ContextWindowExceeded" → context_window (extracts token counts)
   - "Timeout" / "APITimeout"  → api_timeout
   - Everything else           → other (logs the error text)

4. CONVERSATION LENGTH: For non-crashed entries, counts `traj` turns to
   find the longest conversations (potential near-limit cases).

5. OUTPUT: Prints markdown tables showing:
   - Per-file crash summary (total entries, crashes by type)
   - All context window crashes with exact token counts
   - All other crashes with error descriptions
   - Top 10 longest conversations (potential near-limit)
   - Cross-model comparison (crash rates by model size)

Usage:
    python analyze_crashes.py                          # scan all model sizes
    python analyze_crashes.py --model-size 14b         # only 14B files
    python analyze_crashes.py --model-size 4b          # only 4B files
    python analyze_crashes.py --output results.md      # save to file
"""

import argparse
import json
import re
import sys
from pathlib import Path


def parse_config_from_path(filepath: Path) -> dict:
    """
    Extract model_size, strategy, and domain from a trajectory file path.

    Handles two layouts:
      1. Subdirectory: .../act_airline_trials5_qwen_14b/act-Qwen3-14B-....json
      2. Standalone:   .../retail_act-Qwen3-4B-....json

    Returns dict with keys: model_size, strategy, domain, config_label
    """
    name = filepath.stem.lower()
    parent = filepath.parent.name.lower()

    # --- Model size ---
    model_size = None
    for pattern in [r"qwen3?-(\d+b)", r"qwen_(\d+b)"]:
        match = re.search(pattern, name + " " + parent, re.IGNORECASE)
        if match:
            model_size = match.group(1).upper()
            break
    if not model_size:
        model_size = "unknown"

    # --- Strategy ---
    combined = parent + " " + name
    if "tool-calling" in combined or "tool_calling" in combined:
        strategy = "FC"
    elif "react" in combined:
        strategy = "ReAct"
    elif "act" in combined:
        strategy = "ACT"
    else:
        strategy = "unknown"

    # --- Domain ---
    if "airline" in combined:
        domain = "airline"
    elif "retail" in combined:
        domain = "retail"
    else:
        domain = "unknown"

    config_label = f"{model_size}_{strategy}_{domain}"
    return {
        "model_size": model_size,
        "strategy": strategy,
        "domain": domain,
        "config_label": config_label,
    }


def classify_crash(error_msg: str) -> dict:
    """
    Classify a crash based on the info.error string.

    Returns dict with:
      - crash_type: "context_window" | "api_timeout" | "other"
      - tokens_used: int or None (only for context_window)
      - token_limit: int or None (only for context_window)
      - error_short: short description of the error
    """
    if "ContextWindowExceeded" in error_msg:
        # Extract token counts: "your request has XXXXX input tokens"
        tokens_match = re.search(r"your request has (\d+) input tokens", error_msg)
        limit_match = re.search(r"maximum context length is (\d+) tokens", error_msg)
        tokens_used = int(tokens_match.group(1)) if tokens_match else None
        token_limit = int(limit_match.group(1)) if limit_match else None
        return {
            "crash_type": "context_window",
            "tokens_used": tokens_used,
            "token_limit": token_limit,
            "error_short": f"Context window exceeded ({tokens_used}/{token_limit} tokens)"
            if tokens_used
            else "Context window exceeded",
        }
    elif "Timeout" in error_msg or "APITimeout" in error_msg:
        return {
            "crash_type": "api_timeout",
            "tokens_used": None,
            "token_limit": None,
            "error_short": "API request timed out",
        }
    else:
        # Take first line, truncate
        first_line = error_msg.split("\n")[0][:120]
        return {
            "crash_type": "other",
            "tokens_used": None,
            "token_limit": None,
            "error_short": first_line,
        }


def scan_file(filepath: Path, config: dict) -> dict:
    """
    Scan a single trajectory JSON file for crashed entries.

    Returns dict with:
      - config: the config dict
      - filepath: path to the file
      - total_entries: total number of entries in the file
      - normal_entries: entries with info.task
      - crashes: list of crash detail dicts
      - longest_trajs: top 10 longest conversations (turns, task_id, trial, reward)
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    crashes = []
    traj_lengths = []

    for entry in data:
        info = entry.get("info", {})
        task_id = entry.get("task_id", "?")
        trial = entry.get("trial", "?")
        reward = entry.get("reward", 0.0)
        traj = entry.get("traj", [])

        if "error" in info:
            crash_info = classify_crash(info["error"])
            crash_info["task_id"] = task_id
            crash_info["trial"] = trial
            crash_info["config_label"] = config["config_label"]
            crashes.append(crash_info)
        else:
            traj_lengths.append(
                {
                    "task_id": task_id,
                    "trial": trial,
                    "turns": len(traj),
                    "reward": reward,
                }
            )

    # Sort by turns descending, take top 10
    traj_lengths.sort(key=lambda x: x["turns"], reverse=True)

    return {
        "config": config,
        "filepath": filepath,
        "total_entries": len(data),
        "normal_entries": len(data) - len(crashes),
        "crashes": crashes,
        "longest_trajs": traj_lengths[:10],
    }


def discover_files(base_dir: Path, model_filter: str = None) -> list:
    """
    Find all trajectory JSON files. Returns list of (filepath, config) tuples.
    """
    results = []

    for json_path in sorted(base_dir.rglob("*.json")):
        # Skip non-trajectory files (results, summaries, etc.)
        if "results" in str(json_path) or "summary" in str(json_path):
            continue

        config = parse_config_from_path(json_path)

        # Apply model size filter if specified
        if model_filter and config["model_size"].lower() != model_filter.lower():
            continue

        results.append((json_path, config))

    return results


def print_summary(all_results: list, output_file=None):
    """Print markdown summary tables."""
    out = output_file or sys.stdout

    def p(text=""):
        print(text, file=out)

    # ── Header ──
    p("# Crash & Context Window Analysis")
    p()
    p(f"Scanned **{len(all_results)} trajectory files** across "
      f"{len(set(r['config']['model_size'] for r in all_results))} model sizes.")
    p()

    total_entries = sum(r["total_entries"] for r in all_results)
    total_crashes = sum(len(r["crashes"]) for r in all_results)
    ctx_crashes = sum(
        1 for r in all_results for c in r["crashes"] if c["crash_type"] == "context_window"
    )
    timeout_crashes = sum(
        1 for r in all_results for c in r["crashes"] if c["crash_type"] == "api_timeout"
    )
    other_crashes = sum(
        1 for r in all_results for c in r["crashes"] if c["crash_type"] == "other"
    )

    p(f"**Total entries:** {total_entries} | "
      f"**Total crashes:** {total_crashes} ({total_crashes/total_entries*100:.1f}%) | "
      f"Context window: {ctx_crashes} | Timeout: {timeout_crashes} | Other: {other_crashes}")
    p()

    # ── Table 1: Per-file summary ──
    p("## Per-File Summary")
    p()
    p("| Config | Total | Normal | Crashes | Ctx Window | Timeout | Other |")
    p("|--------|-------|--------|---------|------------|---------|-------|")

    for r in all_results:
        ctx = sum(1 for c in r["crashes"] if c["crash_type"] == "context_window")
        tout = sum(1 for c in r["crashes"] if c["crash_type"] == "api_timeout")
        oth = sum(1 for c in r["crashes"] if c["crash_type"] == "other")
        crash_total = len(r["crashes"])
        label = r["config"]["config_label"]
        p(f"| {label} | {r['total_entries']} | {r['normal_entries']} | "
          f"{crash_total} | {ctx} | {tout} | {oth} |")

    p()

    # ── Table 2: All context window crashes with token details ──
    ctx_entries = [
        c for r in all_results for c in r["crashes"] if c["crash_type"] == "context_window"
    ]

    if ctx_entries:
        p("## Context Window Exceeded — Detail")
        p()
        p("| Config | Task ID | Trial | Tokens Used | Token Limit | Over By |")
        p("|--------|---------|-------|-------------|-------------|---------|")

        for c in ctx_entries:
            over = (c["tokens_used"] - c["token_limit"]) if c["tokens_used"] and c["token_limit"] else "?"
            p(f"| {c['config_label']} | {c['task_id']} | {c['trial']} | "
              f"{c['tokens_used'] or '?':,} | {c['token_limit'] or '?':,} | "
              f"+{over:,} |" if isinstance(over, int) else
              f"| {c['config_label']} | {c['task_id']} | {c['trial']} | "
              f"{c['tokens_used'] or '?'} | {c['token_limit'] or '?'} | ? |")
        p()

    # ── Table 3: All other crashes ──
    other_entries = [
        c for r in all_results for c in r["crashes"] if c["crash_type"] != "context_window"
    ]

    if other_entries:
        p("## Other Crashes (Timeouts, Code Bugs)")
        p()
        p("| Config | Task ID | Trial | Type | Error |")
        p("|--------|---------|-------|------|-------|")

        for c in other_entries:
            p(f"| {c['config_label']} | {c['task_id']} | {c['trial']} | "
              f"{c['crash_type']} | {c['error_short']} |")
        p()

    # ── Table 4: Cross-model comparison ──
    model_sizes = sorted(set(r["config"]["model_size"] for r in all_results))
    if len(model_sizes) > 1:
        p("## Cross-Model Crash Rates")
        p()
        p("| Model Size | Total Entries | Total Crashes | Crash Rate | Ctx Window | Timeout | Other |")
        p("|------------|---------------|---------------|------------|------------|---------|-------|")

        for ms in model_sizes:
            ms_results = [r for r in all_results if r["config"]["model_size"] == ms]
            ms_total = sum(r["total_entries"] for r in ms_results)
            ms_crashes = sum(len(r["crashes"]) for r in ms_results)
            ms_ctx = sum(1 for r in ms_results for c in r["crashes"] if c["crash_type"] == "context_window")
            ms_tout = sum(1 for r in ms_results for c in r["crashes"] if c["crash_type"] == "api_timeout")
            ms_oth = sum(1 for r in ms_results for c in r["crashes"] if c["crash_type"] == "other")
            rate = f"{ms_crashes/ms_total*100:.1f}%" if ms_total > 0 else "N/A"
            p(f"| {ms} | {ms_total} | {ms_crashes} | {rate} | {ms_ctx} | {ms_tout} | {ms_oth} |")
        p()

    # ── Table 5: Longest conversations (potential near-limit) ──
    p("## Top 10 Longest Conversations (Potential Near-Limit)")
    p()
    p("These are the longest non-crashed conversations. Long conversations consume more")
    p("tokens and are more likely to degrade due to context pressure, even without crashing.")
    p()
    p("| Config | Task ID | Trial | Turns | Reward |")
    p("|--------|---------|-------|-------|--------|")

    all_long = []
    for r in all_results:
        for t in r["longest_trajs"]:
            t["config_label"] = r["config"]["config_label"]
            all_long.append(t)

    all_long.sort(key=lambda x: x["turns"], reverse=True)
    for t in all_long[:10]:
        status = "PASS" if t["reward"] == 1.0 else "FAIL"
        p(f"| {t['config_label']} | {t['task_id']} | {t['trial']} | "
          f"{t['turns']} | {status} |")
    p()


def save_json(all_results: list, json_path: str):
    """
    Save structured crash analysis results to JSON.

    Produces a machine-readable version of the same data shown in the
    markdown tables: per-file summaries, individual crash details,
    cross-model comparison, and longest conversations.
    """
    output = {
        "totals": {
            "total_entries": sum(r["total_entries"] for r in all_results),
            "total_crashes": sum(len(r["crashes"]) for r in all_results),
            "context_window": sum(
                1 for r in all_results for c in r["crashes"] if c["crash_type"] == "context_window"
            ),
            "api_timeout": sum(
                1 for r in all_results for c in r["crashes"] if c["crash_type"] == "api_timeout"
            ),
            "other": sum(
                1 for r in all_results for c in r["crashes"] if c["crash_type"] == "other"
            ),
        },
        "per_file": [],
        "crashes": [],
        "cross_model": {},
        "longest_conversations": [],
    }

    total = output["totals"]["total_entries"]
    output["totals"]["crash_rate_pct"] = round(
        output["totals"]["total_crashes"] / total * 100, 2
    ) if total > 0 else 0.0

    # Per-file summaries
    for r in all_results:
        ctx = sum(1 for c in r["crashes"] if c["crash_type"] == "context_window")
        tout = sum(1 for c in r["crashes"] if c["crash_type"] == "api_timeout")
        oth = sum(1 for c in r["crashes"] if c["crash_type"] == "other")
        output["per_file"].append({
            "config": r["config"]["config_label"],
            "model_size": r["config"]["model_size"],
            "strategy": r["config"]["strategy"],
            "domain": r["config"]["domain"],
            "total_entries": r["total_entries"],
            "normal_entries": r["normal_entries"],
            "total_crashes": len(r["crashes"]),
            "context_window": ctx,
            "api_timeout": tout,
            "other": oth,
        })

    # All individual crashes
    for r in all_results:
        for c in r["crashes"]:
            entry = {
                "config": c["config_label"],
                "task_id": c["task_id"],
                "trial": c["trial"],
                "crash_type": c["crash_type"],
                "error_short": c["error_short"],
            }
            if c["tokens_used"] is not None:
                entry["tokens_used"] = c["tokens_used"]
                entry["token_limit"] = c["token_limit"]
                entry["over_by"] = c["tokens_used"] - c["token_limit"]
            output["crashes"].append(entry)

    # Cross-model comparison
    model_sizes = sorted(set(r["config"]["model_size"] for r in all_results))
    for ms in model_sizes:
        ms_results = [r for r in all_results if r["config"]["model_size"] == ms]
        ms_total = sum(r["total_entries"] for r in ms_results)
        ms_crashes = sum(len(r["crashes"]) for r in ms_results)
        output["cross_model"][ms] = {
            "total_entries": ms_total,
            "total_crashes": ms_crashes,
            "crash_rate_pct": round(ms_crashes / ms_total * 100, 2) if ms_total > 0 else 0.0,
            "context_window": sum(
                1 for r in ms_results for c in r["crashes"] if c["crash_type"] == "context_window"
            ),
            "api_timeout": sum(
                1 for r in ms_results for c in r["crashes"] if c["crash_type"] == "api_timeout"
            ),
            "other": sum(
                1 for r in ms_results for c in r["crashes"] if c["crash_type"] == "other"
            ),
        }

    # Top 10 longest conversations
    all_long = []
    for r in all_results:
        for t in r["longest_trajs"]:
            all_long.append({
                "config": r["config"]["config_label"],
                "task_id": t["task_id"],
                "trial": t["trial"],
                "turns": t["turns"],
                "reward": t["reward"],
            })
    all_long.sort(key=lambda x: x["turns"], reverse=True)
    output["longest_conversations"] = all_long[:10]

    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze crashed runs in tau-bench trajectory files."
    )
    parser.add_argument(
        "--trajectory-dir",
        type=str,
        default=None,
        help="Path to trajectory directory. Default: auto-detect from script location.",
    )
    parser.add_argument(
        "--model-size",
        type=str,
        default=None,
        choices=["4b", "8b", "14b", "32b"],
        help="Filter to a specific model size (e.g., 14b). Default: all sizes.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Save markdown output to a file instead of printing to stdout.",
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default=None,
        help="Save structured results to a JSON file.",
    )
    args = parser.parse_args()

    # Auto-detect trajectory directory
    if args.trajectory_dir:
        traj_dir = Path(args.trajectory_dir)
    else:
        script_dir = Path(__file__).resolve().parent
        # Try: phase2/error_analysis -> phase1/JSON_trajectories
        candidate = script_dir.parent.parent / "phase1" / "JSON_trajectories"
        if not candidate.exists():
            # Try with trailing space (known issue)
            candidate = script_dir.parent.parent / "phase1" / "JSON_trajectories "
        traj_dir = candidate

    if not traj_dir.exists():
        print(f"ERROR: Trajectory directory not found: {traj_dir}")
        sys.exit(1)

    print(f"Scanning: {traj_dir}")
    if args.model_size:
        print(f"Filter: {args.model_size.upper()} only")

    # Discover and scan
    files = discover_files(traj_dir, args.model_size)
    print(f"Found {len(files)} trajectory file(s)")

    if not files:
        print("No files found. Check --trajectory-dir path.")
        sys.exit(1)

    all_results = []
    for filepath, config in files:
        print(f"  Scanning {config['config_label']}: {filepath.name}")
        result = scan_file(filepath, config)
        all_results.append(result)

    print()

    # Markdown output
    if args.output:
        with open(args.output, "w") as f:
            print_summary(all_results, output_file=f)
        print(f"Saved markdown to {args.output}")
    else:
        print_summary(all_results)

    # JSON output
    if args.json_output:
        save_json(all_results, args.json_output)
        print(f"Saved JSON to {args.json_output}")


if __name__ == "__main__":
    main()
