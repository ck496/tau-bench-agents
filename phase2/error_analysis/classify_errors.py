#!/usr/bin/env python3
"""
tau-bench Phase 2 — Error Classification Script

Classifies failure cases from Qwen3 trajectory JSONs by sending each one
to a strong LLM (Claude Sonnet or GPT-4o) and asking it to label the error.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python classify_errors.py --provider anthropic

    # or with OpenAI:
    export OPENAI_API_KEY=sk-...
    python classify_errors.py --provider openai

    # see all options:
    python classify_errors.py --help
"""

import argparse
import json
import os
import random
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

# Set to True via --debug flag. Controls [DEBUG] print statements.
DEBUG = False

# ═══════════════════════════════════════════════════════════════════════════════
# ERROR TAXONOMY
# These are OUR categories (not tau-bench paper's). Edit here to change them.
# The LLM classifier picks exactly one per failure case.
# ═══════════════════════════════════════════════════════════════════════════════

ERROR_TAXONOMY = {
    "wrong_tool": (
        "Agent called the wrong tool entirely "
        "(e.g., cancel_reservation when it should have called update_reservation_flights)"
    ),
    "wrong_arguments": (
        "Correct tool but wrong parameters "
        "(e.g., wrong reservation_id, wrong payment_method, wrong flight number, wrong date)"
    ),
    "policy_violation": (
        "Agent violated a domain rule "
        "(e.g., modifying basic economy, cancelling without insurance, giving unauthorized refund, "
        "skipping user authentication)"
    ),
    "incomplete_execution": (
        "Agent completed some but not all required actions "
        "(e.g., changed flights but forgot to update baggage or passengers)"
    ),
    "premature_escalation": (
        "Agent transferred to a human agent when it could have handled the request "
        "with available tools"
    ),
    "information_error": (
        "Agent gave the user incorrect information (wrong price, wrong policy detail, "
        "wrong flight status) which affected the conversation outcome"
    ),
    "reasoning_failure": (
        "Agent misunderstood user intent or made a wrong plan despite having "
        "correct information available from tools and conversation"
    ),
    "user_simulator_error": (
        "The user simulator gave ambiguous, contradictory, or hallucinated instructions "
        "that caused the agent to fail through no fault of its own"
    ),
    "context_or_format_error": (
        "Conversation cut short (context window overflow), malformed JSON action, "
        "or other infrastructure/parsing failure"
    ),
}

# Default models per provider — good balance of quality and cost for classification
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5-20250929",
    "openai": "gpt-4o",
}


# ═══════════════════════════════════════════════════════════════════════════════
# FILE DISCOVERY
# Our trajectory JSONs live in phase_2/JSON_trajectories/ organized in
# subdirectories named like: {strategy}_{domain}_trials5_qwen_{size}b/
#   e.g., react_airline_trials5_qwen_14b/
#         tool-calling_retail_trials5_qwen_14b/
# Each subdirectory has one JSON file with all trials for that configuration.
# This function scans that directory and finds all 6 files for a given model
# size (3 strategies x 2 domains).
# ═══════════════════════════════════════════════════════════════════════════════

