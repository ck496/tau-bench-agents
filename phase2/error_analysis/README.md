# Phase 2 Error Classification — tau-bench

## What This Does

This script automates the error analysis for Phase 2 of the tau-bench project. It reads the trajectory JSON files from our Phase 1 Qwen3 runs, finds every failed task (reward=0), sends each one to a strong LLM (Claude Sonnet or GPT-4o) with a structured prompt, and asks it to classify **why** the agent failed. The results go into JSON files and matplotlib plots that go directly into the report.

**Why use an LLM to classify errors instead of doing it by hand?**
We have ~300 failure cases across 6 trajectory files (3 strategies x 2 domains for 14B). Manually reading each conversation and labeling the error type would take hours and be inconsistent. By sending each case to the same model with the same prompt and same taxonomy, we get consistent, reproducible classifications in minutes. The cost is ~$5-10 in API calls.

---

## How This Maps to Phase 2 Requirements

| Phase 2 Requirement | What This Script Produces |
|---|---|
| **Error analysis report with quantitative breakdown** (10 pts) | `results/combined_summary.json` — counts and percentages per error category, per strategy, per domain. Paste into report. |
| **Plots comparing error types across baselines/model sizes** (part of 10 pts) | `results/plots/errors_by_strategy.png`, `errors_by_domain.png`, `error_breakdown_all.png` — ready for the report. |
| **5 representative failure trajectory JSONs per error category** (10 pts) | `results/examples/representative_examples.json` — auto-extracted with task_id, instruction, ground truth, agent actions, and explanation. |
| **Multi-agent system proposal** (20 pts) | NOT produced by this script. But the error distribution tells you which errors are most common, so your PATTS proposal can say: "Policy violations account for X% of failures -> Policy Validator module addresses this." |

---

## Prerequisites

```bash
# You need ONE of these API packages:
pip install anthropic    # for Claude Sonnet
# OR
pip install openai       # for GPT-4o

# For plots:
pip install matplotlib

# Set your API key:
export ANTHROPIC_API_KEY=sk-ant-...
# OR
export OPENAI_API_KEY=sk-...
```

---

## Quick Start

```bash
cd phase_2/error_analysis

# Basic run with Claude Sonnet (recommended — good quality, reasonable cost):
python classify_errors.py --provider anthropic

# Or with GPT-4o:
python classify_errors.py --provider openai

# See what the prompt looks like before spending money:
python classify_errors.py --provider anthropic --dry-run

# Run for a different model size (e.g., 32B for cross-model comparison):
python classify_errors.py --provider anthropic --model-size 32b

# Force re-run even if results already exist:
python classify_errors.py --provider anthropic --force
```

**Time estimate:** ~5-10 minutes for all 6 files (14B). ~$5-10 in API costs.

**Resume support:** If the script crashes mid-run, just re-run the same command. It saves progress after each classification and picks up where it left off.

---

## Output Files

After running, you'll find:

```
results/
├── 14b_ACT_airline.json            # Full results for each config
├── 14b_ACT_retail.json
├── 14b_ReAct_airline.json
├── 14b_ReAct_retail.json
├── 14b_FC_airline.json
├── 14b_FC_retail.json
├── combined_summary.json           # Aggregated counts/percentages across all configs
├── examples/
│   └── representative_examples.json  # 5 clearest failure examples per error category
└── plots/
    ├── errors_by_strategy.png      # Grouped bar: ReAct vs ACT vs FC
    ├── errors_by_domain.png        # Grouped bar: Airline vs Retail
    └── error_breakdown_all.png     # Stacked bar: all configs
```

### Per-config JSON structure

```json
{
  "config": "14b_ReAct_airline",
  "stats": {
    "total_tasks": 50,
    "total_failures_in_file": 178,
    "unique_failures_sampled": 36
  },
  "summary": {
    "policy_violation": {"count": 12, "percentage": 33.3},
    "wrong_arguments": {"count": 8, "percentage": 22.2},
    ...
  },
  "classifications": [
    {
      "task_id": 4,
      "trial": 0,
      "instruction": "Your user id is omar_rossi_1241. For your upcoming trip...",
      "ground_truth_actions": [...],
      "agent_actions": [...],
      "classification": {
        "primary_category": "policy_violation",
        "sub_category": "modification_rule",
        "explanation": "Agent tried to modify basic economy reservation which violates policy"
      }
    }
  ]
}
```

---

## Error Taxonomy

These are **our own categories** (the spec says: do NOT use the tau-bench paper's taxonomy). Edit the `ERROR_TAXONOMY` dict at the top of `classify_errors.py` to change them.

| Category | What It Means |
|---|---|
| `wrong_tool` | Called the wrong tool entirely |
| `wrong_arguments` | Right tool, wrong parameters |
| `policy_violation` | Broke a domain rule (cancellation, modification, compensation, auth) |
| `incomplete_execution` | Didn't finish all required actions for a multi-step task |
| `premature_escalation` | Transferred to human when it could have handled it |
| `information_error` | Gave user wrong info that affected the outcome |
| `reasoning_failure` | Misunderstood user intent or made wrong plan |
| `user_simulator_error` | User simulator's fault, not agent's |
| `context_or_format_error` | Context overflow, malformed JSON, infrastructure issue |

---

## How the Classification Works

For each failed task, the script builds a prompt containing:

1. **User's goal** — what the simulated user wanted (from `info.task.instruction`)
2. **Ground truth** — what the agent should have done (from `info.task.actions`)
3. **Domain policy** — the rules the agent was given (from the system prompt)
4. **Actual conversation** — what the agent actually did (from `traj`)
5. **Error taxonomy** — our category definitions

The LLM compares expected vs actual behavior and picks one category. This is essentially what tau-bench's own `auto_error_identification.py` does, but with our custom taxonomy.

---

## All CLI Options

| Flag | Default | Description |
|---|---|---|
| `--provider` | (required) | `anthropic` or `openai` |
| `--model` | auto | Model name (claude-sonnet-4-5-20250929 / gpt-4o) |
| `--model-size` | `14b` | Which Qwen3 size to analyze |
| `--sample-size` | `50` | Max unique failures per file |
| `--trajectory-dir` | auto-detected | Path to JSON_trajectories |
| `--output-dir` | `results/` | Where to save output |
| `--delay` | `0.5` | Seconds between API calls |
| `--force` | off | Re-run even if results exist |
| `--dry-run` | off | Print prompt, don't call API |
| `--seed` | `42` | Random seed for sampling |

---

## Running for Other Model Sizes

To get cross-model comparison plots (recommended for the report):

```bash
# After running 14b (default):
python classify_errors.py --provider anthropic --model-size 4b
python classify_errors.py --provider anthropic --model-size 8b
python classify_errors.py --provider anthropic --model-size 32b
```

Each run saves to separate files, so they don't overwrite each other.

---

## What to Do After Running

1. **Check `combined_summary.json`** — this has all the numbers for your report tables
2. **Copy plots from `results/plots/`** into your report document
3. **Review `examples/representative_examples.json`** — pick the clearest 5 per category for the submission
4. **Write the narrative** — the script gives you data, you write the analysis
5. **Connect to PATTS proposal** — "X% of failures are policy violations -> Policy Validator addresses this"
