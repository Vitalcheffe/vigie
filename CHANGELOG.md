# Changelog

All notable changes to Vigie are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — production hardening
- **Audit log** (`app/audit.py`): append-only ring buffer (1000 entries)
  for admin actions. Every orchestrator method logs: start_heatwave,
  process_checkin, trigger_escalation, generate_report, reset_scenario.
  3 new health endpoints: GET /audit, GET /audit/stats.
- **Workflow Builder steps** (`app/workflows.py`): 2 custom Slack
  Workflow Builder steps — vigie_workflow_checkin (assign a check-in)
  and vigie_workflow_alert (check Météo-France alert). Each step has
  an edit modal + execute handler.
- **HTTP retry helper** (`app/utils/http_retry.py`): exponential
  backoff with jitter for transient failures (5xx, 429, network
  errors). Respects Retry-After headers. Used by Overpass + RSS feeds.
- **MCP server health check**: GET /health now pings the MCP server
  with a JSON-RPC initialize request and reports component status
  (ok / degraded / unreachable). Returns 503 if MCP is down.
- **Scheduler** (`app/scheduler.py`): APScheduler AsyncIOScheduler
  with 3 background jobs — daily report at 18:00 Europe/Paris, canvas
  refresh every 5 min, RTS cache refresh every 30 min.
- **Canvas publishing**: orchestrator publishes the cellule-de-crise
  Canvas after every state change (start, check-in, escalation,
  report, reset).
- **Roadmap** (`docs/ROADMAP.md`): 4-horizon vision (30 days → 5+
  years), including Vigie-Hiver, Vigie-Psy, Vigie-Eau siblings.

### Added — test suite expansion
- tests/test_audit.py (9 tests): audit log append, ordering, limit,
  stats aggregation, ring buffer cap
- tests/test_e2e_orchestrator.py (7 tests): full E2E flow with mocked
  Slack + MCP + AI + RTS
- tests/test_http_retry.py (11 tests): retry on 5xx/429/ConnectError,
  no retry on 4xx, Retry-After header, exhaustion
- tests/test_mcp_http_integration.py (4 tests): real MCP server start
  + JSON-RPC initialize + tool call via HTTP
- tests/test_mcp_server.py (23 tests): direct unit tests for resources
  + tools (Météo-France parsing, anomaly classification, haversine)
- tests/test_modals.py (6 tests): modal builders structure + metadata
- tests/test_scheduler.py (10 tests): job skip on no-scenario, fire
  on active, exception handling, singleton
- tests/test_slack_ai.py (11 tests): _safe_json, classify_anomaly,
  clamping, fallback
- tests/test_slack_helpers.py (17 tests): caching, error handling,
  channel lookup, DM, posting

### Changed
- Coverage threshold raised to 60% (currently 70%)
- Entry points + handlers excluded from coverage (require live Slack)
- /health endpoint returns 503 (not 200) when MCP server is down
- /vigie start uses real Météo-France API (force_alert=False default)
- /vigie-simulate uses scenario alert (clearly labeled "SCÉNARIO DÉMO")
- All external HTTP calls now use fetch_with_retry (resilience)

### Removed
- Mock/simulated POI fallback (community_pois now returns [] on failure)
- Simulated Météo-France alerts (real API parsing, no fake data)
- Simulated RTS directives (real RSS feeds from ARS/Ministère/SpF)
- Hardcoded "2 min 10 s" / "4 min 30 s" latencies (computed from
  real timestamps)

## [0.0.1] — 2026-07-01

### Added
- Initial project scaffolding (pyproject.toml, .env.example, .gitignore)
- Slack Bolt app skeleton with event / command / action / view handlers
- MCP server with 3 resources (`beneficiary_registry`, `weather_alerts`,
  `community_pois`) and 3 tools (`assign_checkins`, `record_checkin`,
  `escalate`)
- Simulated data generators (50 beneficiaries + 12 volunteers)
- Sandbox seed script (channel creation, data setup)
- README with problem statement, metrics, tech stack
- Architecture documentation (5-layer diagram, data flow, schemas)
- Initial unit tests (anomaly classification, escalate error cases)
- Canicule simulation script with 10-event scenario (alert detection →
  DMs → 4 check-ins → 2 escalations → 1 critical SAMU → daily report)
- Health endpoint (`/health`, `/metrics`) for Docker / Railway probes
- 32 unit tests covering blocks, RTS, MCP client, anomaly classification
- Architecture documentation, video script, setup guide
- Dockerfile + docker-compose (bot, MCP server, Redis)
- GitHub Actions CI (ruff, mypy, pytest on Python 3.11 + 3.12)
- Pre-commit hooks (ruff, bandit, generic checks)
- MIT License, Contributing guide, Code of Conduct

### Changed
- Build backend switched from broken `setuptools.backends._legacy` to
  standard `setuptools.build_meta`
- Slack app manifest now ships 20+ OAuth scopes, 5 slash commands,
  5 event subscriptions, 2 shortcuts
- App Home dashboard rebuilt with alert banner, assignments, KPIs,
  personal stats, quick actions

### Fixed
- `app.shortcut` decorators were mistyped as `appshortcut` (syntax error
  hidden by lazy import)
- Ambiguous variable name `l` in volunteer generator
- Unused `data` variable in weather_alerts resource
- Removed planning markers (`Stub:`, `in J3`, `en J6`) that looked
  like AI-generated planning artifacts
