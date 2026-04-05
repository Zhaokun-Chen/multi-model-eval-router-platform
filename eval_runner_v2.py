from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from config import DATA_DIR, MODEL_CONFIGS, REPORT_DIR, SYSTEM_PROMPTS
from models import EvalCase
from providers_v2 import build_provider


def load_eval_cases() -> list[EvalCase]:
    dataset_path = DATA_DIR / "eval_dataset.json"
    raw_cases = json.loads(dataset_path.read_text(encoding="utf-8-sig"))
    return [EvalCase(**case) for case in raw_cases]


def build_output_preview(content: str) -> str:
    preview = " ".join(content.split())
    return preview[:300]


def detect_bullet_lines(content: str) -> int:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    prefixes = ("-", "*", "•", "1.", "2.", "3.", "4.", "5.")
    return sum(1 for line in lines if line.startswith(prefixes))


def score_format(content: str, expected_format: str) -> tuple[float, str]:
    stripped = content.strip()

    if expected_format == "json":
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, (dict, list)):
                return 1.0, "json_parse_ok"
            return 0.6, "json_parse_non_container"
        except Exception:
            return 0.0, "json_parse_failed"

    if expected_format == "bullet":
        bullet_count = detect_bullet_lines(content)
        if bullet_count >= 3:
            return 1.0, "bullet_3plus"
        if bullet_count >= 1:
            return 0.5, "bullet_partial"
        return 0.0, "bullet_missing"

    if expected_format == "free_text":
        if len(stripped) >= 60:
            return 1.0, "free_text_sufficient"
        if len(stripped) >= 20:
            return 0.5, "free_text_short"
        return 0.0, "free_text_too_short"

    return 0.5, "format_unknown"


def length_penalty(content: str, task_type: str) -> tuple[float, str]:
    length = len(content.strip())

    if length == 0:
        return 0.25, "empty_output"

    if task_type == "summary" and length > 280:
        return 0.1, "summary_too_long"
    if task_type == "structured_extraction" and length > 500:
        return 0.15, "extraction_too_verbose"
    if task_type == "rewrite" and length < 30:
        return 0.1, "rewrite_too_short"

    return 0.0, "length_ok"


def score_output(
    content: str,
    expected_keywords: list[str],
    banned_keywords: list[str],
    expected_format: str,
    task_type: str,
) -> dict:
    lowered = content.lower()
    hit_count = sum(1 for keyword in expected_keywords if keyword.lower() in lowered)
    banned_hit_count = sum(1 for keyword in banned_keywords if keyword.lower() in lowered)

    keyword_score = hit_count / max(len(expected_keywords), 1)
    format_score, format_reason = score_format(content, expected_format)
    length_penalty_value, length_reason = length_penalty(content, task_type)
    banned_penalty = banned_hit_count * 0.15
    total_penalty = banned_penalty + length_penalty_value
    final_score = max(
        0.0,
        min(1.0, 0.65 * keyword_score + 0.35 * format_score - total_penalty),
    )
    return {
        "keyword_score": round(keyword_score, 3),
        "format_score": round(format_score, 3),
        "format_reason": format_reason,
        "banned_penalty": round(banned_penalty, 3),
        "length_penalty": round(length_penalty_value, 3),
        "length_reason": length_reason,
        "penalty": round(total_penalty, 3),
        "final_score": round(final_score, 3),
    }


def build_summary(results: list[dict]) -> dict:
    model_task_metrics: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    model_totals: dict[str, dict[str, float]] = defaultdict(dict)
    format_reason_counter: dict[str, Counter] = defaultdict(Counter)
    length_reason_counter: dict[str, Counter] = defaultdict(Counter)

    for result in results:
        if "error" in result:
            continue

        model_id = result["model_id"]
        task_type = result["task_type"]
        latency_ms = result["latency_ms"]
        final_score = result["score"]["final_score"]

        task_bucket = model_task_metrics[model_id].setdefault(
            task_type,
            {"count": 0, "avg_score": 0.0, "avg_latency_ms": 0.0},
        )
        task_bucket["count"] += 1
        task_bucket["avg_score"] += final_score
        task_bucket["avg_latency_ms"] += latency_ms

        total_bucket = model_totals.setdefault(
            model_id,
            {"count": 0, "avg_score": 0.0, "avg_latency_ms": 0.0},
        )
        total_bucket["count"] += 1
        total_bucket["avg_score"] += final_score
        total_bucket["avg_latency_ms"] += latency_ms
        format_reason_counter[model_id][result["score"]["format_reason"]] += 1
        length_reason_counter[model_id][result["score"]["length_reason"]] += 1

    for metrics in model_task_metrics.values():
        for bucket in metrics.values():
            count = max(bucket["count"], 1)
            bucket["avg_score"] = round(bucket["avg_score"] / count, 3)
            bucket["avg_latency_ms"] = round(bucket["avg_latency_ms"] / count, 1)

    for bucket in model_totals.values():
        count = max(bucket["count"], 1)
        bucket["avg_score"] = round(bucket["avg_score"] / count, 3)
        bucket["avg_latency_ms"] = round(bucket["avg_latency_ms"] / count, 1)

    return {
        "per_model": dict(model_totals),
        "per_model_task": {model_id: dict(task_map) for model_id, task_map in model_task_metrics.items()},
        "format_reasons": {model_id: dict(counter) for model_id, counter in format_reason_counter.items()},
        "length_reasons": {model_id: dict(counter) for model_id, counter in length_reason_counter.items()},
    }


