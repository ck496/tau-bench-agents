# Phase 2: Error Analysis and Multi-Agent System Proposal

**Course:** CSE 598 - AI Agents | **Benchmark:** tau-bench | **Model:** Qwen3-14B | **Date:** February 2026

---

## 1. Error Analysis

### 1.1 Methodology

We classified **290 unique failure cases** across 6 trajectory configurations (3 strategies x 2 domains) for Qwen3-14B. Each failure was sent to Claude Sonnet 4.5 via the Anthropic API with a structured prompt containing: (1) the user's goal, (2) ground truth actions, (3) domain policy rules, (4) the full agent conversation, and (5) our custom error taxonomy. The LLM compared expected vs. actual behavior and assigned exactly one category per failure.

**Why LLM-based classification?** With ~290 cases, manual labeling would take hours and introduce inconsistency. Sending every case to the same model with the same prompt and same taxonomy gives reproducible, consistent results. This mirrors tau-bench's own `auto_error_identification.py` approach but uses our custom taxonomy.

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

### 1.3 Quantitative Breakdown

#### Overall Error Distribution (Averaged Across All 6 Configs)

| Error Category           | Avg %     | Airline Avg % | Retail Avg % |
| ------------------------ | --------- | ------------- | ------------ |
| **Policy Violation**     | **28.5%** | 23.6%         | 33.3%        |
| **Incomplete Execution** | **22.6%** | 17.2%         | 28.0%        |
| **Reasoning Failure**    | **19.0%** | 22.0%         | 16.0%        |
| **Wrong Arguments**      | **18.7%** | 18.6%         | 18.7%        |
| **Wrong Tool**           | **4.9%**  | 7.9%          | 2.0%         |
| **Premature Escalation** | **5.1%**  | 8.7%          | 2.0%         |
| **User Simulator Error** | **1.0%**  | 2.1%          | 0.0%         |
| **Information Error**    | **0.3%**  | 0.0%          | 0.7%         |

**The top 4 categories (policy violation, incomplete execution, reasoning failure, wrong arguments) account for ~89% of all failures.** These are the targets for our multi-agent proposal.

#### Per-Configuration Breakdown

| Config               | Policy Viol. | Incomplete | Reasoning | Wrong Args | Other |
| -------------------- | ------------ | ---------- | --------- | ---------- | ----- |
| ACT Airline (n=46)   | 19.6%        | 23.9%      | 21.7%     | 17.4%      | 17.4% |
| ACT Retail (n=50)    | 24.0%        | 30.0%      | 20.0%     | 20.0%      | 6.0%  |
| ReAct Airline (n=44) | 27.3%        | 13.6%      | 18.2%     | 20.5%      | 20.5% |
| ReAct Retail (n=50)  | 30.0%        | 32.0%      | 12.0%     | 22.0%      | 4.0%  |
| FC Airline (n=50)    | 24.0%        | 14.0%      | 26.0%     | 18.0%      | 18.0% |
| FC Retail (n=50)     | **46.0%**    | 22.0%      | 16.0%     | 14.0%      | 2.0%  |

#### Key Observations

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

#### Incomplete Execution -- "Handled one exchange, forgot the second"

> **Task 14, FC Retail:** User needed two separate exchanges (hiking boots + jigsaw puzzle). The agent never even started -- conversation shows user messages but no agent actions. The agent failed to authenticate the user or take any of the required steps.

#### Reasoning Failure -- "Confused its own role with the user's"

> **Task 7, FC Airline:** The agent completely confused its role with the user's. Instead of acting as the customer service agent, it responded as if it were the user asking for help. This fundamental misunderstanding prevented any useful tool calls.

#### Wrong Arguments -- "Exchanged boots for wrong size"

> **Task 108, FC Retail:** The agent exchanged hiking boots (item 1615379700) for item 4582956489 (size 12) instead of the correct same-spec replacement (same item_id, size 10). The user wanted "the same specs" but the agent picked a different variant.

#### Premature Escalation -- "Transferred to human despite having the user_id"

> **Task 0, ReAct Airline:** The agent transferred to a human claiming it needed the user's ID, but the user goal clearly states "Your user id is mia_li_3668". The agent should have asked the user directly or extracted it from the conversation.

---

## 2. Multi-Agent System Proposal: PACE

**P**olicy-**A**ware **C**ontext-**E**ngineered Multi-Agent System

### 2.1 Design Rationale

Our error analysis reveals four failure modes that account for 89% of errors. Each points to a specific architectural fix:

