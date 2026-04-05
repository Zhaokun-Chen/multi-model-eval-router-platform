from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from typing import Any

import requests
from requests import HTTPError, RequestException

from models import GenerationResult


def clean_generation_text(content: str) -> str:
    cleaned = content.strip()
    noisy_prefixes = [
        "user",
        '"user"',
        "PARTICULAR",
        "PARTICULARLY",
        "oplayer",
        "iniz",
        "billig",
        "emodels",
        "Beste",
        "');",
        "*/",
    ]

    changed = True
    while changed and cleaned:
        changed = False
        for prefix in noisy_prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].lstrip(" \n\r\t:：\"'")
                changed = True

    return cleaned.strip()


def extract_json_like_text(content: str) -> str:
    stripped = content.strip()
    if not stripped:
        return stripped

    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
            stripped = "\n".join(lines[1:-1]).strip()
            if stripped.lower().startswith("json"):
                stripped = stripped[4:].lstrip()

    start_candidates = [idx for idx in (stripped.find("{"), stripped.find("[")) if idx != -1]
    if not start_candidates:
        return stripped

    start = min(start_candidates)
    opening = stripped[start]
    closing = "}" if opening == "{" else "]"
    end = stripped.rfind(closing)

    if end != -1 and end > start:
        candidate = stripped[start : end + 1].strip()
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            return candidate

    return stripped


def extract_openai_compatible_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""

    message = choices[0].get("message") or {}
    content = message.get("content", "")
    reasoning_content = message.get("reasoning_content", "")

    if isinstance(content, str):
        cleaned_content = clean_generation_text(content)
        if cleaned_content:
            return extract_json_like_text(cleaned_content)

    if isinstance(reasoning_content, str):
        cleaned_reasoning = clean_generation_text(reasoning_content)
        if cleaned_reasoning:
            return extract_json_like_text(cleaned_reasoning)

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                if isinstance(text, str):
                    parts.append(text)
        return extract_json_like_text(clean_generation_text("\n".join(parts)))

    return ""


class BaseProvider(ABC):
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.model_id = config["id"]
        self.model_label = config["label"]

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str, max_new_tokens: int = 256) -> GenerationResult:
        raise NotImplementedError


class LocalQwenProvider(BaseProvider):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self._tokenizer = None
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is not None and self._tokenizer is not None:
            return

        print(f"[LocalQwenProvider] 开始加载模型: {self.model_label}", flush=True)

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        model_path = self.config["model_path"]
        self._tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True,
            use_fast=False,
        )
        print(f"[LocalQwenProvider] tokenizer 加载完成: {self.model_label}", flush=True)
        self._model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        print(f"[LocalQwenProvider] model 加载完成: {self.model_label}", flush=True)

    def generate(self, prompt: str, system_prompt: str, max_new_tokens: int = 256) -> GenerationResult:
        self._ensure_loaded()
        print(f"[LocalQwenProvider] 开始生成回复: {self.model_label}", flush=True)
        started_at = time.perf_counter()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        text = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        model_inputs = self._tokenizer([text], return_tensors="pt", padding=True)
        model_inputs = {k: v.to(self._model.device) for k, v in model_inputs.items()}
        input_length = model_inputs["input_ids"].shape[1]

        outputs = self._model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.2,
            top_p=0.9,
            do_sample=True,
            pad_token_id=self._tokenizer.eos_token_id,
        )

        generated_ids = outputs[0][input_length:]
        content = self._tokenizer.decode(generated_ids, skip_special_tokens=True)
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        print(f"[LocalQwenProvider] 生成完成: {self.model_label}, latency={latency_ms}ms", flush=True)

        return GenerationResult(
            model_id=self.model_id,
            model_label=self.model_label,
            content=extract_json_like_text(clean_generation_text(content)),
            latency_ms=latency_ms,
            estimated_cost=0.0,
            metadata={"provider": "local_qwen"},
        )