def discover_files(base_dir, model_size="14b"):
    """Find all trajectory files for a model size. Returns [(path, config_name), ...]"""
    if DEBUG: print(f"[DEBUG] discover_files(base_dir={base_dir}, model_size={model_size})")
    base = Path(base_dir)
    if not base.exists():
        # Our JSON_trajectories dir accidentally has a trailing space in its name.
        # This handles that edge case so teammates don't get confused.
        alt = Path(str(base) + " ")
        if alt.exists():
            base = alt
        else:
            print(f"ERROR: Directory not found: {base_dir}")
            return []

    # Maps directory prefix -> human-readable label for output filenames
    # e.g., "tool-calling" dirs get labeled "FC" in our results
    strategies = {
        "act": "ACT",
        "react": "ReAct",
        "tool-calling": "FC",
    }
    domains = ["airline", "retail"]
    files = []

    for strategy_key, strategy_label in strategies.items():
        for domain in domains:
            # config_name becomes the output filename, e.g., "14b_ReAct_airline.json"
            config_name = f"{model_size}_{strategy_label}_{domain}"

            # Scan subdirectories for a match like "react_airline_trials5_qwen_14b"
            found = False
            for subdir in sorted(base.iterdir()):
                if not subdir.is_dir():
                    continue
                name = subdir.name.lower()
                # startswith() prevents "act_" from matching "react_" directories
                if (name.startswith(f"{strategy_key}_{domain}_")
                        and model_size.lower() in name):
                    # Each subdirectory should have exactly one JSON file inside
                    jsons = sorted(subdir.glob("*.json"))
                    if jsons:
                        files.append((jsons[0], config_name))
                        found = True
                        break

            if not found:
                print(f"  WARNING: No file found for {config_name}")

    if DEBUG: print(f"[DEBUG] discover_files -> found {len(files)} files")
    return files


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING & SAMPLING
#
# Each trajectory JSON is a flat array of objects, one per (task_id, trial).
# A typical file has 50 tasks x 5 trials = 250 entries. Each entry looks like:
#   {"task_id": 4, "reward": 0.0, "info": {...}, "traj": [...], "trial": 0}
#
# We only care about failures (reward=0.0), and we deduplicate by task_id
# so we classify each unique failure pattern once, not 5 times.
# ═══════════════════════════════════════════════════════════════════════════════

def load_and_sample(filepath, sample_size=50, seed=42):
    """Load trajectory JSON, return sampled unique failure cases."""
    if DEBUG: print(f"[DEBUG] load_and_sample(filepath={Path(filepath).name}, sample_size={sample_size}, seed={seed})")
    with open(filepath) as f:
        data = json.load(f)

    # Filter to failed tasks only (reward=0.0 means the agent got it wrong).
    # Also skip entries that crashed mid-run — these have info.error/traceback
    # instead of info.task, and an empty traj. Nothing to classify.
    failures = [
        entry for entry in data
        if entry.get("reward", 1.0) == 0.0
        and "task" in entry.get("info", {})
        and entry.get("traj")
    ]

    # Deduplicate: keep one entry per task_id (lowest trial number).
    # Why? A task that fails all 5 trials is ONE failure pattern, not five.
    # We keep trial 0 because it's deterministic (temperature=0.0).
    seen = {}
    for entry in failures:
        tid = entry["task_id"]
        if tid not in seen or entry.get("trial", 0) < seen[tid].get("trial", 0):
            seen[tid] = entry
    unique = sorted(seen.values(), key=lambda x: x["task_id"])

    # Deterministic sample (fixed seed = same sample on re-run = safe to resume)
    random.seed(seed)
    if DEBUG: print(f"[DEBUG] load_and_sample -> {len(data)} total entries, {len(failures)} failures, {len(unique)} unique task_ids")
    if len(unique) <= sample_size:
        return unique, len(data)
    return random.sample(unique, sample_size), len(data)


# ═══════════════════════════════════════════════════════════════════════════════
# TRAJECTORY PARSING
#
# Each trajectory entry has a "traj" array — the full conversation between
# the agent and user simulator. The structure is:
#   traj[0]  = system message (contains domain policy + tool JSON schemas)
#   traj[1]  = first user message
#   traj[2]  = first assistant response (may contain Action: {...} or tool_calls)
#   traj[3]  = API output or next user message
#   ... and so on until the conversation ends
#
# The "info" object has ground truth: what the agent SHOULD have done.
#   info.task.actions    = list of correct tool calls with exact arguments
#   info.task.instruction = what the simulated user was trying to accomplish
#   info.reward_info     = how the reward was computed (action match + output match)
# ═══════════════════════════════════════════════════════════════════════════════

def extract_policy(system_content):
    """Pull just the policy rules from the system prompt (skip tool JSON schemas).

    The system prompt is huge (~3000+ tokens) because it includes full JSON
    schemas for every tool. We only send the policy rules section to the
    classifier to save tokens and keep the prompt focused.
    """
    if DEBUG: print(f"[DEBUG] extract_policy(system_content_len={len(system_content)})")
    for marker in ["#Available tools", "# Available tools", "#Available Tools"]:
        if marker in system_content:
            return system_content.split(marker)[0].strip()
    return system_content[:3000]  # fallback: first 3000 chars


