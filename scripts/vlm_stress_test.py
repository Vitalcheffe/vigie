#!/usr/bin/env python3
"""
VLM Stress Test — Vigie Bot (Python version, aligned with project architecture).

Runs 100 VLM calls on a fixed screenshot, then repeats. Measures latency
(p50/p95/p99), success rate, JSON parse rate, and response stability.

Uses the `z-ai vision` CLI in subprocess (same pattern as app/services/zai_llm.py).

Outputs:
  /home/z/my-project/scripts/vlm_stress_run1.json
  /home/z/my-project/scripts/vlm_stress_run2.json
  /home/z/my-project/scripts/vlm_stress_report.md
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------- Config ----------
SCREENSHOT_PATH = "/home/z/my-project/scripts/vigie_screenshot.png"
NUM_CALLS = int(os.environ.get("VLM_STRESS_NUM_CALLS", "100"))
RUNS = int(os.environ.get("VLM_STRESS_RUNS", "2"))
OUTPUT_DIR = Path("/home/z/my-project/scripts")
REPORT_PATH = OUTPUT_DIR / "vlm_stress_report.md"
CONCURRENCY = 1  # sequential — VLM API rate-limits aggressively
INTER_CALL_DELAY = 0.5  # seconds between successful calls
MAX_RETRIES = 3  # retry on 429 with exponential backoff
RETRY_BASE_DELAY = 10.0  # seconds (10s, 20s, 40s)

SYSTEM_PROMPT = """Tu es Vigie-VLM, un assistant visuel dédié à l'analyse de captures d'écran du bot Slack Vigie (prévention des décès par isolation pendant les canicules).

