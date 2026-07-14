#!/usr/bin/env python3
# Recomendador de modelos OpenRouter para a skill modelos-custo-beneficio.
# Stdlib only. Sem dependencias. Porque dependencias para consultar uma API JSON seriam uma extravagancia imperial.
from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1").rstrip("/")
USER_AGENT = "modelos-custo-beneficio-skill/0.1 (+https://github.com/cadugevaerd)"


@dataclass
class ArgsView:
    limit: int
    candidate_limit: int
    min_throughput: float | None
    allow_unknown_throughput: bool
    input_modalities: str
    output_modalities: str
    tool_calls: bool | None
    structured_outputs: bool | None
    min_context: int
    max_cost_per_1m: float | None
    input_weight: float
    output_weight: float
    latest_only: bool
    include_free: bool
    provider: list[str]
    exclude_provider: list[str]
    model_contains: list[str]
    exclude_model_contains: list[str]
    use_artificial_analysis: bool
    workers: int
    fmt: str
    debug: bool


def csv_set(value: str | list[str] | None) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        raw = []
        for item in value:
            raw.extend(str(item).split(","))
    else:
        raw = str(value).split(",")
    result = {x.strip().lower() for x in raw if x.strip()}
    if "any" in result or "*" in result:
        return set()
    return result


def as_bool(value: Any) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "sim", "s"}:
        return True
    if text in {"0", "false", "no", "n", "nao", "não"}:
        return False
    raise ValueError(f"Valor booleano invalido: {value!r}")


def price_token_to_1m(value: Any) -> float:
    if value is None or value == "":
        return math.inf
    try:
        raw = float(value)
        if raw < 0:
            # Routers/agregadores podem publicar -1 como sentinel de preco dinamico.
            # Isso nao e preco; e uma armadilha com cracha.
            return math.inf
        return raw * 1_000_000
    except (TypeError, ValueError):
        return math.inf


def weighted_cost_per_1m(pricing: dict[str, Any], input_weight: float, output_weight: float) -> float:
    prompt = price_token_to_1m(pricing.get("prompt"))
    completion = price_token_to_1m(pricing.get("completion"))
    if math.isinf(prompt) and math.isinf(completion):
        return math.inf
    if math.isinf(prompt):
        prompt = completion
    if math.isinf(completion):
        completion = prompt
    return (prompt * input_weight) + (completion * output_weight)


