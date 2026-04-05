from __future__ import annotations

from typing import Any

from config import ROUTING_WEIGHT_PRESETS
from models import ModelScore


class ModelRouter:
    def __init__(self, model_configs: list[dict[str, Any]]):
        self.model_configs = model_configs
        self.model_scores = self._build_scores()

    def _build_scores(self) -> list[ModelScore]:
        scores: list[ModelScore] = []
        for config in self.model_configs:
            scores.append(
                ModelScore(
                    model_id=config["id"],
                    model_label=config["label"],
                    quality_score=config["quality_hint"],
                    latency_score=config["latency_hint"],
                    cost_score=config["cost_hint"],
                    stability_score=config["stability_hint"],
                    recommended_tasks=config.get("recommended_tasks", []),
                )
            )
        return scores

    def _policy_bonus(self, model_id: str, task_type: str, strategy: str) -> float:
        # 第一版规则路由：先用评测结论做方向性加权，再由分数排序兜底。
        if model_id == "aliyun_qwen36_plus":
            if strategy == "quality" and task_type in {"qa", "summary", "rewrite"}:
                return 1.0
            if task_type == "structured_extraction" and strategy == "quality":
                return 0.4
            return 0.0

        if model_id == "zhipu_glm_flash":
            if strategy == "balanced" and task_type in {"qa", "summary"}:
                return 0.7
            if strategy == "quality" and task_type in {"qa", "summary"}:
                return 0.2
            return 0.0

        if model_id == "qwen_local_awq":
            if strategy in {"cost", "latency"}:
                return 0.8
            if task_type == "structured_extraction":
                return 0.7
            return 0.0

        return 0.0

    def rank_models(self, task_type: str, strategy: str) -> list[dict[str, Any]]:
        weights = ROUTING_WEIGHT_PRESETS[strategy]
        ranked = []
        for model_score in self.model_scores:
            task_bonus = 0.5 if task_type in model_score.recommended_tasks else 0.0
            policy_bonus = self._policy_bonus(model_score.model_id, task_type, strategy)
            final_score = (
                model_score.quality_score * weights["quality"]
                + model_score.latency_score * weights["latency"]
                + model_score.cost_score * weights["cost"]
                + model_score.stability_score * weights["stability"]
                + task_bonus
                + policy_bonus
            )
            ranked.append(
                {
                    "model_id": model_score.model_id,
                    "model_label": model_score.model_label,
                    "final_score": round(final_score, 3),
                    "quality_score": model_score.quality_score,
                    "latency_score": model_score.latency_score,
                    "cost_score": model_score.cost_score,
                    "stability_score": model_score.stability_score,
                    "task_bonus": task_bonus,
                    "policy_bonus": policy_bonus,
                }
            )
        return sorted(ranked, key=lambda item: item["final_score"], reverse=True)

    def _build_explanation(self, task_type: str, strategy: str, selected: dict[str, Any]) -> str:
        model_label = selected["model_label"]

        if strategy == "quality" and task_type in {"qa", "summary", "rewrite"}:
            return (
                f"当前任务为 {task_type}，策略为 {strategy}。"
                f"根据离线评测结果，高质量模式优先选择在复杂生成任务上表现更强的 {model_label}。"
            )

        if task_type == "structured_extraction" and strategy != "quality":
            return (
                f"当前任务为 {task_type}，策略为 {strategy}。"
                f"结构化抽取更看重格式稳定性与成本，因此优先选择 {model_label}。"
            )

        if strategy == "balanced" and task_type in {"qa", "summary"}:
            return (
                f"当前任务为 {task_type}，策略为 {strategy}。"
                f"平衡模式会综合质量、延迟与稳定性，优先选择综合表现更均衡的 {model_label}。"
            )

        if strategy in {"cost", "latency"}:
            return (
                f"当前任务为 {task_type}，策略为 {strategy}。"
                f"在成本或延迟优先场景下，平台会优先选择本地或更轻量的模型，本次命中 {model_label}。"
            )

        return (
            f"当前任务为 {task_type}，策略为 {strategy}。"
            f"系统综合质量、延迟、成本、稳定性以及任务适配性后，选择了 {model_label}。"
        )

    def route(self, task_type: str, strategy: str) -> dict[str, Any]:
        ranked = self.rank_models(task_type, strategy)
        selected = ranked[0]
        explanation = self._build_explanation(task_type, strategy, selected)
        return {"selected": selected, "ranked": ranked, "explanation": explanation}
