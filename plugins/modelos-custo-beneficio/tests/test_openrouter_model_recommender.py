from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PLUGIN_ROOT / "skills/modelos-custo-beneficio/scripts/openrouter_model_recommender.py"
FIXTURE_PATH = PLUGIN_ROOT / "tests/fixtures/openrouter-benchmarks-intelligence.json"


def load_module():
    spec = importlib.util.spec_from_file_location("openrouter_model_recommender_test", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class IntelligenceBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_only_finite_unique_scores_strictly_above_default_are_eligible(self):
        index, meta, benchmark_counts = self.module.index_openrouter_intelligence(self.fixture)
        models = [
            {"id": "example/eligible"},
            {"id": "example/threshold"},
            {"id": "example/below"},
            {"id": "example/invalid"},
            {"id": "example/duplicate"},
            {"id": "example/missing"},
        ]

        eligible, filter_counts = self.module.filter_models_by_intelligence(models, index, 35.0)

        self.assertEqual([model["id"] for model in eligible], ["example/eligible"])
        self.assertEqual(index["example/eligible"], 35.1)
        self.assertIsNone(self.module.finite_float(True))
        self.assertIsNone(index["example/duplicate"])
        self.assertEqual(benchmark_counts["benchmark_invalid"], 1)
        self.assertEqual(benchmark_counts["benchmark_ambiguous"], 1)
        self.assertEqual(filter_counts["intelligence_below_or_equal"], 2)
        self.assertEqual(filter_counts["intelligence_missing"], 3)
        self.assertEqual(filter_counts["intelligence_eligible"], 1)
        self.assertEqual(meta["source"], "artificial-analysis")
        self.assertEqual(meta["as_of"], "2026-07-21T00:01:02.674Z")

    def test_dated_permaslug_matches_undated_openrouter_model_id(self):
        index, _, counts = self.module.index_openrouter_intelligence(
            {"data": [{"model_permaslug": "google/gemini-3.5-flash-20260519", "intelligence_index": 36.1}]}
        )

        eligible, filter_counts = self.module.filter_models_by_intelligence(
            [{"id": "google/gemini-3.5-flash"}], index, 35.0
        )

        self.assertEqual(index["google/gemini-3.5-flash-20260519"], 36.1)
        self.assertEqual(index[self.module.benchmark_fallback_index_key("google/gemini-3.5-flash")], 36.1)
        self.assertEqual(self.module.intelligence_score_for_model("google/gemini-3.5-flash", index), 36.1)
        self.assertEqual([model["id"] for model in eligible], ["google/gemini-3.5-flash"])
        self.assertEqual(counts["benchmark_ambiguous"], 0)
        self.assertEqual(filter_counts["intelligence_eligible"], 1)

    def test_exact_match_wins_without_collapsing_gpt_families(self):
        index, _, _ = self.module.index_openrouter_intelligence({"data": [
            {"model_permaslug": "openai/gpt-4.1-2025-04-14", "intelligence_index": 50.0},
            {"model_permaslug": "openai/gpt-4.1", "intelligence_index": 36.0},
        ]})
        eligible, counts = self.module.filter_models_by_intelligence(
            [{"id": "openai/gpt-4.1"}, {"id": "openai/gpt-4o"}], index, 35.0
        )
        self.assertEqual(index["openai/gpt-4.1"], 36.0)
        self.assertEqual([model["id"] for model in eligible], ["openai/gpt-4.1"])
        self.assertEqual(counts["intelligence_missing"], 1)

    def test_ambiguous_dated_scores_do_not_choose_a_fallback(self):
        index, _, counts = self.module.index_openrouter_intelligence({"data": [
            {"model_permaslug": "example/model-2025-04-14", "intelligence_index": 40.0},
            {"model_permaslug": "example/model-2025-05-01", "intelligence_index": 41.0},
        ]})
        eligible, filter_counts = self.module.filter_models_by_intelligence([{"id": "example/model:free"}], index, 35.0)
        self.assertIsNone(index[self.module.benchmark_fallback_index_key("example/model")])
        self.assertEqual(counts["benchmark_ambiguous"], 1)
        self.assertEqual(eligible, [])
        self.assertEqual(filter_counts["intelligence_missing"], 1)

    def test_cli_default_and_requirements_json_override(self):
        parser = self.module.build_parser()
        defaults = parser.parse_args(["--eval-language", "pt-BR"])
        self.module.apply_requirements_json(defaults)
        self.assertEqual(defaults.min_intelligence, 35.0)

        overridden = parser.parse_args(
            [
                "--requirements-json",
                '{"eval_language":"pt-BR","min_intelligence":"36.2"}',
            ]
        )
        self.module.apply_requirements_json(overridden)
        self.assertEqual(overridden.min_intelligence, 36.2)

    def test_intelligence_gate_runs_before_candidate_limit(self):
        parser = self.module.build_parser()
        args = parser.parse_args(["--eval-language", "pt-BR", "--candidate-limit", "1", "--limit", "2"])
        models = [
            {
                "id": "example/below",
                "name": "Cheap but excluded",
                "created": 2,
                "context_length": 128000,
                "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
                "pricing": {"prompt": "0.0000001", "completion": "0.0000001"},
                "supported_parameters": ["tools", "structured_outputs"],
                "reasoning": {"supported_efforts": ["high"]},
            },
            {
                "id": "example/eligible",
                "name": "More expensive but eligible",
                "created": 1,
                "context_length": 128000,
                "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
                "pricing": {"prompt": "0.000002", "completion": "0.000002"},
                "supported_parameters": ["tools", "structured_outputs"],
                "reasoning": {"supported_efforts": ["high"]},
            },
        ]
        endpoint = {
            "name": "Example endpoint",
            "provider_name": "Example",
            "tag": "example/default",
            "context_length": 128000,
            "pricing": {"prompt": "0.000002", "completion": "0.000002"},
            "supported_parameters": ["tools", "structured_outputs"],
            "throughput_last_30m": {"p75": 70},
            "latency_last_30m": {"p50": 1.0, "p99": 1.5},
            "uptime_last_30m": 99,
        }
        benchmark = (
            {"example/below": 35.0, "example/eligible": 35.1},
            {"source": "artificial-analysis", "task_type": "intelligence", "version": "v1"},
            {"benchmark_rows": 2, "benchmark_invalid": 0, "benchmark_ambiguous": 0},
        )
        with (
            patch.object(self.module, "list_openrouter_models", return_value=models),
            patch.object(self.module, "fetch_openrouter_intelligence", return_value=benchmark),
            patch.object(self.module, "fetch_openrouter_endpoints", return_value=[endpoint]) as endpoints,
        ):
            records, counts, _ = self.module.run(args)

        self.assertEqual([record["base_model_id"] for record in records], ["example/eligible"])
        self.assertEqual(counts["intelligence_eligible"], 1)
        self.assertEqual(endpoints.call_args.args[0], "example/eligible")

    def test_default_latency_slo_requires_p50_under_two_minutes_and_p99_under_three(self):
        args = self.module.build_parser().parse_args(["--eval-language", "pt-BR"])
        model = {
            "id": "example/model", "context_length": 128000,
            "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            "pricing": {"prompt": "0.000001", "completion": "0.000001"},
            "supported_parameters": ["tools", "structured_outputs"],
            "reasoning": {"supported_efforts": ["high"]},
        }
        endpoint = {
            "name": "Endpoint", "provider_name": "Example", "tag": "default", "context_length": 128000,
            "pricing": model["pricing"], "supported_parameters": model["supported_parameters"],
            "throughput_last_30m": {"p75": 70}, "uptime_last_30m": 99,
        }
        endpoints = [
            endpoint | {"latency_last_30m": {"p50": 119_999, "p99": 179_999}},
            endpoint | {"latency_last_30m": {"p50": 120_000, "p99": 179_999}},
            endpoint | {"latency_last_30m": {"p50": 119_999, "p99": 180_000}},
            endpoint | {"latency_last_30m": {"p50": 119_999}},
            endpoint | {"latency_last_30m": {"median": 119_999, "p99": 179_999}},
            endpoint | {"latency_last_30m": {"p50": "invalid", "p99": 179_999}},
        ]

        records = self.module.endpoint_records(model, endpoints, args, 36.0)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["latency_ms"], 119_999.0)

    def test_json_and_markdown_expose_intelligence_diagnostics(self):
        args = self.module.build_parser().parse_args(["--eval-language", "pt-BR", "--format", "json"])
        record = {
            "score": 1.23,
            "model_name": "Eligible",
            "base_model_id": "example/eligible",
            "variant": None,
            "endpoint": "example/default",
            "reasoning_effort": "high",
            "throughput_tps": 70.0,
            "throughput_metric": "p75",
            "price_per_1m": 1.0,
            "intelligence_index": 35.1,
        }
        counts = {
            "models": 2,
            "model_prefilter": 2,
            "intelligence_eligible": 1,
            "candidate_pool": 1,
            "endpoint_records": 1,
            "benchmark_rows": 2,
            "benchmark_invalid": 0,
            "benchmark_ambiguous": 0,
            "intelligence_missing": 0,
            "intelligence_below_or_equal": 1,
        }
        benchmark_meta = {
            "source": "artificial-analysis",
            "task_type": "intelligence",
            "as_of": "2026-07-21T00:01:02Z",
            "version": "v1",
        }
        markdown = self.module.render_markdown([record], args, counts, benchmark_meta)
        self.assertIn("intelligence > 35.0", markdown)
        self.assertIn("artificial-analysis", markdown)
        self.assertIn("35.1", markdown)

        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(self.module, "require_openrouter_api_key", return_value="test-key"),
            patch.object(self.module, "run", return_value=([record, record], counts, benchmark_meta)),
            patch("sys.stdout", stdout),
            patch("sys.stderr", stderr),
        ):
            self.assertEqual(self.module.main(["--eval-language", "pt-BR", "--format", "json"]), 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["benchmark"]["source"], "artificial-analysis")
        self.assertEqual(payload["diagnostics"]["intelligence_eligible"], 1)
        self.assertEqual(payload["candidates"][0]["intelligence_index"], 35.1)

    def test_missing_openrouter_key_is_a_clear_configuration_error(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=False):
            with self.assertRaises(self.module.ConfigurationError):
                self.module.require_openrouter_api_key()


if __name__ == "__main__":
    unittest.main()
