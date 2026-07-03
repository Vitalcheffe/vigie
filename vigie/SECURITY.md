# Security Policy

## Reporting a vulnerability

If you find a security issue in Vigie, please email **amineharchelkorane5@gmail.com**
with a clear description and reproduction steps. Do NOT open a public GitHub issue.

We will acknowledge within 48 hours and aim to publish a fix within 7 days
for critical issues, 30 days for moderate issues.

## Scope

This policy covers the Vigie codebase in this repository. It does not
cover Slack platform itself (report to Slack directly), Météo-France API
(report to Météo-France), OpenStreetMap Overpass (report to Overpass
maintainers), or any third-party service Vigie integrates with.

## Data protection

Vigie is designed to process simulated beneficiary data only. In a real
deployment, the operator (a registered nonprofit or local government)
is the data controller under GDPR (or HIPAA in the US). Vigie itself
does not store personal data outside the operator's Slack workspace
and MCP server.

The MCP server stores the beneficiary registry on disk
(`mcp_server/data/beneficiaries.json`). In production, this file must
be encrypted at rest (AES-256 or platform-managed encryption).

Logs are structured JSON via `structlog`. PII (phone numbers, names,
addresses) is logged at DEBUG level only. Production deployments should
run at INFO level.

## Disclosure policy

Once a fix is released, we will publish a GitHub Security Advisory with
credit to the reporter (unless they prefer to remain anonymous).

## Best practices for deployers

- Rotate `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_APP_TOKEN`
  every 90 days.
- Use a separate Slack workspace for testing vs production.
- Do not commit `.env` to git. The provided `.gitignore` already
  excludes it.
- Run Vigie as a non-root user (the Dockerfile handles this).
- Limit network egress from the Vigie container to: Slack API,
  Météo-France API, NWS API, OpenStreetMap Overpass, your LLM provider.
