from __future__ import annotations

from typing import Any


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_model_name(value: Any) -> str:
    return str(value or "").strip()


def normalize_gemini_model_name(value: Any) -> str:
    normalized = normalize_model_name(value)
    if normalized.lower().startswith("models/"):
        return normalized[7:].strip()
    return normalized


def is_image_generation_model(model_name: Any) -> bool:
    normalized = normalize_model_name(model_name).lower()
    return "image-preview" in normalized


def _display_name_to_friendly(display_name: str, provider: str) -> str:
    """将 modelDisplayName 转换为友好模型名，如 'Claude Sonnet 4.6' → 'claude-sonnet-4-6'。"""
    name = display_name.strip().lower().replace(" ", "-")
    if provider == "claude":
        # Claude 模型版本号中的点改为连字符：4.6 → 4-6
        name = name.replace(".", "-")
    return name


def resolve_model_name(name: str, catalog: list[dict[str, Any]]) -> str:
    """将友好名称或内部代码解析为实际发送给上游的 modelName。

    若 name 匹配某条目的 friendlyName，返回对应 modelName（内部代码）；
    否则原样返回（调用方传入的已经是内部代码或其他合法值）。
    """
    for item in catalog:
        if item.get("friendlyName") == name:
            return str(item.get("modelName") or name)
    return name


def extract_model_catalog(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if not isinstance(data, list):
        return []

    catalog: list[dict[str, Any]] = []
    for provider_item in data:
        if not isinstance(provider_item, dict):
            continue
        provider = str(provider_item.get("provider") or "").strip().lower()
        provider_display_name = str(
            provider_item.get("providerDisplayName") or provider
        ).strip()
        model_list = provider_item.get("modelList")
        if not isinstance(model_list, list):
            continue

        for model_item in model_list:
            if not isinstance(model_item, dict):
                continue
            model_name = str(model_item.get("modelName") or "").strip()
            if not model_name:
                continue
            model_display_name = str(
                model_item.get("modelDisplayName") or model_name
            )
            catalog.append(
                {
                    "provider": provider,
                    "providerDisplayName": provider_display_name,
                    "modelName": model_name,
                    "modelDisplayName": model_display_name,
                    "friendlyName": _display_name_to_friendly(model_display_name, provider),
                    "group": str(model_item.get("group") or "").strip(),
                    "multimodal": bool(model_item.get("multimodal", False)),
                    "visible": bool(model_item.get("visible", False)),
                    "thinkLevel": model_item.get("thinkLevel"),
                    "contextWindow": _as_int(model_item.get("contextWindow"), 0),
                    "isDefault": bool(model_item.get("isDefault", False)),
                    "tenant": model_item.get("tenant"),
                    "iaiTag": model_item.get("iaiTag"),
                    "empId": model_item.get("empId"),
                    "priceApiType": model_item.get("priceApiType"),
                    "reasoningEfforts": model_item.get("reasoningEfforts"),
                    "defaultReasoningEffort": model_item.get("defaultReasoningEffort"),
                }
            )

    catalog.sort(
        key=lambda item: (
            str(item.get("provider") or ""),
            0 if bool(item.get("visible")) else 1,
            str(item.get("friendlyName") or item.get("modelName") or ""),
        )
    )
    return catalog


def list_model_names(
    catalog: list[dict[str, Any]],
    *,
    provider: str | None = None,
) -> set[str]:
    """返回目录中所有可用的模型名称，包含友好名称和内部代码两种形式。"""
    provider_key = str(provider or "").strip().lower()
    names: set[str] = set()
    for item in catalog:
        if provider_key and str(item.get("provider") or "").strip().lower() != provider_key:
            continue
        model_name = str(item.get("modelName") or "").strip()
        if model_name:
            names.add(model_name)
        friendly = str(item.get("friendlyName") or "").strip()
        if friendly:
            names.add(friendly)
    return names


def list_proxy_model_names(catalog: list[dict[str, Any]]) -> set[str]:
    """返回可作为代理目标的模型名称（排除图片生成模型），包含友好名称和内部代码。"""
    names: set[str] = set()
    for item in catalog:
        model_name = normalize_model_name(item.get("modelName"))
        if not model_name or is_image_generation_model(model_name):
            continue
        names.add(model_name)
        friendly = str(item.get("friendlyName") or "").strip()
        if friendly:
            names.add(friendly)
    return names


def build_gemini_model_payload_from_catalog(
    catalog: list[dict[str, Any]],
    model_name: str,
) -> dict[str, Any] | None:
    normalized_target = normalize_gemini_model_name(model_name)
    if not normalized_target:
        return None

    for item in catalog:
        if str(item.get("provider") or "").strip().lower() != "gemini":
            continue
        candidate_name = normalize_gemini_model_name(item.get("modelName"))
        friendly_name = str(item.get("friendlyName") or "").strip()
        # 同时支持内部代码和友好名称匹配
        if candidate_name != normalized_target and friendly_name != normalized_target:
            continue
        context_window = _as_int(item.get("contextWindow"), 0)
        output_limit = 8192 if is_image_generation_model(candidate_name) else 16384
        exposed_name = friendly_name or candidate_name
        return {
            "name": f"models/{exposed_name}",
            "baseModelId": exposed_name,
            "displayName": str(item.get("modelDisplayName") or candidate_name),
            "description": f"{str(item.get('providerDisplayName') or 'Gemini')} 动态模型",
            "inputTokenLimit": context_window or 1_000_000,
            "outputTokenLimit": output_limit,
            "supportedGenerationMethods": [
                "generateContent",
                "streamGenerateContent",
            ],
            "multimodal": bool(item.get("multimodal", False)),
            "visible": bool(item.get("visible", False)),
            "group": str(item.get("group") or ""),
            "isDefault": bool(item.get("isDefault", False)),
        }
    return None


def build_openai_models_payload_from_catalog(
    catalog: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": str(item.get("friendlyName") or item.get("modelName") or ""),
                "object": "model",
                "owned_by": str(item.get("provider") or "unknown"),
                "display_name": str(item.get("modelDisplayName") or ""),
                "provider_display_name": str(item.get("providerDisplayName") or ""),
                "group": str(item.get("group") or ""),
                "multimodal": bool(item.get("multimodal", False)),
                "visible": bool(item.get("visible", False)),
                "context_window": _as_int(item.get("contextWindow"), 0),
                "is_default": bool(item.get("isDefault", False)),
            }
            for item in catalog
            if normalize_model_name(item.get("modelName"))
            and not is_image_generation_model(item.get("modelName"))
        ],
    }


def build_gemini_models_payload_from_catalog(
    catalog: list[dict[str, Any]],
) -> dict[str, Any]:
    models: list[dict[str, Any]] = []
    for item in catalog:
        if str(item.get("provider") or "").strip().lower() != "gemini":
            continue
        model_payload = build_gemini_model_payload_from_catalog(
            [item],
            str(item.get("modelName") or ""),
        )
        if model_payload:
            models.append(model_payload)
    return {"models": models}