def extract_agent_actions(traj):
    """Parse what tools the agent actually called from the trajectory.

    Handles two formats:
      - ACT/ReAct: actions in content as 'Action:\\n{"name": ..., "arguments": ...}'
      - FC (tool-calling): actions in the 'tool_calls' field
    """
    if DEBUG: print(f"[DEBUG] extract_agent_actions(traj_len={len(traj)})")
    actions = []
    for msg in traj:
        if msg.get("role") != "assistant":
            continue

        # FC format: structured tool_calls array
        tool_calls = msg.get("tool_calls")
        if tool_calls:
            for tc in tool_calls:
                fn = tc.get("function", {})
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    args = fn.get("arguments", {})
                name = fn.get("name", "unknown")
                if name not in ("respond", "unknown"):
                    actions.append({"name": name, "arguments": args})
            continue

        # ACT/ReAct format: Action: {...} in content
        content = msg.get("content", "") or ""
        match = re.search(r'Action:\s*(\{.*\})', content, re.DOTALL)
        if match:
            try:
                action = json.loads(match.group(1))
                if action.get("name") not in ("respond", None):
                    actions.append(action)
            except json.JSONDecodeError:
                pass

    if DEBUG: print(f"[DEBUG] extract_agent_actions -> found {len(actions)} actions")
    return actions


def format_conversation(traj_messages, max_api_output_len=500):
    """Format conversation turns for the classifier prompt.

    Strips user simulator <think> tags (that's the simulator's internal reasoning,
    not relevant to diagnosing agent errors). Keeps agent <think> tags since those
    show agent reasoning failures. Truncates long API outputs to save tokens.
    """
    if DEBUG: print(f"[DEBUG] format_conversation(num_messages={len(traj_messages)}, max_api_output_len={max_api_output_len})")
    lines = []
    for msg in traj_messages:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "") or ""

        # Strip simulator reasoning from user messages (noise for classification)
        if msg.get("role") == "user" and "<think>" in content:
            content = re.sub(r'<think>.*?</think>\s*',
                             '', content, flags=re.DOTALL)

        # Truncate verbose API outputs (tool results can be huge JSON blobs)
        if msg.get("role") == "user" and content.startswith("API output:"):
            if len(content) > max_api_output_len:
                content = content[:max_api_output_len] + " ... [truncated]"

        # For FC format: append tool_calls info to content
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            tc_lines = []
            for tc in msg["tool_calls"]:
                fn = tc.get("function", {})
                tc_lines.append(
                    f"  [Tool Call] {fn.get('name')}({fn.get('arguments', '{}')})")
            content = ((content or "") + "\n" + "\n".join(tc_lines)).strip()

        if content.strip():
            lines.append(f"[{role}]: {content.strip()}")

    return "\n\n".join(lines)


def format_ground_truth(actions):
    """Format expected actions as readable numbered list."""
    if DEBUG: print(f"[DEBUG] format_ground_truth(num_actions={len(actions) if actions else 0})")
    if not actions:
        return (
            "No actions required — the agent should have refused the request "
            "or correctly identified it as out of scope."
        )
    lines = []
    for i, action in enumerate(actions, 1):
        name = action.get("name", "unknown")
        kwargs = action.get("kwargs", action.get("arguments", {}))
        lines.append(f"{i}. {name}({json.dumps(kwargs, indent=2)})")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT CONSTRUCTION
# This is the core of the script. For each failure case, we build a prompt
# that gives the LLM everything it needs to diagnose the error:
#   1. What the user wanted (from info.task.instruction)
#   2. What the agent should have done (from info.task.actions — the ground truth)
#   3. The domain rules (from the system prompt in the trajectory)
#   4. What the agent actually did (the conversation from traj)
#   5. Our error taxonomy (so it picks a consistent category)
# ═══════════════════════════════════════════════════════════════════════════════

