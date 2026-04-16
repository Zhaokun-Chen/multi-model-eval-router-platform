# OpenClaw Pitch

## One-Line Summary

A multi-model evaluation and routing MVP for AI platform scenarios, showing how local and remote LLMs can be evaluated, selected, and routed based on task type, quality, latency, cost, and stability.

## Why This Project Fits OpenClaw

OpenClaw emphasizes practical AI application building. This project aligns well with that direction because it focuses on:

- turning model capability into platform capability
- making model selection explainable instead of manual
- combining task understanding, routing, and fallback into a usable workflow
- building a product-facing AI system rather than a single-model chat demo

Although this repository is not a Feishu-native workflow app yet, its core logic is directly transferable to OpenClaw-style agent and workflow scenarios, such as:

- selecting different models for meeting summaries, extraction, and rewriting
- routing tasks based on business priority and latency requirements
- applying fallback when remote calls fail
- supporting structured outputs for downstream workflow automation

## Problem Solved

In many AI products, teams connect one model and stop there. That creates several issues:

- quality-heavy tasks and cost-sensitive tasks are treated the same way
- structured extraction and free-form generation are sent to the same model path
- model selection depends too much on intuition
- provider instability is not handled systematically

This project solves that by building a minimal but complete loop:

1. define representative task types
2. evaluate multiple models on the same dataset
3. compare quality, latency, and stability
4. encode routing logic
5. expose the decision in a demo interface

## What I Built

- unified access to one local and two remote LLMs
- a labeled evaluation dataset with 50 cases
- an offline evaluation runner
- a lightweight scoring framework
- routing strategies for quality, latency, cost, and balanced scenarios
- retry / backoff and fallback-oriented stability handling
- a Gradio demo that shows routing decisions and outputs

## AI Role In The Project

AI is not just a text-generation endpoint in this project. It plays three roles:

- execution layer: different models generate answers, summaries, extractions, and rewrites
- evaluation object: models are compared through a scenario-based scoring framework
- routing target: the platform decides which model should handle which request

In other words, the project is about operationalizing AI capability instead of only consuming it.

## Quantifiable Outputs

Sample outputs from one evaluation run:

- `50` labeled evaluation cases
- `4` task types: `qa`, `summary`, `structured_extraction`, `rewrite`
- `3` model roles: local, balanced remote, quality remote
- local model success rate: `1.00`
- highest average quality score in sample run: `0.869`
- structured extraction path supported stable structured outputs in the sample setup

## Suggested Competition Framing

If used in competition materials, this repo can be framed as:

`A core capability module for future AI workflow / agent systems, where different tasks should be routed to different models rather than handled by a single default model.`

## Recommended Repo Links To Share

- Main overview: [README.md](../README.md)
- Project explanation: [project_overview.md](project_overview.md)
- Demo flow: [demo_script.md](demo_script.md)
- Result snapshot: [results.md](results.md)
