# Multi-Model Evaluation and Routing Platform

An MVP for AI platform / MaaS scenarios.  
This project demonstrates:

- unified access to local and remote LLMs
- offline evaluation with a labeled dataset
- task-aware routing and fallback
- basic stability governance with retry / backoff
- a simple Gradio demo for routing decisions and model outputs

## Models Used

This public version is designed to work with:

- Local model: `Qwen2.5-7B-AWQ`
- Remote model: `GLM-4.7-Flash` via OpenAI-compatible API
- Remote model: `qwen3.6-plus` via DashScope OpenAI-compatible API

You can also replace these with your own local or remote models by editing environment variables.

## Features

- `50` labeled evaluation samples
- task coverage:
  - `qa`
  - `summary`
  - `structured_extraction`
  - `rewrite`
- metadata labels:
  - `difficulty`
  - `scenario`
  - `expected_format`
  - `priority_metric`
- V2 scoring:
  - keyword score
  - format score
  - length penalty
  - banned keyword penalty
- routing:
  - `balanced`
  - `quality`
  - `latency`
  - `cost`
- retry / backoff / fallback support for remote models

## Project Structure

```text
model_router_platform_public/
├─ app.py
├─ config.py
├─ eval_runner_v2.py
├─ models.py
├─ providers_v2.py
├─ router.py
├─ requirements.txt
├─ .env.example
├─ data/
│  └─ eval_dataset.json
└─ reports/
   └─ .gitkeep
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` and set the values you need.

Key options:

- `LOCAL_QWEN_AWQ_PATH`
- `ZHIPU_API_KEY`
- `ZHIPU_BASE_URL`
- `ZHIPU_MODEL_NAME`
- `QWEN_API_KEY`
- `QWEN_BASE_URL`
- `QWEN_MODEL_NAME`

## Run Demo

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:7861
```

## Run Evaluation

```bash
python eval_runner_v2.py
```

Reports will be written to:

```text
reports/
```

## Notes

- This public version does **not** include model weights.
- This public version does **not** include private API keys.
- For local model usage, set `LOCAL_QWEN_AWQ_PATH` to your own model directory.

## Positioning

This repository is intended to showcase product-facing work at the intersection of:

- AI platform / MaaS
- model evaluation
- model routing
- model serving
- LLM product design