| Failure Mode         | % of Errors | Root Cause                                                               | Proposed Fix                                                                               |
| -------------------- | ----------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| Policy Violation     | 28.5%       | Agent has policies in system prompt but ignores them under task pressure | **Policy Validator** -- dedicated agent that checks actions against rules before execution |
| Incomplete Execution | 22.6%       | Agent loses track of multi-step plans mid-conversation                   | **Task Planner** -- decomposes tasks upfront, tracks completion                            |
| Reasoning Failure    | 19.0%       | Agent misreads user intent or makes flawed plans                         | **Context Engineer** -- structures and enriches context before reasoning                   |
| Wrong Arguments      | 18.7%       | Agent picks wrong parameter values for correct tools                     | **Argument Verifier** -- validates tool arguments against ground truth schemas             |

### 2.2 Architecture

```
User Message
     |
     v
[Context Engineer]  <-- Structures input, extracts key entities (user_id, order_ids, etc.)
     |                   Uses RAG to retrieve relevant policies for this specific task
     v
[Task Planner]      <-- Decomposes into ordered sub-tasks with dependencies
     |                   Pattern: Planning (Gulli Ch. 4) + Hierarchical Task Decomposition
     v
[Executor Agent]    <-- Executes each sub-task using domain tools
     |                   Pattern: Tool Use + ReAct for step-by-step execution
     |
     +---> [Policy Validator]   <-- Pre-execution check: "Does this action violate any rule?"
     |                              Pattern: Multi-Agent Review & Critique (Gulli)
     |
     +---> [Argument Verifier]  <-- Pre-execution check: "Are these parameters valid?"
     |                              Validates against tool schemas and retrieved context
     v
[Step Verifier]     <-- Post-execution: marks sub-task complete, checks if plan is done
     |                   Pattern: Reflection (Gulli) -- evaluates own output before continuing
     v
Response to User
```

### 2.3 How Each Agent Works

#### Context Engineer (Pre-Processing)

**Problem it solves:** Reasoning failures (19%) often stem from the agent missing key information buried in long conversations or complex system prompts.

**How it works:**

- Extracts structured entities from the user message: user_id, reservation IDs, order IDs, dates, amounts
- Uses **RAG** to retrieve only the relevant policy sections for this specific task type (e.g., "cancellation policies" for a cancellation request) rather than stuffing the entire policy document into the prompt
- Produces a structured context block that downstream agents consume

**Design pattern:** Context Engineering + RAG (Retrieval-Augmented Generation). Instead of relying on the model to parse a 17K-token system prompt, we pre-retrieve the 2-3 relevant policy paragraphs. This is the same principle behind GraphRAG for regulatory compliance -- structured retrieval over flat text dumps.

**Why RAG over full-prompt policies:** Our system prompts are ~17K tokens. The agent must find the one rule that applies (e.g., "basic economy cannot be modified") among dozens. RAG retrieves exactly the relevant rules, reducing cognitive load and token cost.

#### Task Planner (Decomposition)

**Problem it solves:** Incomplete execution (22.6%) -- agent handles step 1 but forgets steps 2-4.

**How it works:**

