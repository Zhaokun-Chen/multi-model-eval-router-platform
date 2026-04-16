# Results Summary

This repository includes a sample metrics snapshot from a 50-case evaluation run across three models.

## Overall Metrics

| Model | Attempts | Successes | Avg Score | Avg Latency (ms) | Success Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `qwen_local_awq` | 50 | 50 | 0.748 | 8439.1 | 1.00 |
| `zhipu_glm_flash` | 50 | 37 | 0.782 | 13207.1 | 0.74 |
| `aliyun_qwen36_plus` | 50 | 50 | 0.869 | 20558.7 | 1.00 |

## What These Results Suggest

- `qwen3.6-plus` delivered the highest average score in the sample run, making it a strong candidate for quality-sensitive generation tasks.
- `Qwen2.5-7B-AWQ` had the lowest average latency and perfect success rate in the sample run, which makes it attractive for cost-sensitive and stability-sensitive paths.
- `GLM-4.7-Flash` landed between the two on quality and latency, but its success rate was lower in this run, which highlights why fallback and retry matter in platform design.

## Task-Level Observation

The sample run reinforced a practical routing pattern:

- use stronger remote models for quality-oriented `rewrite` and complex generation
- favor the local model for lower-cost and structure-sensitive tasks
- use a balanced remote model when quality and speed both matter

## Important Caveat

These numbers are sample outputs from one environment and one evaluation run. They should be interpreted as:

- evidence for MVP routing logic
- a product-facing evaluation snapshot

They should not be interpreted as a universal benchmark across all hardware, providers, prompts, or future model versions.

## Raw Sample Artifact

See [reports/sample_metrics_summary.json](../reports/sample_metrics_summary.json).
