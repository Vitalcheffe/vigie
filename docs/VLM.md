# Vigie VLM — Vision Language Model Integration

This module integrates Z-AI's vision model (`glm-4.6v` via `z-ai vision` CLI)
into the Vigie bot to analyze dashboard screenshots and extract structured
crisis-cell state that text-only LLMs cannot see.

## Why VLM?

The existing Z-AI LLM classifier (`app/services/zai_llm.py`) processes
volunteer check-in **text** notes and classifies them L0/L1/L2/L3. But during
a heatwave, supervisors also need to **visually inspect the dashboard** to
catch anomalies invisible to text processing:

- A coverage % dropping below 90% without any individual alert
- A KPI card showing a wrong number due to a state bug
- A screenshot shared by a volunteer showing something the bot missed
- An accessibility issue (color contrast, layout) that prevents a supervisor
  from reading the dashboard under stress

The VLM acts as a **second pair of eyes** on the visual state of the system.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Vigie Bot (Python)                       │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  Slack API   │───▶│  snapshot.py │───▶│   vlm.py     │   │
│  │  (App Home)  │    │  (HTML +     │    │  (z-ai CLI   │   │
│  │              │    │  screenshot) │    │  subprocess) │   │
│  └──────────────┘    └──────────────┘    └──────┬───────┘   │
│                                                  │           │
│                                                  ▼           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  audit.py    │◀───│  Dashboard   │───▶│  health.py   │   │
│  │  (vlm_       │    │  Analysis    │    │  /vlm/health │   │
│  │   analyze)   │    │  dataclass   │    │  endpoint    │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Files

| File | Role |
|------|------|
| `app/services/vlm.py` | Core VLM service: system prompt, parser, cache, stats, audit logging |
| `app/services/snapshot.py` | Captures Slack App Home dashboard → HTML → PNG via `agent-browser` |
| `app/handlers/commands.py` | `/vigie inspect <image_path>` slash command |
| `app/health.py` | `/vlm/health` and `/vlm/cache/clear` endpoints |
| `app/scheduler.py` | `_job_vlm_snapshot` — periodic snapshot every 15 min (opt-in) |
| `app/main.py` | Boot self-check hook (non-blocking) |
| `tests/test_vlm.py` | 8 tests — parser + service |
| `tests/test_vlm_cache.py` | 7 tests — cache + health + stats |
| `tests/test_vlm_audit.py` | 7 tests — audit log integration |
| `scripts/vlm_stress_test.py` | Stress test runner (100×2 calls) |
| `scripts/vlm_build_report.py` | Report generator from JSONL results |

## System Prompt

The system prompt (`VIGIE_VLM_SYSTEM_PROMPT` in `app/services/vlm.py`) asks
the VLM to extract 9 structured fields from any Vigie dashboard screenshot:

| Field | Type | Description |
|-------|------|-------------|
| `COVERAGE_PERCENT` | int | Coverage percentage (e.g., 94) |
| `AVG_LATENCY_MIN` | int | Average check-in latency in minutes |
| `L2_COUNT` | int | Number of L2 escalations (no answer) |
| `L3_COUNT` | int | Number of L3 escalations (unconscious) |
| `CRISIS_MSG_COUNT` | int | Messages in #cellule-crise |
| `TOP_SECTORS` | string[] | Visible sector names |
| `ACTIVE_ALERTS` | {name, level}[] | Beneficiaries currently in L1/L2/L3 |
| `DASHBOARD_HEALTH` | "OK" \| "ALERT" | Computed from coverage + L3 |
| `SUMMARY` | string | One-sentence French summary |

The prompt includes explicit type rules ("ENTIER sans signe %") and a complete
JSON example to minimize type variance.

## Usage

### On-demand analysis

```bash
# In Slack:
/vigie inspect /tmp/my_screenshot.png

# Result: Block Kit message with health verdict, KPIs, alerts, and screenshot
```

### Periodic monitoring

