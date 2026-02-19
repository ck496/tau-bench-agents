# Language Agents for τ-Bench

 **Problem Statement:** τ-bench is a benchmark framework for evaluating tool-using conversational agents in realistic simulated user scenarios (airline and retail). Agents interact with simulated users and apply domain-specific tool APIs and policy rules to complete tasks. Evaluation metrics such as  pass^k measure success reliability over multiple trials. Students will study, run, extend, and analyze the τ-bench benchmarks in the two domains (airline and retail) for tool-using conversational agents. The goal is to understand how agents  interact in multiturn scenarios and performance variation across different strategies and LLM sizes, implement experiments with pre-defined baseline strategies (ReAct, Function Calling, ACT), and conduct fine-grained error analyses and plots comparing results across models.

**Goals of the Project:** By the end of this project, students will be able to:

- Explain how tool-using agents operate in realistic simulated conversations with APIs and policy constraints.
- Run τ-Bench experiments using standard baselines (ReAct, Function Calling, ACT) and multiple LLM configurations.
- Evaluate agent reliability using repeated-trial metrics (e.g., pass^k) and interpret the results.
- Diagnose errors with a structured taxonomy and produce plots that highlight performance differences.
- Develop, test, and justify an improved agent (or multi-agent) method that exceeds baseline performance.

## Project details:

1. **Set up the benchmark:** You should begin by cloning the τ-Bench repository ([https://github.com/sierra-research/tau-benchLinks to an external site.](https://github.com/sierra-research/tau-bench)) and installing the package locally following the instructions in the README.

   1. Next, set up the required LLM API keys as environment variables for any closed-source models you’ll be using (GPT, Gemini, and the Claude family).
      1. For open-source models, you’ll need to run a vLLM server. Students should calculate pass^1, pass^2, pass^3, pass^4, pass^5 for the evaluation metric by running 5 trials.
2. **Models:**
3. **anix]Tool Calling Agent:** You should vary the model of Tool Calling Agent across multiple **Qwen3** sizes—Qwen3-4B, Qwen3-8B, Qwen3-14B, and Qwen3-32B—while keeping all other experimental settings fixed (including the **user model**) to enable fair, size-scaled comparisons.
4. **Methods:** You should perform experiments in different baselines.

- **ReAct (Reason + Act):** It is a pattern where an agent alternates between reasoning about the problem and taking an action, rather than doing all the thinking upfront. After each action, it uses the new observation to update its next step, enabling more adaptive, step-by-step problem solving in dynamic settings. For details you can read: [https://www.promptingguide.ai/techniques/reactLinks to an external site.](https://www.promptingguide.ai/techniques/react)
- **ACT (Action-Centric / Actor-style):** The agent focuses on selecting the next best action (often tool calls) with minimal explicit reasoning shown, relying on structured decision steps. It emphasizes efficient action sequencing and state tracking across turns to reach the goal.
- **FC (Function Calling):** The agent uses structured function/tool calls with explicit schemas (name + arguments) rather than free-form action descriptions. This improves tool reliability by constraining outputs and making tool invocation more precise and easier to parse. For details you can read: [https://platform.openai.com/docs/guides/function-callingLinks to an external site.](https://platform.openai.com/docs/guides/function-calling)

## Phases:

For this project, we have three phases.

### Phase 1: Benchmark Setup + Baseline Results 

`Grade: 20- each part in submission has 10 marks)`

In this phase, you will set up τ-Bench and reproduce baseline performance using the provided strategies (**ReAct, ACT, Function Calling**) with a **fixed user agent**. You will also vary the tool calling agent across Qwen3 sizes (4B/8B/14B/32B) to study how model scale affects tool-use success.

**What you need to submit:** You should submit the following files in a zip:

1. A document contains a short write-up describing your setup (models, domains, key configs)+ **Individual Contribution +** a results table of pass^k for each baseline × model size. (k=1 to 5)+Screenshot of results in the terminal with your username. 
2. Json files of trajectory for each case (Total 2 domains X User Assistant combination (4) X 3 different baselines X 5 trials)

**Deadline:** Thursday- 02/05/2026- [time, 11:59 PM]

---

### Phase 2: Error Analysis and your Multi-Agent Method idea

```
Grade:  40  
- 1st part in submission has 10 marks, 
- 2nd part in submission has 10 marks and 2nd part in submission has 20 marks)
```

In this phase, you will diagnose _why_ baselines fail and use those insights to propose a multi-agent framework that improves performance. This includes building an error taxonomy and identifying the most frequent failure modes.

Do not use the error taxonomy from the τ-bench paper—define your own set of categories instead. When designing the multi-agent system, draw inspiration from recent work published in ACL, EMNLP, NeurIPS, AAAI, ICML, and ICLR (for example, the paper at [https://arxiv.org/pdf/2508.20931Links to an external site.](https://arxiv.org/pdf/2508.20931)). However, use these papers as references only—do not replicate their pipeline.

**What you need to submit:** You should submit the following files in a zip:

1.  an error analysis report with quantitative breakdown, plots comparing error types across baselines/model sizes, and Mention  **Individual Contribution.**
2.  at least 5 representative failure examples trajectory json for each error categories 
3.  a clear proposal of your multi-agent system (architecture diagram/pseudocode + rationale connecting it directly to observed errors)

**Deadline**: Thursday- 02/19/2026- [time, 11:59 PM]

---

### Phase 3: Multi-Agent Results + Improvement Demonstration

`Marks: 40- each part in submission has 8 marks`

In this phase, you will implement your proposed multi-agent framework and evaluate it under the same exact benchmark protocol used in Phase 1. The key goal is to demonstrate measurable gains over baselines and explain how the new system achieves those gains.

**What you need to submit:** You should submit the following files in a zip:

1. final code for your multi-agent system and evaluation scripts, 
2.  A document containing final results table and plots comparing your method vs. baselines + Mention  **Individual Contribution.** 
3. Json files of trajectory for each models 
4. A document of  trajectory highlights: include a small set of side-by-side example conversations showing baseline failure vs. your method’s successful trajectory, with short annotations explaining what changed and why it worked.
5. Screenshot of results in terminal with name.

**Deadline:** Tuesday- 03/03/2026- [time, 11:59 PM]

---

### Tips:

**General Tips:**  Complete the project within your own group.**Do not share** with other groups any of the following (in whole or in part):

1. Code or private repositories
2. Experiment scripts or “working configs”
3. Prompts or agent instructions
4. Results tables, outputs, or intermediate artifacts

**Do not reuse another group’s implementation**, even if you modify it.**No coordinating across groups** to copy solutions, exchange outputs, or align results—this will be treated as **academic misconduct**.**Allowed:** discussing high-level ideas without implementation detail or outputs, such as:

1. Conceptual approaches and design choices
2. General debugging tips
3. Paper references / related work

If you use **external libraries, public code, or published methods**:

1. **Cite them clearly** in your report
2. Ensure your submission remains **substantially your group’s own work**

If your project is **especially creative**, we can support you in turning it into a **paper**.
