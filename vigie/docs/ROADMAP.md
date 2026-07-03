# Vigie — Roadmap

> Where Vigie is going. Not a commitment, a direction.

This document maps the path from hackathon prototype to permanent
infrastructure. It's organized in 4 horizons: 30 days, 6 months,
18 months, 5+ years.

---

## Horizon 1 — 30 days (post-hackathon stabilization)

**Goal**: Turn the hackathon prototype into a deployable tool that real
nonprofits can pilot during the August 2026 heatwave season.

### 1.1 Production readiness
- [ ] PostgreSQL backend for beneficiary registry (replace JSON fixture)
- [ ] Encrypted at rest (AES-256 or platform-managed)
- [ ] Multi-tenant architecture (1 workspace = 1 tenant)
- [ ] OAuth 2.0 for Slack Marketplace installation
- [ ] Proper logging pipeline (Loki + Grafana or Datadog)
- [ ] Uptime monitoring (Better Stack or equivalent)

### 1.2 First pilot deployment
- [ ] Sign pilot agreement with 1 French ONG (Petits Frères des Pauvres, Croix-Rouge, or Secours Populaire)
- [ ] Deploy Vigie in their production Slack workspace
- [ ] Train 30 volunteers (2 training sessions)
- [ ] Run a tabletop exercise (simulated heatwave, no real risk)
- [ ] Document lessons learned in a public post-mortem

### 1.3 Code quality
- [ ] Reach 85% test coverage (currently 70%)
- [ ] Type-checking with mypy --strict (currently non-blocking)
- [ ] Add integration tests for the full Slack Event API round-trip
- [ ] Set up Dependabot + Renovate for automated dependency updates
- [ ] Security audit with bandit + pip-audit in CI

---

## Horizon 2 — 6 months (productize)

**Goal**: Make Vigie installable by any nonprofit in under 1 hour,
without developer assistance.

### 2.1 Slack Marketplace submission
- [ ] Complete the Slack Marketplace review process
- [ ] Comply with all Slack Marketplace Core Guidelines
- [ ] Get installed in 5+ workspaces (requirement)
- [ ] Publish a public app listing with screenshots + video

### 2.2 Self-serve onboarding
- [ ] `/vigie setup` wizard: guided channel creation, volunteer import, beneficiary upload
- [ ] CSV import for beneficiary registry (Plan Canicule format)
- [ ] Slack-native volunteer onboarding flow (no admin panel)
- [ ] Multi-language support (FR + EN + ES)

### 2.3 Vigie family — first sibling
- [ ] **Vigie-Hiver**: same architecture, grand-froid alerts (Météo-France vigilance neige/verglas). Reuses 80% of the Vigie codebase.
- [ ] Validate that the MCP server pattern generalizes beyond canicule.

---

## Horizon 3 — 18 months (institutional adoption)

**Goal**: Vigie becomes the de facto Slack agent for elder watch in
France, with pilots in 5+ countries.

### 3.1 Geographic expansion
- [ ] 50 nonprofit deployments in France
- [ ] 10 deployments in Belgium, Switzerland, Luxembourg (French-speaking)
- [ ] 5 pilots in the US (using NWS API + CDC Heat & Health Toolkit)
- [ ] 3 pilots in Southern Europe (Spain, Italy, Portugal — localized)

### 3.2 Government partnerships
- [ ] Mention in a French Ministry of Health communiqué
- [ ] Cited in the WHO Heat-Health Action Plans update (2027)
- [ ] Adopted by 3 French départements as part of their Plan Canicule
- [ ] Pilot with a US city health department (NYC, Chicago, or Phoenix)

### 3.3 Vigie family — full suite
- [ ] **Vigie-Psy**: weekly wellness check-ins for isolated seniors (no heatwave required)
- [ ] **Vigie-Eau**: flood response coordination (Vigie architecture + Vigicrues API)
- [ ] **Vigie-Canicule** (renamed Vigie): production-hardened, multi-region

### 3.4 Legal structure
- [ ] Incorporate as a French "fonds de dotation" or US 501(c)(3)
- [ ] 1-1-1 model: 1% time, 1% product, 1% equity → nonprofit
- [ ] Accept tax-deductible donations
- [ ] Apply for Salesforce Foundation grants

---

## Horizon 4 — 5+ years (permanent infrastructure)

**Goal**: Vigie exists in 2031 as the Slack-native equivalent of
emergency phone numbers — invisible, reliable, free.

### 4.1 Scale
- [ ] 1,000 deployments across 30 countries
- [ ] 100,000 elders watched per year
- [ ] Documented lives saved (anonymized case studies)

### 4.2 Ecosystem
- [ ] Open API for third-party integrations (CRM, EHR, GIS)
- [ ] Plugin marketplace for Vigie family extensions
- [ ] Annual "Vigie Conference" for the elder-care-tech community
- [ ] Academic partnerships (EHESS, MIT Media Lab, Stanford HAI)

### 4.3 Policy influence
- [ ] Vigie cited in French legislation on elder care
- [ ] EU-wide recommendation for heatwave response tools
- [ ] Vigie methodology taught in public-health master's programs

### 4.4 Long-term sustainability
- [ ] Freemium model: free for nonprofits, paid for governments + enterprises
- [ ] 51% of profits donated to elder-care nonprofits
- [ ] Community of 200+ active contributors
- [ ] No single point of failure (multi-region, multi-cloud)

---

## What we will NOT do

To keep Vigie focused, these are explicitly out of scope:

- **General-purpose chatbot** — Vigie is a heatwave/elder-watch agent, not a Slack ChatGPT
- **Mobile app** — Vigie lives in Slack; if you need mobile, install Slack mobile
- **Web dashboard** — Vigie is Slack-native; the Canvas + App Home are the dashboard
- **Multi-platform** (Teams, Discord) — Slack is the surface; porting dilutes focus
- **Ads or monetization of beneficiary data** — Vigie is funded by donations + freemium SaaS, never by data
- **AI diagnosis** — Vigie surfaces signals, humans (volunteers, doctors) make decisions

---

## How to contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow.

For strategic partnerships (NGO pilot, government deployment,
research collaboration), contact: amineharchelkorane5@gmail.com

---

## Dedicated to

The 14,802 people who died alone during the August 2003 heatwave in
France. And the 61,672 who died across Europe in summer 2022.

Every line of code in this repository exists because they existed.
This roadmap exists so that, by 2031, no one else has to die in
silence during a heatwave.
