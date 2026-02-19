# Crash & Context Window Analysis

**Script:** `phase2/error_analysis/analyze_crashes.py` | **Full data:** [`crash_analysis_all.json`](crash_analysis_all.json)

---

## Key Finding

**Smaller models crash dramatically more often.** Qwen3-4B has a 13.6% crash rate vs 0.3% for 14B — a 48x difference. Of the 755 total infrastructure crashes (entries that died before the agent could act), 715 (94.7%) were specifically context window overflows. These crashes are separate from the 290 behavioral errors classified by the LLM — they have empty trajectories and never reach the classifier.

## Cross-Model Crash Rates

All Qwen3 sizes share the same **32,768 token context limit**. Smaller models generate longer `<think>` reasoning traces per turn, consuming tokens faster. The system prompt alone is ~17K tokens (airline), leaving only ~15K for conversation — a tight budget when the model is verbose.

| Model | Entries | Crashes | Rate | Ctx Window | Timeout | Other |
|-------|---------|---------|------|------------|---------|-------|
| **4B** | 3,593 | 487 | **13.6%** | 476 | 11 | 0 |
| **8B** | 2,933 | 248 | **8.5%** | 228 | 20 | 0 |
| **14B** | 2,475 | 7 | **0.3%** | 5 | 1 | 1 |
| **32B** | 2,475 | 13 | **0.5%** | 6 | 6 | 1 |
| **Total** | **11,476** | **755** | **6.6%** | **715** | **38** | **2** |

## 14B Per-Config Breakdown

FC had zero crashes across both domains — its structured tool call format avoids the free-text overhead of ReAct/ACT `<think>` tags.

| Config | Total | Normal | Crashes | Ctx Window | Timeout | Other |
|--------|-------|--------|---------|------------|---------|-------|
| 14B_ACT_airline | 250 | 249 | 1 | 0 | 0 | 1 |
| 14B_ACT_retail | 575 | 573 | 2 | 2 | 0 | 0 |
| 14B_ReAct_airline | 250 | 249 | 1 | 1 | 0 | 0 |
| 14B_ReAct_retail | 575 | 572 | 3 | 2 | 1 | 0 |
| 14B_FC_airline | 250 | 250 | 0 | 0 | 0 | 0 |
| 14B_FC_retail | 575 | 575 | 0 | 0 | 0 | 0 |

## Context Window Exceeded — Detail

| Config | Task ID | Trial | Tokens Used | Token Limit | Over By |
|--------|---------|-------|-------------|-------------|---------|
| 14B_ACT_retail | 1 | 3 | 33,106 | 32,768 | +338 |
| 14B_ACT_retail | 5 | 3 | 34,346 | 32,768 | +1,578 |
| 14B_ReAct_airline | 27 | 4 | 33,583 | 32,768 | +815 |
| 14B_ReAct_retail | 99 | 0 | 33,225 | 32,768 | +457 |
| 14B_ReAct_retail | 108 | 2 | 40,681 | 32,768 | +7,913 |

## Other Crashes (Timeouts, Code Bugs)

| Config | Task ID | Trial | Type | Error |
|--------|---------|-------|------|-------|
| 14B_ACT_airline | 44 | 0 | other | argument of type 'int' is not iterable |
| 14B_ReAct_retail | 68 | 1 | api_timeout | API request timed out |

## Top 10 Longest Conversations (Context Pressure)

"Turns" counts total messages in the `traj` array (system + user + assistant + API output). A 62-turn conversation is ~30 agent-user exchanges plus tool call/response pairs.

**All 10 are failures.** Even without exceeding the context window, long conversations degrade model performance — the model attends less to earlier policy rules and user details as the conversation grows ("lost in the middle" effect). This surfaces as errors from our taxonomy: reasoning failures, incomplete execution, and wrong arguments rather than an explicit context overflow.

| Config | Task ID | Trial | Turns | Reward |
|--------|---------|-------|-------|--------|
| 14B_ACT_airline | 4 | 0 | 62 | FAIL |
| 14B_ACT_airline | 7 | 0 | 62 | FAIL |
| 14B_ACT_airline | 11 | 0 | 62 | FAIL |
| 14B_ACT_airline | 48 | 0 | 62 | FAIL |
| 14B_ACT_airline | 5 | 1 | 62 | FAIL |
| 14B_ACT_airline | 9 | 1 | 62 | FAIL |
| 14B_ACT_airline | 12 | 1 | 62 | FAIL |
| 14B_ACT_airline | 16 | 1 | 62 | FAIL |
| 14B_ACT_airline | 34 | 1 | 62 | FAIL |
| 14B_ACT_airline | 36 | 1 | 62 | FAIL |

## Impact on Error Analysis

Crashes are **not agent errors** — they have `traj: []` (empty trajectory) and `info.error` instead of `info.task`, so they never reach the LLM classifier. For **14B** (our primary target), only 7/2,475 entries crashed (0.3%) — the 290 classified failures are all genuine behavioral errors. See `combined_summary.json` for the full error breakdown.