- Takes the structured context and generates an explicit plan: `[Step 1: Find user -> Step 2: Get order details -> Step 3: Exchange item A -> Step 4: Exchange item B]`
- Each step has a completion flag
- The planner identifies dependencies (Step 3 requires Step 1's output)

**Design pattern:** Planning pattern (Gulli) + Plan-and-Act separation. Research validates this: "Plan-and-Act" (2025) achieved 57.58% on WebArena-Lite by separating planning from execution. The key insight is that planning and execution require different capabilities -- planning needs broad reasoning, execution needs precise tool use.

#### Policy Validator (Pre-Execution Guardrail)

**Problem it solves:** Policy violations (28.5%) -- the single largest error category.

**How it works:**

- Before any tool call executes, the validator receives: (1) the proposed action, (2) the relevant policy rules (from RAG), (3) the current conversation state
- It answers one question: "Does this action violate any policy rule?"
- If yes: blocks the action and returns the specific rule violated
- If no: approves execution

**Design pattern:** Multi-Agent Review & Critique (Gulli) + Guardrails. This mirrors how the OpenAI Agents SDK implements guardrails -- validation runs in parallel with generation, blocking unsafe outputs before they reach the user. It's also the core principle behind AgenTRIM (2025), which enforces least-privilege tool access at runtime.

**Why a separate agent?** A single agent juggling conversation + tool use + policy compliance suffers from attention dilution. A dedicated validator with a narrow prompt ("check this one action against these specific rules") is more reliable than asking the main agent to self-police.

#### Argument Verifier (Parameter Validation)

**Problem it solves:** Wrong arguments (18.7%) -- right tool, wrong parameters.

**How it works:**

- Validates tool arguments against: (1) the tool's JSON schema (type checking), (2) values extracted by the Context Engineer (e.g., does the order_id match what the user mentioned?), (3) domain constraints (e.g., item_id exists in the order)
- Catches errors like: wrong item_id, wrong payment method, mismatched order/item combinations

**Design pattern:** Tool Use validation + MCP-style schema enforcement. Anthropic's Model Context Protocol (MCP) standardizes tool schemas so that arguments are validated before execution. We apply the same principle: define strict schemas, validate before calling.

#### Step Verifier (Post-Execution Reflection)

**Problem it solves:** Incomplete execution + cascading errors from failed steps.

**How it works:**

- After each tool call, checks: "Did this step succeed? Is the plan progressing?"
- Updates the planner's completion tracking
- If a step fails: triggers re-planning rather than continuing with a broken state

**Design pattern:** Reflection (Gulli) + AgentPro-style process supervision. "Enhancing LLM Agents with Automated Process Supervision" (EMNLP 2025) shows that step-level verification catches errors that end-to-end evaluation misses.

### 2.4 Inter-Agent Communication

Agents communicate through a **shared state object** (following LangGraph's centralized state pattern):

```python
state = {
    "user_message": "...",
    "extracted_entities": {"user_id": "mia_li_3668", "reservation_id": "HXDUBJ"},
    "relevant_policies": ["Basic economy cannot be modified", ...],
    "plan": [
        {"step": 1, "action": "get_reservation_details", "status": "completed"},
        {"step": 2, "action": "update_flights", "status": "blocked", "reason": "policy violation"},
    ],
    "conversation_history": [...],
}
```

This follows the **coordinator pattern** (Gulli): a central orchestrator routes tasks to specialist agents based on the current state. In production, this could use Google's **A2A (Agent-to-Agent) protocol** for standardized agent discovery and task delegation -- each agent publishes an Agent Card describing its capabilities, and the orchestrator routes based on those cards.

### 2.5 Why This Architecture

**Grounded in our data, not hypothetical:** Every component maps directly to an observed failure mode. We're not adding complexity for its own sake -- each agent exists because a specific error category demands it.

**Follows established patterns:** The architecture combines 5 patterns from Gulli's taxonomy (Planning, Tool Use, Reflection, Multi-Agent Review & Critique, Coordinator) with industry practices (RAG for policy retrieval, guardrails for validation, plan-execute separation).

**Supported by recent research:**

- _Plan-and-Act_ (2025): Planning/execution separation improves multi-step task success
- _AgentPro_ (EMNLP 2025): Step-level process supervision catches errors earlier
- _ReConcile_ (NeurIPS 2024): Multi-agent discussion + reflection improves collaborative reasoning
- _AgenTRIM_ (2025): Runtime tool validation prevents policy-violating actions

### 2.6 Expected Impact

| Error Category       | Current % | Target Reduction | Mechanism                                                  |
| -------------------- | --------- | ---------------- | ---------------------------------------------------------- |
| Policy Violation     | 28.5%     | 60-70%           | Policy Validator blocks rule-violating actions             |
| Incomplete Execution | 22.6%     | 50-60%           | Task Planner tracks completion; Step Verifier catches gaps |
| Reasoning Failure    | 19.0%     | 30-40%           | Context Engineer provides structured, relevant context     |
| Wrong Arguments      | 18.7%     | 40-50%           | Argument Verifier validates parameters before execution    |

**Conservative estimate:** If PACE reduces the top-4 error categories by 40-50% on average, overall pass^1 for Qwen3-14B could improve from ~0.15-0.34 to ~0.25-0.50 depending on strategy and domain.

### 2.7 Implementation Plan (Phase 3)

1. **Week 1:** Implement Context Engineer + Task Planner using LangGraph for orchestration
2. **Week 1-2:** Implement Policy Validator as a guardrail agent with RAG-based policy retrieval
3. **Week 2:** Implement Argument Verifier + Step Verifier
4. **Week 2:** Run full tau-bench evaluation (same protocol as Phase 1) and compare pass^k

---

## 3. Individual Contribution

Chris: Created the python script to perform error analysis for the different models with LLM-based classifications
Marko:
Jay:
Mohit:
Han:

---

## References

1. Gulli, A. (2025). _Agentic Design Patterns: A Hands-On Guide to Building Intelligent Systems_. Springer.
2. Yao et al. (2023). "ReAct: Synergizing Reasoning and Acting in Language Models." ICLR 2023.
3. "Plan-and-Act: Improving Planning of Agents for Long-Horizon Tasks." arXiv:2503.09572, 2025.
4. "Enhancing LLM Agents with Automated Process Supervision." EMNLP 2025.
5. "Reflective Multi-Agent Collaboration based on Large Language Models." NeurIPS 2024.
6. "Harmonizing Multi-Agent Systems via Joint Alignment Tuning." EMNLP 2025 Findings.
7. "AgenTRIM: Tool Risk Mitigation for Agentic AI." arXiv:2601.12449, 2025.
8. Google. "Agent-to-Agent Protocol (A2A)." developers.googleblog.com, 2025.
9. Anthropic. "Model Context Protocol (MCP)." modelcontextprotocol.io, 2024.
10. Yue et al. (2024). "tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains." arXiv:2406.12045.
