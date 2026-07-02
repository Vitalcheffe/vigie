# Changelog

All notable changes to Vigie are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Slack AI service with 4 tasks: transcription (Whisper fallback),
  structured extraction (JSON), 4-level anomaly classification, daily
  report generation
- Real-Time Search API service with 30-min TTL cache and simulated
  fallback for sandbox demos
- MCP client (typed async HTTP, JSON-RPC over streamable-http, SSE parsing)
- Block Kit builders for: check-in (sector message + volunteer DM),
  escalation (cellule de crise + thread replies), daily report, canvas,
  App Home dashboard
- Slack helpers: user info (cached), channel lookup, posting helpers,
  DM open+post, canvas publish
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
