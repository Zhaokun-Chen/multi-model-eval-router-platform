from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"

LOCAL_QWEN_AWQ_PATH = os.getenv("LOCAL_QWEN_AWQ_PATH", "").strip()

ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4").strip()
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "").strip()
ZHIPU_MODEL_NAME = os.getenv("ZHIPU_MODEL_NAME", "glm-4.7-flash").strip()

QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").strip()
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "").strip()
QWEN_MODEL_NAME = os.getenv("QWEN_MODEL_NAME", "qwen3.6-plus").strip()

MODEL_CONFIGS: list[dict] = []

if LOCAL_QWEN_AWQ_PATH:
    MODEL_CONFIGS.append(
        {
            "id": "qwen_local_awq",
            "label": "Qwen2.5-7B-AWQ Local",
            "provider_type": "local_qwen",
            "model_path": LOCAL_QWEN_AWQ_PATH,
            "quality_hint": 8.3,
            "latency_hint": 7.2,
            "cost_hint": 9.8,
            "stability_hint": 8.0,
            "recommended_tasks": ["qa", "structured_extraction", "rewrite"],
        }
    )

if ZHIPU_API_KEY:
    MODEL_CONFIGS.append(
        {
            "id": "zhipu_glm_flash",
            "label": f"Zhipu {ZHIPU_MODEL_NAME}",
            "provider_type": "openai_compat",
            "base_url": ZHIPU_BASE_URL,
            "api_key": ZHIPU_API_KEY,
            "model_name": ZHIPU_MODEL_NAME,
            "cost_per_1k_tokens": 0.0,
            "quality_hint": 8.9,
            "latency_hint": 7.5,
            "cost_hint": 9.2,
            "stability_hint": 8.6,
            "recommended_tasks": ["summary", "rewrite", "qa"],
            "debug_dir": str(REPORT_DIR),
            "max_retries": 2,
            "backoff_seconds": 2.0,
        }
    )

if QWEN_API_KEY:
    MODEL_CONFIGS.append(
        {
            "id": "aliyun_qwen36_plus",
            "label": f"DashScope {QWEN_MODEL_NAME}",
            "provider_type": "openai_compat",
            "base_url": QWEN_BASE_URL,
            "api_key": QWEN_API_KEY,
            "model_name": QWEN_MODEL_NAME,
            "cost_per_1k_tokens": 0.0,
            "quality_hint": 9.2,
            "latency_hint": 7.1,
            "cost_hint": 8.8,
            "stability_hint": 8.8,
            "recommended_tasks": ["summary", "qa", "rewrite"],
            "debug_dir": str(REPORT_DIR),
            "max_retries": 2,
            "backoff_seconds": 2.0,
        }
    )

SYSTEM_PROMPTS = {
    "qa": "You are a precise QA assistant. Give a direct and structured answer.",
    "summary": "You are a summarization assistant. Focus on concise key points.",
    "structured_extraction": "You must output valid JSON only. Do not add explanations or markdown fences.",
    "rewrite": "You are a rewriting assistant. Preserve meaning while improving clarity and professionalism.",
}

ROUTING_WEIGHT_PRESETS = {
    "balanced": {"quality": 0.4, "latency": 0.2, "cost": 0.2, "stability": 0.2},
    "quality": {"quality": 0.65, "latency": 0.1, "cost": 0.05, "stability": 0.2},
    "latency": {"quality": 0.2, "latency": 0.5, "cost": 0.15, "stability": 0.15},
    "cost": {"quality": 0.2, "latency": 0.15, "cost": 0.5, "stability": 0.15},
}
