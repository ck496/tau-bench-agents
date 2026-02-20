# Phase 2: Error Analysis and Multi-Agent System Proposal

**Course:** CSE 598 - AI Agents | **Benchmark:** tau-bench | **Models:** Qwen3-8B, Qwen3-14B | **Date:** February 2026

---

## 1. Error Analysis

### 1.1 Methodology

We focused our analysis on **Qwen3-14B**, the model size with the lowest crash rate (0.3%) and highest behavioral signal. Across all 6 configurations (3 strategies x 2 domains), 14B produced ~1,835 total failures. We sampled **290 unique failure cases** (50 per config, fewer where configs had less) and classified each using Claude Sonnet 4.5 via the Anthropic API. Each failure was sent with a structured prompt containing: (1) the user's goal, (2) ground truth actions, (3) domain policy rules, (4) the full agent conversation, and (5) our custom error taxonomy. The LLM compared expected vs. actual behavior and assigned exactly one category per failure.

**Why LLM-based classification?** With ~290 cases, manual labeling would take hours and introduce inconsistency. Sending every case to the same model with the same prompt and same taxonomy gives reproducible, consistent results. This mirrors tau-bench's own `auto_error_identification.py` approach but uses our custom taxonomy.

**Two types of failures, two scripts.** Not all failures are behavioral errors. Entries that crash before the agent can act — context window overflows, API timeouts, code bugs — have empty trajectories (`traj: []`) and an `info.error` field instead of `info.task`. These _infrastructure crashes_ are detected programmatically by `analyze_crashes.py`, which parses error messages and extracts token counts. They never reach the LLM classifier. The remaining failures have full conversation trajectories and represent genuine _behavioral errors_ — these are the 290 cases classified by `classify_errors.py` via Claude Sonnet 4.5. For 14B, only 7 of 2,475 entries crashed (0.3%), so the two populations are nearly disjoint. Full crash analysis is in `context_crash_analysis_summary.md`.

### 1.2 Error Taxonomy

