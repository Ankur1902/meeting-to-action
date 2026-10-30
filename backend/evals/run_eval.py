"""
Eval runner.

    python -m evals.run_eval --provider baseline            # offline, deterministic (CI)
    python -m evals.run_eval --provider gemini --models gemini-2.5-flash,gemini-2.5-pro
    python -m evals.run_eval --provider baseline --check    # fail if below evals/thresholds.json

Writes evals/results/latest.json and evals/results/RESULTS.md.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import Settings
from app.llm.base import LLMClient
from app.pipeline.runner import ExtractionPipeline
from evals.baseline import RuleBasedLLM
from evals.metrics import CaseScore, aggregate, score_case

HERE = Path(__file__).parent
# Approximate USD per 1M tokens (input, output). Verify against current provider pricing.
PRICING = {"gemini-2.5-flash": (0.30, 2.50), "gemini-2.5-pro": (1.25, 10.0), "gemini-2.5-flash-lite": (0.10, 0.40)}
JUDGE_PROMPT = """Does the QUOTE from a meeting transcript support the ACTION ITEM (someone committed to or was assigned it)?
ACTION ITEM: {task} (owner: {owner})
QUOTE: {quote}
Return ONLY JSON: {{"supported": true|false}}"""


def load_cases() -> List[Dict[str, Any]]:
    return json.loads((HERE / "dataset" / "cases.json").read_text())


class _CountingLLM:
    """Wraps an LLMClient to accumulate token counts."""

    def __init__(self, inner: LLMClient):
        self._inner = inner
        self.model = inner.model
        self.input_tokens = 0
        self.output_tokens = 0

    async def generate(self, prompt: str, *, json_mode: bool = False):
        res = await self._inner.generate(prompt, json_mode=json_mode)
        self.input_tokens += res.input_tokens
        self.output_tokens += res.output_tokens
        return res

    async def embed(self, texts):
        return await self._inner.embed(texts)


async def evaluate(llm: LLMClient, settings: Settings, judge: bool = False) -> Dict[str, Any]:
    scores: List[CaseScore] = []
    per_case = []
    for case in load_cases():
        counting = _CountingLLM(llm)
        pipeline = ExtractionPipeline(counting, settings)
        started = time.perf_counter()
        try:
            final = await pipeline.run(case["transcript"], case.get("meetingDate"))
            tasks = [t.model_dump(by_alias=True, mode="json") for t in final["data"].tasks]
            error = None
        except Exception as exc:  # noqa: BLE001 — a failing case counts as zero predictions
            tasks, error = [], str(exc)
        latency = (time.perf_counter() - started) * 1000
        sc = score_case(case, tasks)
        sc.latency_ms, sc.input_tokens, sc.output_tokens = latency, counting.input_tokens, counting.output_tokens
        if error:
            sc.notes.append(error)
        if judge and tasks:
            for t in tasks:
                if t.get("evidence") and t["evidence"].get("quote"):
                    r = await llm.generate(JUDGE_PROMPT.format(task=t["task"], owner=t["owner"], quote=t["evidence"]["quote"]), json_mode=True)
                    if '"supported": false' in r.text.lower().replace('"supported":false', '"supported": false'):
                        sc.unsupported += 1
        scores.append(sc)
        per_case.append({"id": case["id"], "tags": case["tags"], "tp": sc.tp, "fp": sc.fp, "fn": sc.fn, "notes": sc.notes})
    agg = aggregate(scores)
    in_p, out_p = PRICING.get(llm.model, (0.0, 0.0))
    agg["estCostUsd"] = round(agg["inputTokens"] / 1e6 * in_p + agg["outputTokens"] / 1e6 * out_p, 5)
    return {"model": llm.model, "metrics": agg, "cases": per_case}


def to_markdown(results: List[Dict[str, Any]], n_cases: int) -> str:
    cols = [("Precision", "precision"), ("Recall", "recall"), ("F1", "f1"), ("Owner acc", "ownerAccuracy"),
            ("Deadline acc", "deadlineAccuracy"), ("Priority acc", "priorityAccuracy"), ("Faithfulness", "faithfulness"),
            ("Injection resist.", "injectionResistance"), ("No-action false alarms", "noActionFalseAlarmRate"),
            ("p50 ms", "latencyP50Ms"), ("p95 ms", "latencyP95Ms"), ("Est. cost $", "estCostUsd")]
    lines = [f"Eval set: {n_cases} labeled transcripts (`evals/dataset/cases.json`).", "",
             "| Model | " + " | ".join(c[0] for c in cols) + " |", "|---|" + "---|" * len(cols)]
    for r in results:
        lines.append(f"| `{r['model']}` | " + " | ".join(str(r["metrics"][c[1]]) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def check_thresholds(result: Dict[str, Any]) -> List[str]:
    thresholds = json.loads((HERE / "thresholds.json").read_text())
    m = result["metrics"]
    failures = []
    for key, floor in thresholds.get("min", {}).items():
        if m[key] < floor:
            failures.append(f"{key}={m[key]} < {floor}")
    for key, ceiling in thresholds.get("max", {}).items():
        if m[key] > ceiling:
            failures.append(f"{key}={m[key]} > {ceiling}")
    return failures


async def main_async(args: argparse.Namespace) -> int:
    settings = Settings(gemini_api_key=args.api_key or "")
    results = []
    if args.provider == "baseline":
        results.append(await evaluate(RuleBasedLLM(), settings, judge=False))
    else:
        from app.llm.gemini import GeminiClient

        for model in args.models.split(","):
            client = GeminiClient(settings.gemini_api_key, model.strip(), settings.embedding_model)
            results.append(await evaluate(client, settings, judge=args.judge))

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"latest-{args.provider}.json").write_text(json.dumps(results, indent=2) + "\n")
    md = to_markdown(results, len(load_cases()))
    (out_dir / f"RESULTS-{args.provider}.md").write_text(md)
    print(md)

    if args.check:
        failures = check_thresholds(results[0])
        if failures:
            print("REGRESSION:", "; ".join(failures), file=sys.stderr)
            return 1
        print("Thresholds OK")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["baseline", "gemini"], default="baseline")
    ap.add_argument("--models", default="gemini-2.5-flash")
    ap.add_argument("--api-key", default="")
    ap.add_argument("--judge", action="store_true", help="LLM-judge pass over each quote (gemini only)")
    ap.add_argument("--check", action="store_true", help="exit 1 if metrics fall below evals/thresholds.json")
    args = ap.parse_args()
    if args.provider == "gemini" and not args.api_key:
        import os

        args.api_key = os.environ.get("GEMINI_API_KEY", "")
        if not args.api_key:
            sys.exit("Set GEMINI_API_KEY (or --api-key) to run the gemini provider.")
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
