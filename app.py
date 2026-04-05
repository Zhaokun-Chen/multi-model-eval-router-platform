from __future__ import annotations

import json
import os
from pathlib import Path

os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

import gradio as gr

from config import MODEL_CONFIGS, REPORT_DIR, SYSTEM_PROMPTS
from providers_v2 import build_provider
from router import ModelRouter

router = ModelRouter(MODEL_CONFIGS)
providers = {config["id"]: build_provider(config) for config in MODEL_CONFIGS}


def clean_answer_for_display(content: str) -> str:
    lines = [line.rstrip() for line in content.splitlines()]
    filtered: list[str] = []
    skip_prefixes = (
        "分析用户请求",
        "拆解主题",
        "确定比较维度",
        "角色：",
        "要求：",
        "主题：",
    )
    for line in lines:
        stripped = line.strip()
        if not stripped:
            filtered.append("")
            continue
        if any(stripped.startswith(prefix) for prefix in skip_prefixes):
            continue
        filtered.append(line)

    cleaned = "\n".join(filtered).strip()
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned


def latest_report_preview() -> str:
    if not REPORT_DIR.exists():
        return "暂无评测报告。"

    metrics_path = REPORT_DIR / "metrics_summary.json"
    if metrics_path.exists():
        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        lines = [f"指标摘要更新时间：{payload.get('generated_at', '-')}"]
        per_model = payload.get("per_model", {})
        if per_model:
            lines.append("")
            lines.append("模型稳定性与效果：")
            for model_id, metrics in per_model.items():
                lines.append(
                    f"- {model_id}: 成功率 {metrics.get('success_rate', '-')}, 平均分 {metrics.get('avg_score', '-')}, 平均时延 {metrics.get('avg_latency_ms', '-')} ms"
                )
        best_by_task = payload.get("best_model_by_task", {})
        if best_by_task:
            lines.append("")
            lines.append("各任务当前最优模型：")
            for task_type, metrics in best_by_task.items():
                lines.append(
                    f"- {task_type}: {metrics.get('model_id', '-')} (best_score {metrics.get('best_score', '-')})"
                )
        return "\n".join(lines)

    reports = sorted(REPORT_DIR.glob("eval_report_*.json"), reverse=True)
    if not reports:
        return "暂无评测报告。"

    latest = reports[0]
    payload = json.loads(latest.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return f"最近一次评测：{latest.name}"

    meta = payload.get("meta", {})
    summary = payload.get("summary", {})
    per_model = summary.get("per_model", {})
    per_model_task = summary.get("per_model_task", {})

    lines = [f"最近一次评测：{latest.name}"]
    if meta:
        lines.append(
            f"样本数 {meta.get('num_cases', '-') } | 模型数 {meta.get('num_models', '-')} | 任务类型 {', '.join(meta.get('task_types', []))}"
        )

    if per_model:
        lines.append("")
        lines.append("模型总体表现：")
        for model_id, metrics in per_model.items():
            lines.append(
                f"- {model_id}: 平均分 {metrics.get('avg_score', '-')}, 平均时延 {metrics.get('avg_latency_ms', '-')} ms"
            )

    if per_model_task:
        lines.append("")
        lines.append("任务维度最优模型：")
        task_best: dict[str, tuple[str, float]] = {}
        for model_id, task_map in per_model_task.items():
            for task_type, metrics in task_map.items():
                score = metrics.get("avg_score", 0)
                current = task_best.get(task_type)
                if current is None or score > current[1]:
                    task_best[task_type] = (model_id, score)
        for task_type, (model_id, score) in sorted(task_best.items()):
            lines.append(f"- {task_type}: {model_id} (平均分 {score})")

    return "\n".join(lines)


def route_and_generate(task_type: str, strategy: str, prompt: str) -> tuple[str, str]:
    print(f"[App] 收到请求 task_type={task_type}, strategy={strategy}", flush=True)
    decision = router.route(task_type, strategy)
    ranked = decision["ranked"]

    selected_result = None
    selected_item = None
    fallback_notes: list[str] = []

    for idx, candidate in enumerate(ranked):
        provider = providers[candidate["model_id"]]
        try:
            print(f"[App] 尝试模型: {candidate['model_label']}", flush=True)
            result = provider.generate(prompt=prompt, system_prompt=SYSTEM_PROMPTS[task_type], max_new_tokens=256)
            selected_result = result
            selected_item = candidate
            if idx > 0:
                fallback_notes.append(f"最终命中 fallback 模型: {candidate['model_label']}")
            break
        except Exception as exc:
            note = f"{candidate['model_label']} 调用失败，触发 fallback：{exc}"
            print(f"[App] {note}", flush=True)
            fallback_notes.append(note)
            continue

    if selected_result is None or selected_item is None:
        failure_text = "\n".join(fallback_notes) if fallback_notes else "所有候选模型均调用失败。"
        return decision["explanation"], failure_text

    decision_text = (
        f"路由策略：{strategy}\n"
        f"任务类型：{task_type}\n"
        f"命中模型：{selected_item['model_label']}\n"
        f"综合得分：{selected_item['final_score']}\n"
        f"解释：{decision['explanation']}\n"
    )
    if fallback_notes:
        decision_text += "\nFallback 记录：\n" + "\n".join(fallback_notes) + "\n"

    decision_text += "\n候选排序：\n"
    for item in ranked:
        decision_text += (
            f"- {item['model_label']} | 总分 {item['final_score']} | "
            f"质量 {item['quality_score']} | 延迟 {item['latency_score']} | "
            f"成本 {item['cost_score']} | 稳定性 {item['stability_score']}\n"
        )

    answer_body = clean_answer_for_display(selected_result.content)
    answer_text = (
        f"模型：{selected_result.model_label}\n"
        f"延迟：{selected_result.latency_ms} ms\n"
        f"预估成本：{selected_result.estimated_cost}\n\n"
        f"{answer_body}"
    )
    return decision_text, answer_text


demo = gr.Interface(
    fn=route_and_generate,
    inputs=[
        gr.Dropdown(
            choices=["qa", "summary", "structured_extraction", "rewrite"],
            value="qa",
            label="任务类型",
        ),
        gr.Dropdown(
            choices=["balanced", "quality", "latency", "cost"],
            value="balanced",
            label="路由策略",
        ),
        gr.Textbox(
            lines=8,
            label="输入 Prompt",
            value="请比较 AWQ 量化和 FP16 部署在本地推理场景中的差异，并给出适用建议。",
        ),
    ],
    outputs=[
        gr.Textbox(label="路由决策"),
        gr.Textbox(label="模型输出"),
    ],
    title="多模型评测与路由平台",
    description="一个面向 AI 平台 / MaaS 产品方向的 MVP：展示多模型接入、评测结果沉淀与路由决策逻辑。",
    article=(
        "当前默认接入本地 Qwen2.5-AWQ 以及远端 OpenAI 兼容模型。"
        f"\n\n{latest_report_preview()}"
    ),
    allow_flagging="never",
)


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7861,
        share=False,
        inbrowser=False,
    )