def metric_p50(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        for key in ("p50", "median", "avg"):
            if key in value and value[key] is not None:
                try:
                    return float(value[key])
                except (TypeError, ValueError):
                    return None
    return None


def metric_p75_or_p50(value: Any) -> tuple[float | None, str | None]:
    """Return OpenRouter throughput with the required p75 -> p50 fallback."""
    if value is None:
        return None, None
    if isinstance(value, (int, float)):
        return float(value), "p50 fallback"
    if not isinstance(value, dict):
        return None, None
    for key, label in (("p75", "p75"), ("p50", "p50 fallback"), ("median", "p50 fallback"), ("avg", "p50 fallback")):
        if value.get(key) is None:
            continue
        try:
            return float(value[key]), label
        except (TypeError, ValueError):
            return None, None
    return None, None


def params_set(obj: dict[str, Any]) -> set[str]:
    return {str(x) for x in (obj.get("supported_parameters") or [])}


def supports_tools(params: set[str]) -> bool:
    return "tools" in params


def supports_structured(params: set[str]) -> bool:
    # response_format sozinho pode ser JSON mode; structured_outputs indica JSON Schema estrito no OpenRouter.
    return "structured_outputs" in params


EFFORT_LEVELS = ("xhigh", "high", "medium", "low", "minimal")


def reasoning_capability(model: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize OpenRouter reasoning metadata without guessing a parameter name."""
    raw = model.get("reasoning") or {}
    if not isinstance(raw, dict):
        return None
    supported = {
        str(value).strip().lower()
        for value in (raw.get("supported_efforts") or [])
        if str(value).strip().lower() in EFFORT_LEVELS
    }
    if supported:
        ordered = [level for level in EFFORT_LEVELS if level in supported]
        return {
            "mode": "effort",
            "supported_efforts": ordered,
            "initial": ordered[0],
            "mandatory": bool(raw.get("mandatory")),
        }
    if raw.get("supports_max_tokens") is True:
        return {
            "mode": "max_tokens",
            "supported_efforts": [],
            "initial": "xhigh",
            "mandatory": bool(raw.get("mandatory")),
        }
    return None


def routed_model_id(model_id: str, tool_calls: bool | None) -> tuple[str, str]:
    variant = ":exacto" if tool_calls is True else ":nitro"
    return f"{strip_router_variant(model_id)}{variant}", variant


def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def strip_router_variant(model_id: str) -> str:
    # :free / :thinking etc. sao variantes de roteamento, nao familia do modelo.
    return model_id.split(":", 1)[0]


def family_key(model_id: str) -> str:
    base = strip_router_variant(model_id).lstrip("~").lower()
    if "/" in base:
        provider, slug = base.split("/", 1)
    else:
        provider, slug = "", base

    slug = re.sub(r"[-_](20\d{2}[-_]?\d{2}[-_]?\d{2}|20\d{6})", "", slug)
    slug = re.sub(r"[-_](latest|preview|beta|alpha|experimental|exp|stable)$", "", slug)

    if provider == "anthropic" and slug.startswith("claude"):
        for tier in ("haiku", "sonnet", "opus"):
            if tier in slug:
                return f"{provider}/claude-{tier}"
        return f"{provider}/claude"

    if provider == "google" and slug.startswith("gemini"):
        if "flash-lite" in slug or "flashlite" in slug:
            tier = "flash-lite"
        elif "flash" in slug:
            tier = "flash"
        elif "pro" in slug:
            tier = "pro"
        else:
            tier = "core"
        return f"{provider}/gemini-{tier}"

    if provider == "openai":
        if slug.startswith("gpt-"):
            major = re.match(r"gpt-(\d+)", slug)
            tier = ""
            if "nano" in slug:
                tier = "-nano"
            elif "mini" in slug:
                tier = "-mini"
            return f"{provider}/gpt-{major.group(1) if major else 'x'}{tier}"
        om = re.match(r"(o\d+)", slug)
        if om:
            tier = "-mini" if "mini" in slug else ""
            return f"{provider}/{om.group(1)}{tier}"

    if provider == "x-ai" and slug.startswith("grok"):
        if "fast" in slug:
            tier = "fast"
        elif "mini" in slug:
            tier = "mini"
        else:
            tier = "core"
        return f"{provider}/grok-{tier}"

    tokens = slug.split("-")
    keep: list[str] = []
    for token in tokens:
        if not token:
            continue
        if re.fullmatch(r"v?\d+(\.\d+)*", token):
            continue
        if re.fullmatch(r"\d{6,8}", token):
            continue
        keep.append(token)
    return f"{provider}/{'-'.join(keep[:4]) if keep else slug}"


def created_ts(model: dict[str, Any]) -> int:
    try:
        return int(model.get("created") or 0)
    except (TypeError, ValueError):
        return 0


def created_date(ts: int | None) -> str:
    if not ts:
        return "?"
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return str(ts)


def is_free_model(model: dict[str, Any]) -> bool:
    mid = str(model.get("id", ""))
    pricing = model.get("pricing") or {}
    prompt = price_token_to_1m(pricing.get("prompt"))
    completion = price_token_to_1m(pricing.get("completion"))
    return mid.endswith(":free") or (prompt == 0 and completion == 0)


def fetch_json(url: str, *, openrouter: bool = True, api_key: str | None = None) -> dict[str, Any]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if api_key:
        headers["Authorization" if openrouter else "x-api-key"] = f"Bearer {api_key}" if openrouter else api_key
    req = Request(url, headers=headers)
    with urlopen(req, timeout=35) as response:
        return json.loads(response.read().decode("utf-8"))


def list_openrouter_models() -> list[dict[str, Any]]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    data = fetch_json(f"{OPENROUTER_BASE_URL}/models", api_key=api_key)
    return list(data.get("data") or [])


def fetch_openrouter_endpoints(model_id: str, model: dict[str, Any]) -> list[dict[str, Any]]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    encoded = quote(model_id, safe="/:~")
    url = f"{OPENROUTER_BASE_URL}/models/{encoded}/endpoints"
    try:
        data = fetch_json(url, api_key=api_key)
        endpoints = list((data.get("data") or {}).get("endpoints") or [])
        if endpoints:
            return endpoints
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        pass
    # Fallback agregado: ainda permite ranking por preco/capacidade se o endpoint detalhado falhar.
    top_provider = model.get("top_provider") or {}
    return [
        {
            "name": "OpenRouter aggregate",
            "provider_name": "OpenRouter",
            "tag": "aggregate",
            "context_length": top_provider.get("context_length") or model.get("context_length"),
            "max_completion_tokens": top_provider.get("max_completion_tokens"),
            "pricing": model.get("pricing") or {},
            "supported_parameters": model.get("supported_parameters") or [],
            "throughput_last_30m": None,
            "latency_last_30m": None,
            "uptime_last_30m": None,
            "uptime_last_5m": None,
            "uptime_last_1d": None,
            "status": None,
        }
    ]


def fetch_artificial_analysis() -> dict[str, dict[str, Any]]:
    key = os.getenv("AA_API_KEY") or os.getenv("ARTIFICIAL_ANALYSIS_API_KEY")
    if not key:
        return {}
    url = "https://artificialanalysis.ai/api/v2/language/models"
    try:
        data = fetch_json(url, openrouter=False, api_key=key)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for item in data.get("data") or []:
        names = [str(item.get("name") or ""), str(item.get("slug") or "")]
        creator = ((item.get("model_creator") or {}).get("name") or "")
        if creator:
            names.append(f"{creator} {item.get('name') or ''}")
        for name in names:
            key_norm = normalize_text(name)
            if key_norm:
                index[key_norm] = item
    return index


def match_aa(model: dict[str, Any], aa_index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if not aa_index:
        return None
    candidates = [
        normalize_text(str(model.get("name") or "")),
        normalize_text(strip_router_variant(str(model.get("id") or "")).split("/", 1)[-1]),
    ]
    for cand in candidates:
        if cand in aa_index:
            return aa_index[cand]
    # Fuzzy leve: evita puxar Selenium para isto. Ainda bem.
    for key, value in aa_index.items():
        for cand in candidates:
            if cand and key and (cand in key or key in cand):
                return value
    return None


def apply_latest_filter(models: list[dict[str, Any]], include_free: bool) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for model in models:
        if not include_free and is_free_model(model):
            continue
        key = family_key(str(model.get("id") or ""))
        current = latest.get(key)
        if current is None:
            latest[key] = model
            continue
        candidate_tuple = (created_ts(model), not str(model.get("id", "")).startswith("~"))
        current_tuple = (created_ts(current), not str(current.get("id", "")).startswith("~"))
        if candidate_tuple > current_tuple:
            latest[key] = model
    return list(latest.values())


def model_prefilter(models: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    input_req = csv_set(args.input_modalities)
    output_req = csv_set(args.output_modalities)
    providers = {x.lower() for x in args.provider}
    exclude_providers = {x.lower() for x in args.exclude_provider}
    include_terms = [x.lower() for x in args.model_contains]
    exclude_terms = [x.lower() for x in args.exclude_model_contains]
    result: list[dict[str, Any]] = []

    for model in models:
        mid = str(model.get("id") or "")
        # Routers/agregadores sao uteis em runtime, mas esta skill ranqueia
        # modelos concretos. Caso contrario openrouter/auto ganha com preco
        # sentinel/dinamico e estraga o ranking.
        if mid.startswith("openrouter/") or mid.startswith("~"):
            continue
        provider = mid.split("/", 1)[0].lower() if "/" in mid else ""
        haystack = f"{mid} {model.get('name') or ''}".lower()
        if providers and provider not in providers:
            continue
        if provider in exclude_providers:
            continue
        if include_terms and not all(term in haystack for term in include_terms):
            continue
        if exclude_terms and any(term in haystack for term in exclude_terms):
            continue
        if not args.include_free and is_free_model(model):
            continue
        if reasoning_capability(model) is None:
            continue

        arch = model.get("architecture") or {}
        inputs = {str(x).lower() for x in (arch.get("input_modalities") or [])}
        outputs = {str(x).lower() for x in (arch.get("output_modalities") or [])}
        if input_req and not input_req.issubset(inputs):
            continue
        if output_req and not output_req.issubset(outputs):
            continue

        model_params = params_set(model)
        if args.tool_calls is True and not supports_tools(model_params):
            continue
        if args.structured_outputs is True and not supports_structured(model_params):
            continue
        if args.structured_outputs is False and supports_structured(model_params):
            continue
        if args.min_context and int(model.get("context_length") or 0) < args.min_context:
            continue
        result.append(model)
    return result


def endpoint_records(model: dict[str, Any], endpoints: list[dict[str, Any]], args: argparse.Namespace, aa_item: dict[str, Any] | None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    model_params = params_set(model)
    reasoning = reasoning_capability(model)
    if reasoning is None:
        return records
    arch = model.get("architecture") or {}
    aa_eval = (aa_item or {}).get("evaluations") or {}

    quality = aa_eval.get("artificial_analysis_coding_index") or aa_eval.get("artificial_analysis_intelligence_index")
    try:
        quality = float(quality) if quality is not None else None
    except (TypeError, ValueError):
        quality = None

    for ep in endpoints:
        ep_params = params_set(ep) or model_params
        if args.tool_calls is True and not supports_tools(ep_params):
            continue
        if args.structured_outputs is True and not supports_structured(ep_params):
            continue
        if args.structured_outputs is False and supports_structured(ep_params):
            continue

        context = int(ep.get("context_length") or model.get("context_length") or 0)
        if args.min_context and context < args.min_context:
            continue

        pricing = ep.get("pricing") or model.get("pricing") or {}
        cost = weighted_cost_per_1m(pricing, args.input_weight, args.output_weight)
        if math.isinf(cost):
            continue
        if not args.include_free and cost == 0:
            continue
        if args.max_cost_per_1m is not None and cost > args.max_cost_per_1m:
            continue

        throughput, throughput_percentile = metric_p75_or_p50(ep.get("throughput_last_30m"))
        throughput_source = f"OpenRouter {throughput_percentile}" if throughput_percentile else None
        # Throughput is a hard OpenRouter endpoint gate. Artificial Analysis can enrich
        # ranking quality, but cannot substitute provider-specific routing evidence.
        if throughput is None or throughput < args.min_throughput:
            continue

        uptime = ep.get("uptime_last_30m")
        if uptime is None:
            uptime = ep.get("uptime_last_5m")
        if uptime is None:
            uptime = ep.get("uptime_last_1d")
        try:
            uptime_float = float(uptime) if uptime is not None else 97.0
        except (TypeError, ValueError):
            uptime_float = 97.0

        latency = metric_p50(ep.get("latency_last_30m"))
        prompt_cost = price_token_to_1m(pricing.get("prompt"))
        completion_cost = price_token_to_1m(pricing.get("completion"))
        throughput_for_score = throughput
        context_factor = 1.0 + min(math.log10(max(context, 1)) / 12.0, 0.5)
        uptime_factor = max(min(uptime_float, 100.0), 0.0) / 100.0
        quality_factor = (quality / 50.0) if quality else 1.0
        effective_cost = max(cost, 0.001)
        score = (throughput_for_score * uptime_factor * context_factor * quality_factor) / effective_cost

        records.append(
            {
                "model_id": routed_model_id(str(model.get("id") or ""), args.tool_calls)[0],
                "base_model_id": model.get("id"),
                "routing_variant": routed_model_id(str(model.get("id") or ""), args.tool_calls)[1],
                "model_name": model.get("name"),
                "reasoning": reasoning,
                "family_key": family_key(str(model.get("id") or "")),
                "created": created_ts(model),
                "created_date": created_date(created_ts(model)),
                "endpoint": ep.get("name"),
                "provider": ep.get("provider_name"),
                "tag": ep.get("tag"),
                "input_modalities": arch.get("input_modalities") or [],
                "output_modalities": arch.get("output_modalities") or [],
                "tool_calls": supports_tools(ep_params),
                "structured_outputs": supports_structured(ep_params),
                "context_length": context,
                "max_completion_tokens": ep.get("max_completion_tokens"),
                "throughput_tps": throughput,
                "throughput_source": throughput_source if throughput is not None else None,
                "latency_s": latency,
                "uptime_percent": uptime_float,
                "prompt_usd_per_1m": prompt_cost,
                "completion_usd_per_1m": completion_cost,
                "weighted_usd_per_1m": cost,
                "quality_index": quality,
                "score": score,
            }
        )
    return records


def dedupe_best_endpoint(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for rec in records:
        mid = str(rec["model_id"])
        current = best.get(mid)
        if current is None or (rec["score"], -rec["weighted_usd_per_1m"]) > (current["score"], -current["weighted_usd_per_1m"]):
            best[mid] = rec
    return list(best.values())


def rank_records(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    records = dedupe_best_endpoint(records)
    return sorted(records, key=lambda r: (r["score"], -r["weighted_usd_per_1m"], r["created"]), reverse=True)[:limit]


def apply_requirements_json(args: argparse.Namespace) -> None:
    if not args.requirements_json:
        return
    try:
        data = json.loads(args.requirements_json)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"requirements-json invalido: {exc}") from exc
    aliases = {
        "throughput_min": "min_throughput",
        "min_throughput": "min_throughput",
        "input_types": "input_modalities",
        "inputs": "input_modalities",
        "input_modalities": "input_modalities",
        "output_modalities": "output_modalities",
        "tool_calls": "tool_calls",
        "structured_outputs": "structured_outputs",
        "saida_estruturada": "structured_outputs",
        "min_context": "min_context",
        "context_min": "min_context",
        "limit": "limit",
        "max_cost_per_1m": "max_cost_per_1m",
    }
    for key, dest in aliases.items():
        if key not in data:
            continue
        value = data[key]
        if dest in {"tool_calls", "structured_outputs"}:
            value = as_bool(value)
        if dest in {"input_modalities", "output_modalities"} and isinstance(value, list):
            value = ",".join(map(str, value))
        setattr(args, dest, value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Acha modelos OpenRouter latest com melhor custo-beneficio para requisitos de capacidade.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--requirements-json", help="JSON com requisitos: throughput_min, input_types, tool_calls, structured_outputs, etc.")
    parser.add_argument("--limit", type=int, default=5, help="Quantidade de candidatos (2 a 5)")
    parser.add_argument("--candidate-limit", type=int, default=140, help="Maximo de modelos prefiltrados para consultar endpoints")
    parser.add_argument("--min-throughput", type=float, default=60.0, help="Throughput minimo hard em tokens/s: p75 OpenRouter, p50 como fallback")
    parser.add_argument("--input", "--input-modalities", dest="input_modalities", default="text", help="Modalidades exigidas: text,image,file,audio,video ou any")
    parser.add_argument("--output", "--output-modalities", dest="output_modalities", default="text", help="Modalidades de saida exigidas ou any")
    parser.add_argument("--tool-calls", dest="tool_calls", action="store_true", default=None, help="Exigir suporte a Tool Calls")
    parser.add_argument("--no-tool-calls", dest="tool_calls", action="store_false", help="Seleção para geração textual; aplica a variante :nitro sem excluir modelos capazes de tools")
    parser.add_argument("--structured-outputs", dest="structured_outputs", action="store_true", default=None, help="Exigir structured_outputs / JSON Schema")
    parser.add_argument("--no-structured-outputs", dest="structured_outputs", action="store_false", help="Exigir modelos sem structured_outputs")
    parser.add_argument("--min-context", type=int, default=0, help="Context window minimo em tokens")
    parser.add_argument("--max-cost-per-1m", type=float, default=None, help="Custo ponderado maximo por 1M tokens")
    parser.add_argument("--input-weight", type=float, default=0.7, help="Peso de tokens de input no custo ponderado")
    parser.add_argument("--output-weight", type=float, default=0.3, help="Peso de tokens de output no custo ponderado")
    parser.add_argument("--latest-only", dest="latest_only", action="store_true", default=True, help="Manter apenas a versao mais nova por familia heuristica")
    parser.add_argument("--no-latest-only", dest="latest_only", action="store_false", help="Permitir modelos antigos da mesma familia")
    parser.add_argument("--include-free", action="store_true", help="Incluir variantes/modelos gratis; por padrao sao excluidos para evitar ranking enganoso")
    parser.add_argument("--provider", action="append", default=[], help="Filtrar por provider do model_id, ex: openai, anthropic, google")
    parser.add_argument("--exclude-provider", action="append", default=[], help="Excluir provider do model_id")
    parser.add_argument("--model-contains", action="append", default=[], help="Termo obrigatorio no id/nome do modelo")
    parser.add_argument("--exclude-model-contains", action="append", default=[], help="Termo proibido no id/nome do modelo")
    parser.add_argument("--use-artificial-analysis", action="store_true", help="Mesclar throughput/qualidade da Artificial Analysis se AA_API_KEY existir")
    parser.add_argument("--workers", type=int, default=16, help="Concorrencia para consultar endpoints OpenRouter")
    parser.add_argument("--format", dest="fmt", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--debug", action="store_true", help="Imprimir contadores de diagnostico em stderr")
    parser.add_argument("--self-test", action="store_true", help="Executa testes internos sem rede")
    return parser


def fmt_money(value: float) -> str:
    if math.isinf(value):
        return "?"
    return f"${value:.3f}" if value < 10 else f"${value:.2f}"


def fmt_num(value: Any, suffix: str = "") -> str:
    if value is None:
        return "?"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number >= 1000:
        return f"{number:,.0f}{suffix}"
    return f"{number:.1f}{suffix}"


def pipe_safe(value: Any) -> str:
    return str(value).replace("|", "\\|")


def render_markdown(records: list[dict[str, Any]], args: argparse.Namespace, counts: dict[str, int], aa_used: bool) -> str:
    filters = []
    if args.min_throughput is not None:
        filters.append(f"throughput >= {args.min_throughput} t/s")
    filters.append(f"input={args.input_modalities}")
    filters.append(f"output={args.output_modalities}")
    if args.tool_calls is not None:
        filters.append(f"tool_calls={args.tool_calls}")
    if args.structured_outputs is not None:
        filters.append(f"structured_outputs={args.structured_outputs}")
    if args.min_context:
        filters.append(f"context >= {args.min_context}")

    lines = [
        f"# Candidatos para Model Engineering Eval ({len(records)} de {args.limit})",
        "",
        f"Filtros hard: `{'; '.join(filters)}`; reasoning controlável; não gratuito.",
        "",
        "| # | Modelo para o Eval | Provider / endpoint | Reasoning inicial | Throughput |",
        "|---:|---|---|---|---:|",
    ]
    for idx, rec in enumerate(records, 1):
        throughput = fmt_num(rec.get("throughput_tps"), " t/s")
        if rec.get("throughput_source"):
            throughput = f"{throughput} ({rec['throughput_source']})"
        reasoning = rec.get("reasoning") or {}
        if reasoning.get("mode") == "effort":
            reasoning_text = f"effort: `{reasoning.get('initial')}`"
        else:
            reasoning_text = "max_tokens: mapa local começa em `xhigh`"
        lines.append(
            "| {idx} | `{model}` | {endpoint}<br>`{tag}` | {reasoning} | {throughput} |".format(
                idx=idx,
                model=pipe_safe(rec.get("model_id")),
                endpoint=pipe_safe(rec.get("provider") or rec.get("endpoint")),
                tag=pipe_safe(rec.get("tag")),
                reasoning=reasoning_text,
                throughput=throughput,
            )
        )
    lines.extend(
        [
            "",
            "## Guia para testar no Model Engineering Eval do repositório",
            "1. **Pré-requisito:** use a suíte de Eval já definida pelo repositório; esta skill não cria nem executa o runner.",
            "2. Execute cada slug acima com a configuração inicial indicada. Para `max_tokens`, aplique o mapa local de percentuais/budgets para `xhigh`.",
            "3. Uma configuração passa somente com `pass_rate >= 95%` (ou o limiar local explicitamente configurado). Registre payload de reasoning, provider efetivo, custo real, latência e throughput.",
            "4. Para cada sobrevivente, desça um nível de cada vez: `xhigh → high → medium → low → minimal`; pule níveis não suportados. Pare para aquele modelo na primeira falha, mas continue mesmo que reste apenas um sobrevivente.",
            "5. Retenha o menor reasoning aprovado por modelo. Com pelo menos dois modelos distintos aprovados, o Eval define `principal` e `fallback` por: menor custo total observado → menor latência → maior throughput.",
            "6. Revalide no prazo configurado (padrão: 30 dias) ou após mudança de modelo, provider, preço, reasoning ou suíte de Eval. Aplique runtime manualmente; esta skill não altera produção.",
        ]
    )
    return "\n".join(lines)


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, int], bool]:
    models = list_openrouter_models()
    counts = {"models": len(models)}
    if args.latest_only:
        models = apply_latest_filter(models, include_free=args.include_free)
    counts["latest"] = len(models)
    models = model_prefilter(models, args)
    counts["prefiltered"] = len(models)

    # Consulta endpoints dos candidatos mais promissores primeiro: baratos, recentes e com contexto razoavel.
    def rough_key(model: dict[str, Any]) -> tuple[float, int, int]:
        cost = weighted_cost_per_1m(model.get("pricing") or {}, args.input_weight, args.output_weight)
        if math.isinf(cost):
            cost = 10**9
        return (cost, -created_ts(model), -int(model.get("context_length") or 0))

    models = sorted(models, key=rough_key)[: max(args.candidate_limit, args.limit)]

    aa_index: dict[str, dict[str, Any]] = {}
    if args.use_artificial_analysis:
        aa_index = fetch_artificial_analysis()
    aa_used = bool(aa_index)

    records: list[dict[str, Any]] = []
    with futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        future_map = {executor.submit(fetch_openrouter_endpoints, str(model.get("id")), model): model for model in models}
        for future in futures.as_completed(future_map):
            model = future_map[future]
            try:
                endpoints = future.result()
            except Exception:  # noqa: BLE001 - relatorio deve sobreviver a endpoint quebrado
                endpoints = []
            aa_item = match_aa(model, aa_index)
            records.extend(endpoint_records(model, endpoints, args, aa_item))
    counts["records"] = len(records)
    ranked = rank_records(records, args.limit)
    return ranked, counts, aa_used


def run_self_test() -> None:
    parser = build_parser()
    args = parser.parse_args([
        "--input", "text,image",
        "--tool-calls",
        "--structured-outputs",
        "--min-throughput", "60",
        "--limit", "1",
    ])
    args.requirements_json = None
    apply_requirements_json(args)
    models = [
        {
            "id": "openai/gpt-5",
            "name": "GPT-5",
            "created": 10,
            "context_length": 128000,
            "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
            "pricing": {"prompt": "0.000002", "completion": "0.000004"},
            "supported_parameters": ["tools", "structured_outputs"],
        },
        {
            "id": "openai/gpt-5.1",
            "name": "GPT-5.1",
            "created": 20,
            "context_length": 400000,
            "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
            "pricing": {"prompt": "0.000001", "completion": "0.000003"},
            "supported_parameters": ["tools", "tool_choice", "structured_outputs"],
            "reasoning": {"supported_efforts": ["xhigh", "high", "medium", "low", "minimal"]},
        },
        {
            "id": "example/bad-model",
            "name": "Bad",
            "created": 30,
            "context_length": 8000,
            "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            "pricing": {"prompt": "0.000001", "completion": "0.000001"},
            "supported_parameters": [],
        },
    ]
    latest = apply_latest_filter(models, include_free=False)
    latest_ids = {m["id"] for m in latest}
    assert "openai/gpt-5.1" in latest_ids and "openai/gpt-5" not in latest_ids, latest_ids
    filtered = model_prefilter(latest, args)
    assert [m["id"] for m in filtered] == ["openai/gpt-5.1"], filtered
    endpoints = [
        {
            "name": "OpenAI | gpt-5.1",
            "provider_name": "OpenAI",
            "tag": "openai/default",
            "context_length": 400000,
            "pricing": {"prompt": "0.000001", "completion": "0.000003"},
            "supported_parameters": ["tools", "tool_choice", "structured_outputs"],
            "throughput_last_30m": {"p75": 72.0},
            "uptime_last_30m": 99.9,
        }
    ]
    records = endpoint_records(filtered[0], endpoints, args, None)
    ranked = rank_records(records, 1)
    assert len(ranked) == 1 and ranked[0]["throughput_tps"] == 72.0, ranked
    assert ranked[0]["model_id"] == "openai/gpt-5.1:exacto", ranked
    assert routed_model_id("openai/gpt-5.1:exacto", False) == ("openai/gpt-5.1:nitro", ":nitro")
    assert routed_model_id("openai/gpt-5.1", None) == ("openai/gpt-5.1:nitro", ":nitro")
    assert ranked[0]["reasoning"]["initial"] == "xhigh", ranked
    assert metric_p75_or_p50({"p75": 61, "p50": 99}) == (61.0, "p75")
    assert metric_p75_or_p50({"p50": 61}) == (61.0, "p50 fallback")
    max_tokens_reasoning = reasoning_capability({"reasoning": {"supports_max_tokens": True}})
    assert max_tokens_reasoning and max_tokens_reasoning["mode"] == "max_tokens"
    print("self-test ok")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test:
        run_self_test()
        return 0
    apply_requirements_json(args)
    if not 2 <= args.limit <= 5:
        parser.error("--limit deve estar entre 2 e 5")
    if args.min_throughput < 60:
        parser.error("--min-throughput nao pode ser menor que 60 t/s")
    if args.input_weight < 0 or args.output_weight < 0 or (args.input_weight + args.output_weight) <= 0:
        parser.error("Pesos de input/output invalidos")
    total_weight = args.input_weight + args.output_weight
    args.input_weight = args.input_weight / total_weight
    args.output_weight = args.output_weight / total_weight

    try:
        records, counts, aa_used = run(args)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Erro ao consultar fonte de modelos: {exc}", file=sys.stderr)
        return 1

    if args.debug:
        print(json.dumps(counts, ensure_ascii=False), file=sys.stderr)

    if len(records) < 2:
        msg = {
            "error": "Menos de dois candidatos atendem aos filtros hard.",
            "hint": "São obrigatórios: reasoning controlável, modelo não gratuito e throughput OpenRouter p75 (ou p50 fallback) >= 60 t/s.",
        }
        print(json.dumps(msg, ensure_ascii=False, indent=2) if args.fmt == "json" else f"# Seleção insuficiente\n\n{msg['hint']}")
        return 2

    evaluation_guide = [
        "Use a suíte de Model Engineering Eval já definida pelo repositório; esta skill não cria nem executa o runner.",
        "Comece no reasoning indicado; em max_tokens, aplique o mapa local de xhigh.",
        "Uma configuração passa com pass_rate >= 95% (ou limiar local explicitamente configurado).",
        "Desça xhigh → high → medium → low → minimal; pule níveis não suportados e pare no primeiro nível que falhar por modelo.",
        "Com pelo menos dois modelos distintos aprovados, escolha principal e fallback por custo total, latência e throughput.",
        "Revalide em até 30 dias, ou após alterações de modelo, provider, preço, reasoning ou suíte de Eval; runtime é manual.",
    ]
    if args.fmt == "json":
        print(json.dumps({"candidates": records, "eval_guide": evaluation_guide}, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(records, args, counts, aa_used))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
