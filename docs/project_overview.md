# Project Overview

## Positioning

This project is an MVP for AI platform / MaaS scenarios.

It is not meant to be a general chatbot demo. The core goal is to verify a product and platform question:

`How can a platform evaluate multiple models consistently and route each task to a model that better matches quality, latency, cost, and stability requirements?`

## Problem Statement

When a platform only exposes one model, teams usually run into at least one of these problems:

- high-quality requests become too expensive
- low-latency requests do not get fast enough responses
- structured extraction tasks fail because format stability is weak
- model selection becomes experience-driven instead of evidence-driven

This project addresses that by combining:

- unified model access
- scenario-based offline evaluation
- lightweight routing logic
- fallback and retry / backoff

## Models Used

The public version is configured around three model roles:

- `Qwen2.5-7B-AWQ`: local, lower-cost, more controllable
- `GLM-4.7-Flash`: remote, balanced between quality and latency
- `qwen3.6-plus`: remote, higher-quality generation

The implementation is environment-variable driven, so the same architecture can be reused with other local or remote models.

## Supported Task Types

- `qa`: analysis-heavy question answering
- `summary`: compression and information distillation
- `structured_extraction`: structured output with format constraints
- `rewrite`: rewriting and higher-quality generation

## Evaluation Approach

The project includes a labeled dataset with:

- task type labels
- difficulty labels
- scenario labels
- expected output format
- priority metric

The V2 evaluator produces lightweight product-facing scores instead of academic benchmark scores. It combines:

- keyword score
- format score
- length penalty
- banned keyword penalty
- latency

This makes it easier to answer platform decisions such as:

- which model is more suitable for structured extraction
- whether a higher-quality model is worth the latency tradeoff
- whether a low-cost local model can cover enough of the workload

## Routing Strategy

The router currently supports:

- `balanced`
- `quality`
- `latency`
- `cost`

The current design is:

`rule-first routing + score-based fallback`

That means the system starts from routing rules informed by offline evaluation, then uses model characteristics and fallback logic to pick a practical model for the request.

## What This Repository Demonstrates

- model access abstraction
- product-oriented evaluation design
- routing logic grounded in data instead of intuition only
- basic stability governance for remote providers
- explainable output in a user-facing demo

## Current Boundaries

- task type is selected by the user in the current MVP
- routing is not yet fully automatic from raw prompt classification
- observability is still lightweight
- the included reports are sample outputs, not a production monitoring system

## Best Use Cases For This Repo

- interview portfolio for AI platform / AI product roles
- a starting point for multi-model routing demos
- a reference for product-facing LLM evaluation design
- a portfolio artifact for AI competitions or internship applications