def build_metrics_summary(results: list[dict]) -> dict:
    per_model: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "attempts": 0,
            "successes": 0,
            "errors": 0,
            "avg_latency_ms": 0.0,
            "avg_score": 0.0,
        }
    )
    task_best: dict[str, tuple[str, float]] = {}

    for result in results:
        model_id = result["model_id"]
        bucket = per_model[model_id]
        bucket["attempts"] += 1

        if "error" in result:
            bucket["errors"] += 1
            continue

        bucket["successes"] += 1
        bucket["avg_latency_ms"] += result["latency_ms"]
        bucket["avg_score"] += result["score"]["final_score"]

        task_type = result["task_type"]
        score = result["score"]["final_score"]
        current = task_best.get(task_type)
        if current is None or score > current[1]:
            task_best[task_type] = (model_id, score)

    for bucket in per_model.values():
        successes = max(int(bucket["successes"]), 1)
        bucket["success_rate"] = round(bucket["successes"] / max(int(bucket["attempts"]), 1), 3)
        if bucket["successes"] > 0:
            bucket["avg_latency_ms"] = round(bucket["avg_latency_ms"] / successes, 1)
            bucket["avg_score"] = round(bucket["avg_score"] / successes, 3)
        else:
            bucket["avg_latency_ms"] = None
            bucket["avg_score"] = None

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "per_model": dict(per_model),
        "best_model_by_task": {
            task_type: {"model_id": model_id, "best_score": score}
            for task_type, (model_id, score) in sorted(task_best.items())
        },
    }


def run_eval() -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_eval_cases()
    results = []

    for config in MODEL_CONFIGS:
        provider = build_provider(config)
        for case in cases:
            try:
                generation = provider.generate(
                    prompt=case.prompt,
                    system_prompt=SYSTEM_PROMPTS[case.task_type],
                    max_new_tokens=220,
                )
                score = score_output(
                    generation.content,
                    case.expected_keywords,
                    case.banned_keywords,
                    case.expected_format,
                    case.task_type,
                )
                results.append(
                    {
                        "case_id": case.case_id,
                        "task_type": case.task_type,
                        "difficulty": case.difficulty,
                        "scenario": case.scenario,
                        "expected_format": case.expected_format,
                        "priority_metric": case.priority_metric,
                        "model_id": generation.model_id,
                        "model_label": generation.model_label,
                        "latency_ms": generation.latency_ms,
                        "estimated_cost": generation.estimated_cost,
                        "score": score,
                        "output_preview": build_output_preview(generation.content),
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "case_id": case.case_id,
                        "task_type": case.task_type,
                        "difficulty": case.difficulty,
                        "scenario": case.scenario,
                        "expected_format": case.expected_format,
                        "priority_metric": case.priority_metric,
                        "model_id": config["id"],
                        "model_label": config["label"],
                        "error": str(exc),
                    }
                )

    report_payload = {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "num_cases": len(cases),
            "num_models": len(MODEL_CONFIGS),
            "task_types": sorted({case.task_type for case in cases}),
            "difficulties": sorted({case.difficulty for case in cases}),
            "scenarios": sorted({case.scenario for case in cases}),
        },
        "summary": build_summary(results),
        "results": results,
    }

    report_path = REPORT_DIR / f"eval_report_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    metrics_path = REPORT_DIR / "metrics_summary.json"
    metrics_path.write_text(
        json.dumps(build_metrics_summary(results), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report_path


if __name__ == "__main__":
    path = run_eval()
    print(f"评测完成，结果已写入：{path}")
