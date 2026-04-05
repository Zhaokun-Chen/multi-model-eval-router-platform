from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GenerationResult:
    model_id: str
    model_label: str
    content: str
    latency_ms: int
    estimated_cost: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalCase:
    case_id: str
    task_type: str
    difficulty: str
    scenario: str
    expected_format: str
    priority_metric: str
    prompt: str
    expected_keywords: list[str]
    banned_keywords: list[str]
    notes: str = ""


@dataclass
class ModelScore:
    model_id: str
    model_label: str
    quality_score: float
    latency_score: float
    cost_score: float
    stability_score: float
    recommended_tasks: list[str]
    source: str = "hint"
