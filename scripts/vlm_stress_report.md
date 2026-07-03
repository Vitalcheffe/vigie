# VLM Stress Test Report — Vigie Bot

**Date:** 2026-07-03T06:12:18.977224+00:00
**Screenshot:** `/home/z/my-project/scripts/vigie_screenshot.png`
**Configuration:** 10 calls x 2 runs = 20 total VLM calls
**Concurrency:** 1 parallel subprocess calls
**Backend:** `z-ai vision` CLI (subprocess)

## 1. Summary

| Metric | Run 1 | Run 2 | Drift |
|---|---|---|---|
| Success rate | 90.0% | 100.0% | +10.0 pts |
| Parse rate (JSON valid) | 100.0% | 100.0% | +0.0 pts |
| Avg latency | 17145 ms | 10804 ms | -37.0% |
| p50 latency | 8064 ms | 9114 ms | - |
| p95 latency | 76686 ms | 23524 ms | - |
| p99 latency | 76686 ms | 23524 ms | - |
| Min latency | 4924 ms | 5646 ms | - |
| Max latency | 76686 ms | 23524 ms | - |
| Total wall clock | 229.2 s | 113.1 s | - |
| Unique response hashes | 9 | 10 | - |
| Top hash frequency | 1/9 | 1/10 | - |

## 2. Stability Analysis

- **Run 1 stability:** 11.1% of responses were identical (top hash)
- **Run 2 stability:** 10.0% of responses were identical (top hash)
- **Cross-run latency drift:** -37.0% (HIGH)
- **Cross-run stability drift:** 1.1 pts

## 3. Sample Parsed Response (Run 1)

```json
{
  "COVERAGE_PERCENT": "94%",
  "AVG_LATENCY_MIN": "7",
  "L2_COUNT": 2,
  "L3_COUNT": 1,
  "CRISIS_MSG_COUNT": 43,
  "TOP_SECTORS": [
    "secteur-1",
    "secteur-2",
    "secteur-3"
  ],
  "ACTIVE_ALERTS": [
    {
      "name": "B018 - Monique B.",
      "level": "L3"
    },
    {
      "name": "B007 - Lucien P.",
      "level": "L2"
    },
    {
      "name": "B012 - Henri L.",
      "level": "L2"
    }
  ],
  "DASHBOARD_HEALTH": "ALERT",
  "SUMMARY": "Le dashboard Vigie montre une couverture à 94% avec une latence moyenne de 7 minutes, mais une escalade L3 (inconscient) et deux escalades L2 (sans réponse) sont en cours, déclenchant une alerte."
}
```

## 4. Sample Parsed Response (Run 2)

```json
{
  "COVERAGE_PERCENT": "94",
  "AVG_LATENCY_MIN": "7",
  "L2_COUNT": 2,
  "L3_COUNT": 1,
  "CRISIS_MSG_COUNT": 43,
  "TOP_SECTORS": [
    "secteur-1",
    "secteur-2",
    "secteur-3"
  ],
  "ACTIVE_ALERTS": [
    {
      "name": "B018 - Monique B.",
      "level": "L3"
    }
  ],
  "DASHBOARD_HEALTH": "ALERT",
  "SUMMARY": "Le dashboard Vigie montre une couverture de 94% et une latence moyenne de 7 minutes, mais une escalade L3 (inconscient) est en cours, déclenchant une alerte."
}
```

## 5. Errors (first 5)

| Run | Index | Latency | Error |
|---|---|---|---|
| 1 | 2 | 70375ms | rc=1 stderr=Failed to make vision API request: 143 \|                 headers: headers,
144 \|         |

## 6. Verdict

**CONDITIONAL — review metrics before production integration.**