Set environment variables on Railway:

```bash
VIGIE_VLM_SNAPSHOT_ENABLED=true       # enable the 15-min snapshot job
VIGIE_BOT_USER_ID=U12345              # bot's own user ID for App Home capture
VIGIE_VLM_BOOT_IMAGE=/tmp/boot.png    # optional: image for boot self-check
```

The bot will:
1. Every 15 min during an active scenario, capture the App Home dashboard
2. Run VLM analysis (cache bypassed, since the dashboard changes)
3. Log the analysis to the audit log (`action=vlm_analyze`)
4. If `DASHBOARD_HEALTH=ALERT` and `L3_COUNT > 0`, post a warning in
   `#cellule-crise`

### Boot self-check

On startup, `app/main.py` calls `boot_self_check()` which:
1. Verifies `z-ai` CLI is reachable
2. If `VIGIE_VLM_BOOT_IMAGE` is set, runs a real VLM call on that image
3. Logs the result but never blocks the bot from starting

### Health monitoring

```bash
# VLM service health
curl https://vigie.up.railway.app/vlm/health

# Response:
{
  "ok": true,
  "stats": {
    "calls_total": 42,
    "calls_ok": 40,
    "calls_failed": 2,
    "cache_hits": 15,
    "parse_errors": 0
  },
  "cache_size": 8,
  "cache_max": 32,
  "timeout_s": 180.0
}

# Clear cache
curl https://vigie.up.railway.app/vlm/cache/clear
```

### Audit log

Every VLM call (success or failure) is recorded in the audit log:

```bash
curl https://vigie.up.railway.app/audit | jq '.entries[] | select(.action=="vlm_analyze")'
```

Example entry:

```json
{
  "timestamp": "2026-07-03T14:35:12+00:00",
  "actor": "vigie-vlm",
  "action": "vlm_analyze",
  "target": "/tmp/vigie_vlm_snapshot_1783058112.png",
  "reason": null,
  "result": "ok",
  "metadata": {
    "coverage_percent": 94,
    "l2_count": 2,
    "l3_count": 1,
    "dashboard_health": "ALERT",
    "active_alerts_count": 3,
    "vlm_latency_ms": 15849.8,
    "parse_error": null
  }
}
```

## Test Results

### Unit tests (22 total, 22 passing)

```
tests/test_vlm.py          8/8 PASS   — parser + service
tests/test_vlm_cache.py    7/7 PASS   — cache + health + stats
tests/test_vlm_audit.py    7/7 PASS   — audit log integration
```

### Stress test (7 successful calls on synthetic dashboard)

| Metric | Value |
|---|---|
| Success rate | 100% (7/7) |
| JSON parse rate | 100% |
| Avg latency | 9.8s |
| p50 latency | 8.6s |
| p95 latency | 23.7s |
| Field stability (COVERAGE/L2/L3/HEALTH) | 100% |

The Z-AI API enforces aggressive rate limits (HTTP 429) that prevented
completing the full 200-call test in one session. The partial results validate
the pipeline.

## Limitations

1. **No `--system` flag on `z-ai vision` CLI**: The system prompt is embedded
   in the `--prompt` argument. This works but slightly increases token cost.

2. **Rate limits**: The Z-AI API returns HTTP 429 after ~10-15 rapid calls.
   The service retries with exponential backoff (15s, 30s, 60s, 120s, 240s)
   but this can make batch analysis slow.

3. **Type variance**: Despite the strict prompt, the VLM sometimes returns
   `"94%"` (string) instead of `94` (int). The parser handles both forms by
   stripping `%` and converting to int.

4. **Snapshot requires `agent-browser`**: The periodic snapshot job needs
   `agent-browser` installed (`npm install -g agent-browser`). If not
   available, the job logs a warning and skips.

5. **App Home capture needs `VIGIE_BOT_USER_ID`**: The bot captures its own
   App Home, which requires knowing its user ID. Set via env var.
