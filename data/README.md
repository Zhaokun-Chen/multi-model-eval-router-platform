# Evaluation Dataset Notes

The public dataset file is:

- `eval_dataset.json`

## Purpose

This dataset is designed for product-facing offline evaluation in AI platform / MaaS scenarios.

It is not intended as a large-scale academic benchmark. Its purpose is to help compare model behavior across representative task types and to inform routing strategy design.

## Main Fields

Typical fields include:

- `case_id`: unique case identifier
- `task_type`: one of `qa`, `summary`, `structured_extraction`, `rewrite`
- `difficulty`: relative complexity label
- `scenario`: scenario tag for the case
- `expected_format`: expected output format such as free text or JSON
- `priority_metric`: what the case prioritizes, such as quality or stability

## Why These Labels Matter

- `task_type` helps evaluate capability differences by workload category
- `difficulty` helps avoid overfitting to only easy prompts
- `scenario` helps keep the dataset grounded in platform and product use cases
- `expected_format` matters for format-sensitive tasks such as extraction
- `priority_metric` helps connect offline evaluation to online routing decisions

## Intended Use

Use this dataset with `eval_runner_v2.py` to:

- compare model outputs offline
- analyze quality / format / latency tradeoffs
- support initial routing rules
- produce sample evaluation reports for review