class OpenAICompatibleProvider(BaseProvider):
    def generate(self, prompt: str, system_prompt: str, max_new_tokens: int = 256) -> GenerationResult:
        print(f"[OpenAICompatibleProvider] 开始调用远端模型: {self.model_label}", flush=True)
        base_url = self.config.get("base_url", "").rstrip("/")
        api_key = self.config.get("api_key", "")
        model_name = self.config["model_name"]
        max_retries = int(self.config.get("max_retries", 2))
        backoff_seconds = float(self.config.get("backoff_seconds", 2.0))

        if not base_url or not api_key:
            raise RuntimeError(f"{self.model_label} 未配置可用的远端接口。")

        payload: dict[str, Any] | None = None
        content = ""
        latency_ms = 0
        last_error: str | None = None

        for attempt in range(max_retries + 1):
            started_at = time.perf_counter()
            try:
                response = requests.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": max_new_tokens,
                        "temperature": 0.2,
                    },
                    timeout=120,
                )
                response.raise_for_status()
                payload = response.json()
                latency_ms = int((time.perf_counter() - started_at) * 1000)
                content = extract_openai_compatible_text(payload)
                break
            except HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                latency_ms = int((time.perf_counter() - started_at) * 1000)
                last_error = f"http_status={status_code}, detail={exc}"
                print(
                    f"[OpenAICompatibleProvider] 远端调用失败: {self.model_label}, attempt={attempt + 1}/{max_retries + 1}, latency={latency_ms}ms, {last_error}",
                    flush=True,
                )
                should_retry = status_code in {408, 409, 425, 429, 500, 502, 503, 504}
                if not should_retry or attempt == max_retries:
                    raise RuntimeError(f"{self.model_label} 调用失败: {last_error}") from exc
                sleep_s = backoff_seconds * (2**attempt)
                print(f"[OpenAICompatibleProvider] 准备重试: {self.model_label}, sleep={sleep_s:.1f}s", flush=True)
                time.sleep(sleep_s)
            except RequestException as exc:
                latency_ms = int((time.perf_counter() - started_at) * 1000)
                last_error = f"network_error={exc}"
                print(
                    f"[OpenAICompatibleProvider] 网络请求异常: {self.model_label}, attempt={attempt + 1}/{max_retries + 1}, latency={latency_ms}ms, {last_error}",
                    flush=True,
                )
                if attempt == max_retries:
                    raise RuntimeError(f"{self.model_label} 调用失败: {last_error}") from exc
                sleep_s = backoff_seconds * (2**attempt)
                print(f"[OpenAICompatibleProvider] 准备重试: {self.model_label}, sleep={sleep_s:.1f}s", flush=True)
                time.sleep(sleep_s)

        if payload is None:
            raise RuntimeError(f"{self.model_label} 未返回有效响应。")

        debug_dir = self.config.get("debug_dir", "")
        if debug_dir:
            debug_path = f"{debug_dir}\\last_openai_compat_payload.json"
            try:
                with open(debug_path, "w", encoding="utf-8") as fp:
                    json.dump(payload, fp, ensure_ascii=False, indent=2)
            except OSError:
                pass

        usage = payload.get("usage", {})
        total_tokens = usage.get("total_tokens", 0)
        estimated_cost = round(total_tokens / 1000 * self.config.get("cost_per_1k_tokens", 0.0), 4)
        print(
            f"[OpenAICompatibleProvider] 调用完成: {self.model_label}, latency={latency_ms}ms, content_len={len(content)}",
            flush=True,
        )

        return GenerationResult(
            model_id=self.model_id,
            model_label=self.model_label,
            content=content,
            latency_ms=latency_ms,
            estimated_cost=estimated_cost,
            metadata={
                "provider": "openai_compat",
                "usage": usage,
                "max_retries": max_retries,
                "last_error": last_error,
            },
        )


def build_provider(config: dict[str, Any]) -> BaseProvider:
    provider_type = config["provider_type"]
    if provider_type == "local_qwen":
        return LocalQwenProvider(config)
    if provider_type == "openai_compat":
        return OpenAICompatibleProvider(config)
    raise ValueError(f"未知 provider_type: {provider_type}")