We defined 9 categories (the spec requires our own taxonomy, not the tau-bench paper's):

| Category                 | Description                                                              |
| ------------------------ | ------------------------------------------------------------------------ |
| **Policy Violation**     | Broke a domain rule (e.g., modifying basic economy, unauthorized refund) |
| **Incomplete Execution** | Completed some but not all required actions for a multi-step task        |
| **Reasoning Failure**    | Misunderstood user intent or made a wrong plan despite correct info      |
| **Wrong Arguments**      | Right tool, wrong parameters (e.g., wrong item_id, wrong payment method) |
| **Wrong Tool**           | Called the wrong tool entirely (e.g., return instead of exchange)        |
| **Premature Escalation** | Transferred to human when it could have handled the request              |
| **Information Error**    | Gave user wrong information that affected the outcome                    |
| **User Simulator Error** | Simulator gave ambiguous/contradictory instructions (not agent's fault)  |
| **Context/Format Error** | Context overflow, malformed JSON, or infrastructure failure              |

### 1.3 Qwen3-14B Results

#### 14B Overall Error Distribution (Averaged Across All 6 Configs)

| Error Category           | Avg %     | Airline Avg % | Retail Avg % |
| ------------------------ | --------- | ------------- | ------------ |
| **Policy Violation**     | **28.5%** | 23.6%         | 33.3%        |
| **Incomplete Execution** | **22.6%** | 17.2%         | 28.0%        |
| **Reasoning Failure**    | **19.0%** | 22.0%         | 16.0%        |
| **Wrong Arguments**      | **18.7%** | 18.6%         | 18.7%        |
| **Wrong Tool**           | **4.9%**  | 7.9%          | 2.0%         |
| **Premature Escalation** | **5.0%**  | 8.7%          | 1.3%         |
| **User Simulator Error** | **1.0%**  | 2.1%          | 0.0%         |
| **Information Error**    | **0.3%**  | 0.0%          | 0.7%         |
| **Context/Format Error** | **0.0%**  | 0.0%          | 0.0%         |

> **Note:** Context/Format Error is 0.0% because context window overflows, API timeouts, and infrastructure crashes produce empty trajectories (`traj: []`) and never reach the classifier. These 7 crashed entries (0.3% of all 14B runs) are analyzed separately in the crash analysis — see `results/crash_analysis_summary.md`.

**Context pressure without crashing:** Conversations that stay under the 32,768 token limit can still degrade from context pressure. The 10 longest non-crashed 14B conversations (all 62 turns, all failures) suggest that as conversations grow, the model attends less to earlier policy rules and user details — manifesting as reasoning failures, incomplete execution, and wrong arguments rather than an explicit context overflow.

**The top 4 categories (policy violation, incomplete execution, reasoning failure, wrong arguments) account for ~89% of all failures.** These are the targets for our multi-agent proposal.

#### 14B Per-Configuration Breakdown

| Config               | Policy Viol. | Incomplete | Reasoning | Wrong Args | Other |
| -------------------- | ------------ | ---------- | --------- | ---------- | ----- |
| ACT Airline (n=46)   | 19.6%        | 23.9%      | 21.7%     | 17.4%      | 17.4% |
| ACT Retail (n=50)    | 24.0%        | 30.0%      | 20.0%     | 20.0%      | 6.0%  |
| ReAct Airline (n=44) | 27.3%        | 13.6%      | 18.2%     | 20.5%      | 20.5% |
| ReAct Retail (n=50)  | 30.0%        | 32.0%      | 12.0%     | 22.0%      | 4.0%  |
| FC Airline (n=50)    | 24.0%        | 14.0%      | 26.0%     | 18.0%      | 18.0% |
| FC Retail (n=50)     | **46.0%**    | 22.0%      | 16.0%     | 14.0%      | 2.0%  |

#### 14B Key Observations

1. **Policy violations dominate retail FC** (46%) -- FC's structured outputs give a false sense of correctness; the model calls the right tool shape but violates business rules.
2. **Incomplete execution is worst in retail** (28% avg vs 17% airline) -- retail tasks often require multiple exchanges/returns across different orders, and the agent stops after handling only one.
3. **Reasoning failures are highest in airline** (22% avg) -- airline policies have more edge cases (fare classes, medical exceptions, loyalty tiers) that require multi-step reasoning.
4. **Strategy matters less than domain** -- error distributions are more similar within a domain than within a strategy, suggesting domain complexity drives failure modes more than agent architecture.

### 1.4 Plots

_(See `phase2/error_analysis/results/plots/` for high-resolution versions)_

- **`errors_by_strategy.png`** -- Grouped bar chart comparing ReAct vs ACT vs FC error distributions
- **`errors_by_domain.png`** -- Grouped bar chart comparing Airline vs Retail error distributions
- **`error_breakdown_all.png`** -- Stacked bar showing full breakdown per configuration

### 1.5 Representative Failure Examples

Below are representative failures for each major error category. Full trajectory JSONs with 5 examples per category are in `phase2/error_analysis/results/examples/representative_examples.json`.

#### Policy Violation -- "Modified basic economy when policy forbids it"

> **Task 24, ACT Airline:** User asked to change flights on reservation HXDUBJ. The agent modified the flights without checking the cabin class. Per airline policy, basic economy tickets cannot be modified. The agent should have refused the request and explained the restriction.

#### Incomplete Execution -- "Never started a multi-step exchange task"

> **Task 14, FC Retail:** User needed two separate exchanges (hiking boots + jigsaw puzzle). The agent never even started -- conversation shows user messages but no agent actions. The agent failed to authenticate the user or take any of the required steps.

#### Reasoning Failure -- "Confused its own role with the user's"

> **Task 7, FC Airline:** The agent completely confused its role with the user's. Instead of acting as the customer service agent, it responded as if it were the user asking for help. This fundamental misunderstanding prevented any useful tool calls.

#### Wrong Arguments -- "Exchanged boots for wrong size"

> **Task 108, FC Retail:** The agent exchanged hiking boots (item 1615379700) for item 4582956489 (size 12) instead of the correct same-spec replacement (same item_id, size 10). The user wanted "the same specs" but the agent picked a different variant.

#### Premature Escalation -- "Transferred to human despite having the user_id"

> **Task 0, ReAct Airline:** The agent transferred to a human claiming it needed the user's ID, but the user goal clearly states "Your user id is mia_li_3668". The agent should have asked the user directly or extracted it from the conversation.

#### Wrong Tool -- "Canceled the wrong order entirely"

> **Task 59, ACT Retail:** User wanted to cancel order #W8268610, but the agent canceled #W2702727 instead. The agent retrieved the user's details, saw multiple orders, and picked the wrong one — calling `cancel_pending_order` on an order the user never mentioned.

#### Information Error -- "Calculated wrong refund amount"

> **Task 28, ACT Retail:** User asked about a potential refund. The agent calculated $2,441.42, but the correct amount was $918.43. The wrong number led the user to make a decision based on incorrect information.

#### User Simulator Error -- "Simulator reversed roles mid-conversation"

> **Task 45, FC Airline:** The user simulator switched roles and began acting as the agent, issuing tool calls and responding to itself. This is not an agent failure — it's a limitation of using Qwen3-32B as the user simulator.

### 1.6 Qwen3-8B Error Analysis

We repeated the same classification process for **Qwen3-8B** (287 sampled failures across 6 configs). The 8B model has a significantly higher infrastructure crash rate (8.5% vs 0.3% for 14B — 248 of 2,933 entries crashed), so the behavioral errors below represent only the non-crashed population.

#### 8B Overall Error Distribution (Averaged Across All 6 Configs)

| Error Category           | Avg %     | Airline Avg % | Retail Avg % |
| ------------------------ | --------- | ------------- | ------------ |
| **Reasoning Failure**    | **27.6%** | 29.3%         | 26.0%        |
| **Policy Violation**     | **22.6%** | 21.2%         | 24.0%        |
| **Incomplete Execution** | **22.4%** | 16.8%         | 28.0%        |
| **Premature Escalation** | **11.7%** | 15.3%         | 8.0%         |
| **Wrong Arguments**      | **10.8%** | 10.9%         | 10.7%        |
| **Wrong Tool**           | **2.5%**  | 3.6%          | 1.3%         |
| **Context/Format Error** | **1.1%**  | 1.5%          | 0.7%         |
| **Information Error**    | **0.7%**  | 1.5%          | 0.0%         |
| **User Simulator Error** | **0.7%**  | 0.0%          | 1.3%         |

> **Note:** The LLM classifier occasionally assigned labels outside our taxonomy (`parse_error`, `api_error`) for 8B trajectories that contained malformed output or mid-conversation API failures. These were merged into Context/Format Error for consistency.

#### 8B Per-Configuration Breakdown

| Config               | Policy Viol. | Incomplete | Reasoning | Wrong Args | Other |
| -------------------- | ------------ | ---------- | --------- | ---------- | ----- |
| ACT Airline (n=46)   | 17.4%        | 17.4%      | 26.1%     | 8.7%       | 30.4% |
| ACT Retail (n=50)    | 16.0%        | 28.0%      | 22.0%     | 20.0%      | 14.0% |
| ReAct Airline (n=45) | 20.0%        | 13.3%      | 35.6%     | 8.9%       | 22.2% |
| ReAct Retail (n=50)  | 34.0%        | 22.0%      | 28.0%     | 4.0%       | 12.0% |
| FC Airline (n=46)    | 26.1%        | 19.6%      | 26.1%     | 15.2%      | 13.0% |
| FC Retail (n=50)     | 22.0%        | 34.0%      | 28.0%     | 8.0%       | 8.0%  |

#### 8B Key Observations

1. **Reasoning failure is the top error for 8B** (27.6% avg) — unlike 14B where policy violation leads. The smaller model struggles more with understanding user intent and planning multi-step actions.
2. **Premature escalation more than doubles** (11.7% vs 5.0% for 14B) — the 8B model gives up and transfers to a human far more often, especially in airline ACT (23.9%).
3. **ReAct airline reasoning failures are extreme** (35.6%) — over a third of all errors. The ReAct format's free-text reasoning amplifies the 8B model's tendency to misinterpret complex airline policies.
4. **"Other" is much larger for 8B airline configs** (22-30%) — driven primarily by premature escalation, which is a minor category for 14B.

### 1.7 Cross-Model Comparison: 8B vs 14B

| Category                 | 8B Avg | 14B Avg | Shift  |
| ------------------------ | ------ | ------- | ------ |
| **Reasoning Failure**    | 27.6%  | 19.0%   | +8.6pp |
| **Premature Escalation** | 11.7%  | 5.0%    | +6.7pp |
| **Policy Violation**     | 22.6%  | 28.5%   | -5.9pp |
| **Wrong Arguments**      | 10.8%  | 18.7%   | -7.9pp |
| **Incomplete Execution** | 22.4%  | 22.6%   | ~0     |

**The error distribution reveals a competence gradient.** The 8B model fails earlier in the task pipeline — it misunderstands user intent (reasoning failure +8.6pp) and gives up prematurely (premature escalation +6.7pp). The 14B model gets further but fails at execution — it understands what to do but violates domain rules (policy violation +5.9pp) and passes wrong parameters (wrong arguments +7.9pp). Incomplete execution is essentially unchanged (~22%), suggesting multi-step task completion is equally difficult regardless of model size. The 8B model also crashes 28x more often (8.5% vs 0.3%), meaning a larger fraction of its failures never even reach behavioral classification.

---

## 3. Individual Contribution

Chris: Created the python script to perform error analysis for the different models with LLM-based classifications
Marko:
Jay:
Mohit:
Han:

---