def build_prompt(failure):
    """Build the full classification prompt for one failure case.

    The key insight: we pass BOTH the ground truth and the actual conversation.
    Without ground truth, the classifier would have to guess what "correct"
    looks like and would hallucinate plausible-sounding errors.
    """
    if DEBUG: print(f"[DEBUG] build_prompt(task_id={failure.get('task_id')}, trial={failure.get('trial', 0)})")
    traj = failure.get("traj", [])
    task = failure.get("info", {}).get("task", {})

    # Extract policy from system prompt (first traj entry)
    policy = "No policy available"
    if traj and traj[0].get("role") == "system":
        policy = extract_policy(traj[0].get("content", ""))

    gt_text = format_ground_truth(task.get("actions", []))

    # Conversation = everything after system prompt
    conv_messages = [m for m in traj if m.get("role") != "system"]
    conv_text = format_conversation(conv_messages)

    # Build taxonomy reference for the classifier
    taxonomy_lines = []
    for cat_id, description in ERROR_TAXONOMY.items():
        taxonomy_lines.append(f"  - {cat_id}: {description}")
    taxonomy_text = "\n".join(taxonomy_lines)

    prompt = f"""You are an expert evaluator analyzing a FAILED AI agent interaction from the tau-bench benchmark.

The agent was supposed to help a simulated user with a customer service task but FAILED (reward = 0).
Your job: figure out WHY it failed by comparing what the agent did vs what it should have done.

## User's Goal
{task.get("instruction", "No instruction available")}

## Expected Solution (Ground Truth)
These are the correct actions the agent should have taken:
{gt_text}

## Domain Policy (Rules the Agent Must Follow)
{policy}

## Actual Conversation
{conv_text}

## Error Taxonomy
Classify this failure into EXACTLY ONE of these categories:
{taxonomy_text}

Respond with ONLY valid JSON, nothing else:
{{"primary_category": "<category_id>", "sub_category": "<brief specific sub-type>", "explanation": "<1-2 sentence explanation>"}}"""

    return prompt


# ═══════════════════════════════════════════════════════════════════════════════
# LLM API
# One API call per failure case. Supports Anthropic (Claude) and OpenAI (GPT).
# Cost: ~2-5K tokens input + ~100 tokens output per call.
# At 300 calls total: ~$5-10 with Claude Sonnet, ~$5-12 with GPT-4o.
# ═══════════════════════════════════════════════════════════════════════════════

def create_client(provider):
    """Initialize API client. Reads key from environment variable."""
    if DEBUG: print(f"[DEBUG] create_client(provider={provider})")
    if provider == "anthropic":
        try:
            from anthropic import Anthropic
        except ImportError:
            sys.exit("ERROR: pip install anthropic")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("ERROR: Set ANTHROPIC_API_KEY environment variable")
        return Anthropic()

    elif provider == "openai":
        try:
            from openai import OpenAI
        except ImportError:
            sys.exit("ERROR: pip install openai")
        if not os.environ.get("OPENAI_API_KEY"):
            sys.exit("ERROR: Set OPENAI_API_KEY environment variable")
        return OpenAI()

    else:
        sys.exit(
            f"ERROR: Unknown provider '{provider}'. Use 'anthropic' or 'openai'.")


