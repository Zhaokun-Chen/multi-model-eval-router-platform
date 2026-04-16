# Demo Script

## Demo Goal

Show that the project is not just a UI wrapper around one model. It demonstrates:

- multiple model access
- scenario-based evaluation
- explainable routing
- tradeoffs among quality, latency, cost, and stability

## Opening

This project is an MVP for AI platform / MaaS scenarios. The key question is not "can I call a model", but "which model should the platform call for this task, and why".

## Demo Steps

### 1. Show the routing interface

Explain that the page lets the user choose:

- task type
- routing strategy
- prompt

Then the system returns:

- selected model
- routing explanation
- generated output

### 2. Show `qa + quality`

Suggested prompt:

```text
Explain why an AI platform should not rely on a single model when balancing quality, latency, cost, and stability.
```

Talking point:

- this is a quality-sensitive analytical task
- the platform should prefer the stronger generation model
- the result shows that routing is aligned with quality-first strategy

### 3. Show `summary + balanced`

Suggested prompt:

```text
Summarize the value of offline evaluation before online routing in a model platform.
```

Talking point:

- this task needs good compression but not necessarily the slowest, strongest model
- balanced strategy illustrates how routing can trade off quality and latency

### 4. Show `structured_extraction + cost`

Suggested prompt:

```text
Extract the following into JSON with fields user, priority, requirement, and deadline: "Alice needs a low-cost model for daily summaries by Friday."
```

Talking point:

- structured extraction is where format stability matters
- local AWQ can be a good fit when output format and cost are prioritized
- this demonstrates that the cheapest option is not always weak for every task

### 5. Show `rewrite + quality`

Suggested prompt:

```text
Rewrite this sentence in a more professional product-document tone: "We should not choose models by gut feeling."
```

Talking point:

- rewriting is generation-heavy
- a higher-quality remote model usually performs better here
- this shows clear task differentiation across models

## Close

Wrap up with three points:

- the platform uses one interface to access multiple models
- routing is informed by offline evidence instead of pure intuition
- the project can evolve toward automatic task classification, richer fallback chains, and better observability