Ta mission : analyser une capture d'écran et produire un rapport structuré contenant :
1. COVERAGE_PERCENT: pourcentage de couverture affiché (ou "N/A")
2. AVG_LATENCY_MIN: latence moyenne de check-in affichée en minutes (ou "N/A")
3. L2_COUNT: nombre d'escalades L2 (pas de réponse)
4. L3_COUNT: nombre d'escalades L3 (inconscient)
5. CRISIS_MSG_COUNT: nombre de messages dans #cellule-crise
6. TOP_SECTORS: liste des secteurs visibles (JSON array)
7. ACTIVE_ALERTS: bénéficiaires actuellement en alerte (JSON array d'objets {name, level})
8. DASHBOARD_HEALTH: "OK" si coverage >= 90% ET L3=0, sinon "ALERT"
9. SUMMARY: 1 phrase en français résumant l'état global

Réponds UNIQUEMENT en JSON valide, sans texte autour."""

# z-ai vision CLI has no --system flag, so we concatenate the system prompt
# with the user prompt into a single --prompt argument.
USER_PROMPT = SYSTEM_PROMPT + "\n\n" + "Analyse cette capture du dashboard Vigie et réponds en JSON."


# ---------- Helpers ----------
def percentile(sorted_list: list[float], p: float) -> float:
    if not sorted_list:
        return 0.0
    idx = min(int((p / 100.0) * len(sorted_list)), len(sorted_list) - 1)
    return sorted_list[idx]


def hash_str(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


async def call_vlm_once(sem: asyncio.Semaphore, idx: int) -> dict[str, Any]:
    """One VLM call via z-ai CLI subprocess, with retry on 429."""
    async with sem:
        start = time.perf_counter()
        last_error = ""
        for attempt in range(MAX_RETRIES + 1):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "z-ai", "vision",
                    "-p", USER_PROMPT,
                    "-i", SCREENSHOT_PATH,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180.0)

                if proc.returncode != 0:
                    err_text = stderr.decode("utf-8", errors="replace")
                    last_error = f"rc={proc.returncode} stderr={err_text[:300]}"
                    # Check for 429 rate limit
                    if "429" in err_text and attempt < MAX_RETRIES:
                        backoff = RETRY_BASE_DELAY * (2 ** attempt)
                        print(f"    [idx={idx}] 429 hit, backing off {backoff:.0f}s (attempt {attempt+1}/{MAX_RETRIES})", flush=True)
                        await asyncio.sleep(backoff)
                        continue
                    return {
                        "index": idx,
                        "ok": False,
                        "latencyMs": (time.perf_counter() - start) * 1000.0,
                        "error": last_error,
                    }

                # z-ai vision prints emojis/log lines, then a JSON block.
                raw = stdout.decode("utf-8", errors="replace")
                content = ""
                try:
                    start_json = raw.find("{")
                    if start_json == -1:
                        raise ValueError("no JSON found in stdout")
                    decoder = json.JSONDecoder()
                    data, _ = decoder.raw_decode(raw[start_json:])
                    if isinstance(data, dict):
                        choices = data.get("choices") or []
                        if choices:
                            msg = choices[0].get("message", {})
                            content = msg.get("content", "") or ""
                        if not content:
                            content = data.get("content", "") or data.get("response", "") or raw
                    else:
                        content = str(data)
                except (json.JSONDecodeError, ValueError):
                    content = raw.strip()

                parsed = None
                try:
                    import re
                    m = re.search(r"\{[\s\S]*\}", content)
                    if m:
                        parsed = json.loads(m.group(0))
                except Exception:
                    parsed = None

                latency_ms = (time.perf_counter() - start) * 1000.0
                # Inter-call delay to avoid hammering the API
                await asyncio.sleep(INTER_CALL_DELAY)

                return {
                    "index": idx,
                    "ok": True,
                    "latencyMs": latency_ms,
                    "content": content,
                    "parsed": parsed,
                    "retries": attempt,
                }
            except asyncio.TimeoutError:
                last_error = "timeout_180s"
                if attempt < MAX_RETRIES:
                    print(f"    [idx={idx}] timeout, retrying (attempt {attempt+1}/{MAX_RETRIES})", flush=True)
                    await asyncio.sleep(RETRY_BASE_DELAY)
                    continue
                return {
                    "index": idx,
                    "ok": False,
                    "latencyMs": (time.perf_counter() - start) * 1000.0,
                    "error": last_error,
                }
            except Exception as e:
                last_error = f"exc={type(e).__name__}:{str(e)[:200]}"
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BASE_DELAY)
                    continue
                return {
                    "index": idx,
                    "ok": False,
                    "latencyMs": (time.perf_counter() - start) * 1000.0,
                    "error": last_error,
                }

        # Should not reach here, but safety net
        return {
            "index": idx,
            "ok": False,
            "latencyMs": (time.perf_counter() - start) * 1000.0,
            "error": f"exhausted_retries: {last_error}",
        }


async def run_pass(run_num: int) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    start_total = time.perf_counter()

    print(f"\n=== Run {run_num} — {NUM_CALLS} VLM calls (concurrency={CONCURRENCY}) ===", flush=True)

    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [call_vlm_once(sem, i) for i in range(NUM_CALLS)]

    results: list[dict[str, Any]] = []
    # Stream completion with progress every 10
    done = 0
    for coro in asyncio.as_completed(tasks):
        r = await coro
        results.append(r)
        done += 1
        if done % 10 == 0 or done == NUM_CALLS:
            ok = sum(1 for r in results if r.get("ok"))
            last = results[-1]
            print(
                f"  [{done}/{NUM_CALLS}] ok={ok} last={last.get('latencyMs', 0):.0f}ms"
                + ("" if last.get("ok") else f" ERR={(last.get('error') or '')[:80]}"),
                flush=True,
            )

    # Order by index for reproducibility
    results.sort(key=lambda r: r.get("index", 0))

    total_ms = (time.perf_counter() - start_total) * 1000.0
    ended_at = datetime.now(timezone.utc).isoformat()

    ok_results = [r for r in results if r.get("ok")]
    latencies = sorted([float(r["latencyMs"]) for r in ok_results])
    parse_count = sum(1 for r in ok_results if r.get("parsed") is not None)

    response_hash_counts: dict[str, int] = {}
    for r in ok_results:
        h = hash_str(r.get("content", ""))
        response_hash_counts[h] = response_hash_counts.get(h, 0) + 1

    stats = {
        "successRate": len(ok_results) / max(1, len(results)),
        "p50Ms": percentile(latencies, 50),
        "p95Ms": percentile(latencies, 95),
        "p99Ms": percentile(latencies, 99),
        "avgMs": statistics.mean(latencies) if latencies else 0.0,
        "minMs": latencies[0] if latencies else 0.0,
        "maxMs": latencies[-1] if latencies else 0.0,
        "parseRate": parse_count / max(1, len(ok_results)),
        "uniqueResponses": len(response_hash_counts),
        "responseHashCounts": response_hash_counts,
    }

    print(
        f"  -> Run {run_num} done in {total_ms/1000:.1f}s "
        f"success={stats['successRate']:.2%} p50={stats['p50Ms']:.0f}ms "
        f"p95={stats['p95Ms']:.0f}ms parse={stats['parseRate']:.2%} "
        f"unique={stats['uniqueResponses']}/{len(ok_results)}",
        flush=True,
    )

    return {
        "run": run_num,
        "startedAt": started_at,
        "endedAt": ended_at,
        "totalMs": total_ms,
        "results": results,
        "stats": stats,
    }


def build_report(runs: list[dict[str, Any]]) -> str:
    r1, r2 = runs[0], runs[1]
    ok1 = sum(1 for r in r1["results"] if r.get("ok"))
    ok2 = sum(1 for r in r2["results"] if r.get("ok"))
    top1 = sorted(r1["stats"]["responseHashCounts"].items(), key=lambda kv: -kv[1])[0] if r1["stats"]["responseHashCounts"] else None
    top2 = sorted(r2["stats"]["responseHashCounts"].items(), key=lambda kv: -kv[1])[0] if r2["stats"]["responseHashCounts"] else None

    sample1 = next((r.get("parsed") for r in r1["results"] if r.get("parsed")), None)
    sample2 = next((r.get("parsed") for r in r2["results"] if r.get("parsed")), None)

    latency_drift = (
        (r2["stats"]["avgMs"] - r1["stats"]["avgMs"]) / r1["stats"]["avgMs"] * 100
        if r1["stats"]["avgMs"] else 0.0
    )

    stability1 = (top1[1] / ok1 * 100) if top1 and ok1 else 0
    stability2 = (top2[1] / ok2 * 100) if top2 and ok2 else 0

    md = f"""# VLM Stress Test Report — Vigie Bot

**Date:** {datetime.now(timezone.utc).isoformat()}
**Screenshot:** `{SCREENSHOT_PATH}`
**Configuration:** {NUM_CALLS} calls x {RUNS} runs = {NUM_CALLS * RUNS} total VLM calls
**Concurrency:** {CONCURRENCY} parallel subprocess calls
**Backend:** `z-ai vision` CLI (subprocess)

## 1. Summary

| Metric | Run 1 | Run 2 | Drift |
|---|---|---|---|
| Success rate | {r1['stats']['successRate']*100:.1f}% | {r2['stats']['successRate']*100:.1f}% | {(r2['stats']['successRate']-r1['stats']['successRate'])*100:+.1f} pts |
| Parse rate (JSON valid) | {r1['stats']['parseRate']*100:.1f}% | {r2['stats']['parseRate']*100:.1f}% | {(r2['stats']['parseRate']-r1['stats']['parseRate'])*100:+.1f} pts |
| Avg latency | {r1['stats']['avgMs']:.0f} ms | {r2['stats']['avgMs']:.0f} ms | {latency_drift:+.1f}% |
| p50 latency | {r1['stats']['p50Ms']:.0f} ms | {r2['stats']['p50Ms']:.0f} ms | - |
| p95 latency | {r1['stats']['p95Ms']:.0f} ms | {r2['stats']['p95Ms']:.0f} ms | - |
| p99 latency | {r1['stats']['p99Ms']:.0f} ms | {r2['stats']['p99Ms']:.0f} ms | - |
| Min latency | {r1['stats']['minMs']:.0f} ms | {r2['stats']['minMs']:.0f} ms | - |
| Max latency | {r1['stats']['maxMs']:.0f} ms | {r2['stats']['maxMs']:.0f} ms | - |
| Total wall clock | {r1['totalMs']/1000:.1f} s | {r2['totalMs']/1000:.1f} s | - |
| Unique response hashes | {r1['stats']['uniqueResponses']} | {r2['stats']['uniqueResponses']} | - |
| Top hash frequency | {top1[1] if top1 else 0}/{ok1} | {top2[1] if top2 else 0}/{ok2} | - |

## 2. Stability Analysis

- **Run 1 stability:** {stability1:.1f}% of responses were identical (top hash)
- **Run 2 stability:** {stability2:.1f}% of responses were identical (top hash)
- **Cross-run latency drift:** {latency_drift:+.1f}% ({"HIGH" if abs(latency_drift) > 20 else "MODERATE" if abs(latency_drift) > 10 else "LOW"})
- **Cross-run stability drift:** {abs(stability2 - stability1):.1f} pts

## 3. Sample Parsed Response (Run 1)

```json
{json.dumps(sample1 or {"error": "no parsed sample"}, indent=2, ensure_ascii=False)}
```

## 4. Sample Parsed Response (Run 2)

```json
{json.dumps(sample2 or {"error": "no parsed sample"}, indent=2, ensure_ascii=False)}
```

## 5. Errors (first 5)

"""
    errors = [r for r in [*r1["results"], *r2["results"]] if not r.get("ok")][:5]
    if not errors:
        md += f"No errors across {NUM_CALLS * RUNS} calls.\n\n"
    else:
        md += "| Run | Index | Latency | Error |\n|---|---|---|---|\n"
        for e in errors:
            run_num = 1 if e.get("index", 0) < NUM_CALLS else 2
            md += f"| {run_num} | {e.get('index', 0) % NUM_CALLS} | {e.get('latencyMs', 0):.0f}ms | {(e.get('error') or '')[:100].replace('|', '\\|')} |\n"
        md += "\n"

    md += """## 6. Verdict

"""
    verdict = (
        "PASS — VLM is stable enough for production integration in Vigie bot."
        if (
            r1["stats"]["successRate"] >= 0.95
            and r2["stats"]["successRate"] >= 0.95
            and r1["stats"]["parseRate"] >= 0.9
            and r2["stats"]["parseRate"] >= 0.9
            and abs(latency_drift) < 25
        )
        else "CONDITIONAL — review metrics before production integration."
    )
    md += f"**{verdict}**\n"
    return md


async def main() -> None:
    print("VLM Stress Test — Vigie Bot (Python)")
    print(f"Screenshot: {SCREENSHOT_PATH}")
    print(f"Config: {NUM_CALLS} calls x {RUNS} runs, concurrency={CONCURRENCY}")

    if not Path(SCREENSHOT_PATH).exists():
        raise SystemExit(f"Screenshot not found: {SCREENSHOT_PATH}")

    runs: list[dict[str, Any]] = []
    for i in range(1, RUNS + 1):
        result = await run_pass(i)
        runs.append(result)
        out_json = OUTPUT_DIR / f"vlm_stress_run{i}.json"
        out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"  -> Saved run {i} to {out_json.name}", flush=True)
        if i < RUNS:
            print("  -> Cooling down 5s before next run...", flush=True)
            await asyncio.sleep(5)

    report = build_report(runs)
    REPORT_PATH.write_text(report)
    print(f"\nReport saved to: {REPORT_PATH}")
    print("\n--- REPORT PREVIEW ---\n")
    print(report[:2500])


if __name__ == "__main__":
    asyncio.run(main())