def call_llm(client, provider, model, prompt):
    """Single LLM API call. Returns raw response text."""
    if DEBUG: print(f"[DEBUG] call_llm(provider={provider}, model={model}, prompt_len={len(prompt)})")
    if provider == "anthropic":
        response = client.messages.create(
            model=model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    elif provider == "openai":
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You classify AI agent failures. Respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content


def parse_response(text):
    """Extract classification JSON from LLM response.

    Tries multiple strategies because LLMs sometimes wrap JSON in markdown code blocks.
    """
    if DEBUG: print(f"[DEBUG] parse_response(text_len={len(text)}, preview={text[:80]!r})")
    text = text.strip()

    # Strategy 1: direct JSON parse
    try:
        result = json.loads(text)
        if "primary_category" in result:
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: extract from ```json ... ``` code block
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: find any JSON object containing primary_category
    match = re.search(r'\{[^{}]*"primary_category"[^{}]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Give up — return a parse error (still counts in results, easy to spot)
    return {
        "primary_category": "parse_error",
        "sub_category": "none",
        "explanation": f"Could not parse LLM response: {text[:200]}",
    }


def classify_one(client, provider, model, failure, delay=0.5):
    """Classify a single failure case. Retries once on API error."""
    if DEBUG: print(f"[DEBUG] classify_one(provider={provider}, model={model}, task_id={failure.get('task_id')}, delay={delay})")
    prompt = build_prompt(failure)

    for attempt in range(2):
        try:
            response_text = call_llm(client, provider, model, prompt)
            result = parse_response(response_text)

            # Validate category is in our taxonomy
            valid = set(ERROR_TAXONOMY.keys()) | {"parse_error", "api_error"}
            if result.get("primary_category") not in valid:
                result["primary_category"] = "other"

            time.sleep(delay)
            return result

        except Exception as e:
            if attempt == 0:
                print(f"(retry) ", end="", flush=True)
                time.sleep(2)
            else:
                return {
                    "primary_category": "api_error",
                    "sub_category": "none",
                    "explanation": f"API failed after retry: {str(e)[:200]}",
                }


# ═══════════════════════════════════════════════════════════════════════════════
# PROCESSING & AGGREGATION
# Runs classification on each file and aggregates results.
# ═══════════════════════════════════════════════════════════════════════════════

def compute_summary(classifications):
    """Count errors per category with percentages."""
    if DEBUG: print(f"[DEBUG] compute_summary(num_classifications={len(classifications)})")
    counts = defaultdict(int)
    for c in classifications:
        cat = c["classification"]["primary_category"]
        counts[cat] += 1

    total = len(classifications)
    return {
        cat: {
            "count": count,
            "percentage": round(100 * count / total, 1) if total > 0 else 0,
        }
        for cat, count in sorted(counts.items(), key=lambda x: -x[1])
    }


def process_file(filepath, config_name, client, provider, model,
                 sample_size, output_dir, delay, force, dry_run):
    """Full pipeline for one trajectory file: load -> sample -> classify -> save.

    Supports resuming: if a .partial.json exists from a crashed run, picks up
    where it left off (same seed = same sample = safe to resume).
    """
    if DEBUG: print(f"[DEBUG] process_file(config={config_name}, file={filepath.name}, provider={provider}, model={model}, sample_size={sample_size}, force={force}, dry_run={dry_run})")
    result_path = output_dir / f"{config_name}.json"
    partial_path = output_dir / f"{config_name}.partial.json"

    # Skip if already completed
    if result_path.exists() and not force:
        print(
            f"\n-- Skipping {config_name} (already done, use --force to redo)")
        with open(result_path) as f:
            return json.load(f)

    print(f"\n{'='*60}")
    print(f"Config: {config_name}")
    print(f"File:   {filepath.name}")

    # Load and sample
    failures, total_entries = load_and_sample(filepath, sample_size)
    total_tasks = len(set(e["task_id"]
                      for e in json.loads(open(filepath).read())))

    print(f"  {total_tasks} tasks total, {len(failures)} unique failures sampled")

    if not failures:
        print("  No failures found, skipping")
        return None

    # Dry run: print one prompt and exit
    if dry_run:
        print("\n--- DRY RUN: Prompt for first failure case ---\n")
        print(build_prompt(failures[0]))
        print("\n--- End of dry run ---")
        sys.exit(0)

    # Check for partial results from a previous interrupted run
    classifications = []
    start_idx = 0
    if partial_path.exists() and not force:
        with open(partial_path) as f:
            partial = json.load(f)
        classifications = partial.get("classifications", [])
        start_idx = len(classifications)
        print(f"  Resuming from classification {start_idx}/{len(failures)}")

    # Classify each failure
    for i in range(start_idx, len(failures)):
        failure = failures[i]
        print(
            f"  [{i+1}/{len(failures)}] task_id={failure['task_id']} ... ", end="", flush=True)

        # Safety net: skip entries missing info.task (crashed runs)
        task = failure.get("info", {}).get("task")
        if not task:
            print(f"-> SKIPPED (no info.task — crashed run)")
            continue

        cls = classify_one(client, provider, model, failure, delay)

        classifications.append({
            "task_id": failure["task_id"],
            "trial": failure.get("trial", 0),
            "instruction": task.get("instruction", ""),
            "ground_truth_actions": task.get("actions", []),
            "agent_actions": extract_agent_actions(failure.get("traj", [])),
            "classification": cls,
        })

        print(f"-> {cls['primary_category']}")

        # Save progress after each call (crash-safe)
        with open(partial_path, "w") as f:
            json.dump({"classifications": classifications}, f)

    # Build final result
    summary = compute_summary(classifications)
    result = {
        "config": config_name,
        "file": str(filepath),
        "stats": {
            "total_tasks": total_tasks,
            "total_failures_in_file": sum(
                1 for e in json.loads(open(filepath).read()) if e.get("reward", 1) == 0.0
            ),
            "unique_failures_sampled": len(failures),
        },
        "summary": summary,
        "classifications": classifications,
    }

    # Save final and clean up partial
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)
    if partial_path.exists():
        partial_path.unlink()

    print(f"  Saved: {result_path}")
    return result


def aggregate_all(all_results):
    """Combine summaries across all configs into one structure for plotting."""
    if DEBUG: print(f"[DEBUG] aggregate_all(num_configs={len(all_results)})")
    combined = {}
    for config_name, result in all_results.items():
        if result and "summary" in result:
            combined[config_name] = result["summary"]
    return combined


def extract_examples(all_results, n_per_category=5):
    """Pull up to N representative failure examples per error category.

    These go into the Phase 2 submission as the required "5 representative
    failure trajectory JSONs per error category."
    """
    if DEBUG: print(f"[DEBUG] extract_examples(num_configs={len(all_results)}, n_per_category={n_per_category})")
    by_category = defaultdict(list)

    for config_name, result in all_results.items():
        if not result:
            continue
        for cls in result.get("classifications", []):
            cat = cls["classification"]["primary_category"]
            by_category[cat].append({
                "config": config_name,
                "task_id": cls["task_id"],
                "instruction": cls["instruction"],
                "ground_truth_actions": cls["ground_truth_actions"],
                "agent_actions": cls["agent_actions"],
                "classification": cls["classification"],
            })

    # Pick the N with shortest explanations (usually the clearest examples)
    examples = {}
    for cat, items in by_category.items():
        items.sort(key=lambda x: len(
            x["classification"].get("explanation", "")))
        examples[cat] = items[:n_per_category]

    if DEBUG: print(f"[DEBUG] extract_examples -> {len(examples)} categories: {{{', '.join(f'{k}: {len(v)}' for k, v in examples.items())}}}")
    return examples


# ═══════════════════════════════════════════════════════════════════════════════
# VISUALIZATION
# Generates matplotlib plots for the Phase 2 report.
# ═══════════════════════════════════════════════════════════════════════════════

def generate_plots(combined_summary, plot_dir):
    """Generate 3 plots: by strategy, by domain, and full breakdown.

    combined_summary = {config_name: {category: {count, percentage}, ...}, ...}
    """
    if DEBUG: print(f"[DEBUG] generate_plots(num_configs={len(combined_summary)}, plot_dir={plot_dir})")
    try:
        import matplotlib
        matplotlib.use("Agg")  # no display needed (works on servers)
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not installed — skipping plots (pip install matplotlib)")
        return

    plot_dir = Path(plot_dir)
    plot_dir.mkdir(parents=True, exist_ok=True)

    categories = list(ERROR_TAXONOMY.keys())
    cat_labels = [c.replace("_", " ").title() for c in categories]

    # Organize data by strategy and domain
    strategy_data = defaultdict(lambda: defaultdict(list))
    domain_data = defaultdict(lambda: defaultdict(list))
    config_pcts = {}

    for config_name, summary in combined_summary.items():
        # Parse config: "14b_ReAct_airline" -> strategy=ReAct, domain=airline
        parts = config_name.split("_", 2)
        if len(parts) < 3:
            continue
        strategy, domain = parts[1], parts[2]

        pcts = {}
        for cat in categories:
            pct = summary.get(cat, {}).get("percentage", 0)
            strategy_data[strategy][cat].append(pct)
            domain_data[domain][cat].append(pct)
            pcts[cat] = pct
        config_pcts[config_name] = pcts

    # ── Plot 1: Error distribution by strategy ──
    fig, ax = plt.subplots(figsize=(14, 6))
    strategies = sorted(strategy_data.keys())
    n_strats = len(strategies)
    width = 0.8 / max(n_strats, 1)
    x = list(range(len(categories)))
    colors = ["#2196F3", "#FF9800", "#4CAF50", "#E91E63"]

    for i, strategy in enumerate(strategies):
        vals = []
        for cat in categories:
            pts = strategy_data[strategy].get(cat, [0])
            vals.append(sum(pts) / max(len(pts), 1))
        offset = (i - n_strats / 2 + 0.5) * width
        ax.bar([xi + offset for xi in x], vals, width,
               label=strategy, color=colors[i % len(colors)])

    ax.set_xticks(x)
    ax.set_xticklabels(cat_labels, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Percentage of Failures (%)")
    ax.set_title("Error Distribution by Strategy (Qwen3-14B)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(plot_dir / "errors_by_strategy.png",
                dpi=150, bbox_inches="tight")
    plt.close()

    # ── Plot 2: Error distribution by domain ──
    fig, ax = plt.subplots(figsize=(14, 6))
    domains = sorted(domain_data.keys())
    n_doms = len(domains)
    width = 0.8 / max(n_doms, 1)
    colors_dom = ["#E91E63", "#9C27B0", "#009688"]

    for i, domain in enumerate(domains):
        vals = []
        for cat in categories:
            pts = domain_data[domain].get(cat, [0])
            vals.append(sum(pts) / max(len(pts), 1))
        offset = (i - n_doms / 2 + 0.5) * width
        ax.bar([xi + offset for xi in x], vals, width,
               label=domain.title(), color=colors_dom[i % len(colors_dom)])

    ax.set_xticks(x)
    ax.set_xticklabels(cat_labels, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Percentage of Failures (%)")
    ax.set_title("Error Distribution by Domain (Qwen3-14B)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(plot_dir / "errors_by_domain.png",
                dpi=150, bbox_inches="tight")
    plt.close()

    # ── Plot 3: Stacked bar — full breakdown per config ──
    fig, ax = plt.subplots(figsize=(14, 7))
    configs = sorted(config_pcts.keys())
    bottom = [0.0] * len(configs)

    cmap = plt.cm.get_cmap("Set3", len(categories))
    for j, cat in enumerate(categories):
        vals = [config_pcts[c].get(cat, 0) for c in configs]
        ax.bar(range(len(configs)), vals, bottom=bottom,
               label=cat_labels[j], color=cmap(j))
        bottom = [b + v for b, v in zip(bottom, vals)]

    config_labels = [c.replace(f"{c.split('_')[0]}_", "").replace("_", "\n")
                     for c in configs]
    ax.set_xticks(range(len(configs)))
    ax.set_xticklabels(config_labels, fontsize=9)
    ax.set_ylabel("Percentage (%)")
    ax.set_title("Error Breakdown by Configuration (Qwen3-14B)")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=8)
    plt.tight_layout()
    fig.savefig(plot_dir / "error_breakdown_all.png",
                dpi=150, bbox_inches="tight")
    plt.close()

    print(f"  Saved 3 plots to {plot_dir}/")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI & MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="Classify tau-bench failures using LLM API calls",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python classify_errors.py --provider anthropic
  python classify_errors.py --provider openai --model gpt-4o
  python classify_errors.py --provider anthropic --model-size 32b --sample-size 60
  python classify_errors.py --provider anthropic --dry-run
        """,
    )
    parser.add_argument(
        "--provider", required=True, choices=["anthropic", "openai"],
        help="API provider (anthropic or openai)",
    )
    parser.add_argument(
        "--model", default=None,
        help="Model name (default: claude-sonnet-4-5-20250929 / gpt-4o)",
    )
    parser.add_argument(
        "--model-size", default="14b",
        help="Qwen3 model size to analyze (default: 14b)",
    )
    parser.add_argument(
        "--sample-size", type=int, default=50,
        help="Max unique failures to sample per trajectory file (default: 50)",
    )
    parser.add_argument(
        "--trajectory-dir", default=None,
        help="Path to JSON_trajectories directory (auto-detected if omitted)",
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory for results (default: results/ next to this script)",
    )
    parser.add_argument(
        "--delay", type=float, default=0.5,
        help="Seconds between API calls for rate limiting (default: 0.5)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-run classification even if results already exist",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the prompt for the first failure case and exit (no API calls)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for sampling (default: 42)",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable [DEBUG] print statements for tracing",
    )
    return parser.parse_args()


def main():
    global DEBUG
    args = parse_args()
    DEBUG = args.debug
    if DEBUG: print(f"[DEBUG] main(provider={args.provider}, model={args.model}, model_size={args.model_size}, sample_size={args.sample_size}, force={args.force}, dry_run={args.dry_run}, seed={args.seed})")

    # Resolve paths relative to this script's location.
    # Script lives at:   phase2/error_analysis/classify_errors.py
    # Trajectories at:   phase1/JSON_trajectories/
    # So: up 2 levels to repo root, then into phase1/JSON_trajectories
    script_dir = Path(__file__).resolve().parent
    traj_dir = Path(args.trajectory_dir) if args.trajectory_dir else (
        script_dir.parent.parent / "phase1" / "JSON_trajectories"
    )
    output_dir = Path(args.output_dir) if args.output_dir else (
        script_dir / "results"
    )
    model = args.model or DEFAULT_MODELS[args.provider]

    # Discover trajectory files
    print(
        f"Looking for Qwen3-{args.model_size.upper()} trajectories in: {traj_dir}")
    files = discover_files(traj_dir, args.model_size)
    if not files:
        sys.exit(f"No trajectory files found. Check --trajectory-dir path.")

    print(f"Found {len(files)} trajectory file(s)")
    for fp, name in files:
        print(f"  {name}: {fp.name}")

    # Create output dirs
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "plots").mkdir(exist_ok=True)
    (output_dir / "examples").mkdir(exist_ok=True)

    # Init API client (validates key exists)
    if not args.dry_run:
        client = create_client(args.provider)
        print(f"\nUsing {args.provider} / {model}")
    else:
        client = None
        print("\n[DRY RUN MODE]")

    # Process each trajectory file (6 files for 14b: 3 strategies x 2 domains)
    # Each file goes through: load JSON -> filter failures -> sample -> classify via API -> save
    all_results = {}
    for filepath, config_name in files:
        result = process_file(
            filepath=filepath,
            config_name=config_name,
            client=client,
            provider=args.provider,
            model=model,
            sample_size=args.sample_size,
            output_dir=output_dir,
            delay=args.delay,
            force=args.force,
            dry_run=args.dry_run,
        )
        if result:
            all_results[config_name] = result

    if not all_results:
        print("\nNo results to aggregate.")
        return

    # Save combined summary — this is the main output you'll reference in the report.
    # Structure: {"14b_ReAct_airline": {"policy_violation": {"count": 12, "percentage": 33.3}, ...}, ...}
    combined = aggregate_all(all_results)
    combined_path = output_dir / "combined_summary.json"
    with open(combined_path, "w") as f:
        json.dump(combined, f, indent=2)
    print(f"\nCombined summary: {combined_path}")

    # Extract representative examples (Phase 2 requirement: 5 per category)
    examples = extract_examples(all_results)
    examples_path = output_dir / "examples" / "representative_examples.json"
    with open(examples_path, "w") as f:
        json.dump(examples, f, indent=2)
    n_cats_with_examples = sum(1 for v in examples.values() if v)
    print(
        f"Representative examples: {examples_path} ({n_cats_with_examples} categories)")

    # Generate plots
    print("\nGenerating plots...")
    generate_plots(combined, output_dir / "plots")

    # Print summary table
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for config_name, result in sorted(all_results.items()):
        print(f"\n{config_name}:")
        for cat, info in result["summary"].items():
            bar = "#" * int(info["percentage"] / 2)
            print(
                f"  {cat:25s} {info['count']:3d} ({info['percentage']:5.1f}%) {bar}")

    print(f"\nDone! All outputs in: {output_dir}/")


if __name__ == "__main__":
    main()
