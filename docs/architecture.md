# Vigie — Architecture Technique

> Document de référence pour le diagramme d'architecture soumis au hackathon.
> Source de vérité pour toute décision technique.

---

## Vue d'ensemble

Vigie est un agent Slack qui s'exécute dans un workspace d'ONG ou de collectivité pendant les canicules. Il combine 3 technologies obligatoires du hackathon Slack Agent Builder Challenge 2026 : Slack AI capabilities, MCP server integration, Real-Time Search API.

L'architecture comporte 5 couches horizontales + un flux bidirectionnel avec Slack.

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. SLACK WORKSPACE (Reseau-Soligarde-Paris sandbox)                 │
│  - #cellule-crise  (channel de coordination)                          │
│  - #secteur-1..12  (channels opérationnels par arrondissement)       │
│  - #voisins-1..12  (channels voisins référents)                      │
│  - DMs bénévoles ↔ Vigie                                              │
│  - App Home (dashboard temps réel par bénévole)                      │
│  - Canvas (vue cellule de crise partagée)                            │
│  - Lists (check-in assignments)                                       │
└────────────────────┬─────────────────────────────────────────────────┘
                     │ Slack Event API + Web API (HTTPS)
                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│  2. BOLT APP (Python 3.11, slack_bolt)                               │
│  - Slash commands: /vigie, /vigie-checkin, /vigie-escalate, ...     │
│  - Event handlers: app_mention, message.im, file_shared, ...        │
│  - Block Kit actions + view submissions (modals)                    │
│  - OAuth 2.0, signing secret verification                            │
│  - Socket Mode (dev) ou HTTP Request URL (prod)                      │
│  - Deployé sur Railway / Render                                       │
└──────────────┬──────────────────────────┬───────────────────────────┘
               │                          │
       ┌───────▼────────┐         ┌──────▼──────────────┐
       │ 3. SLACK AI    │         │ 4. MCP SERVER       │
       │   LAYER        │         │   (HTTP/SSE)        │
       │                │         │                     │
       │ • Transcription│         │ Resources:          │
       │   notes vocales│         │  - beneficiary_reg. │
       │ • Extraction   │         │  - weather_alerts   │
       │   JSON         │         │  - community_pois   │
       │ • Classif. 4   │         │                     │
       │   niveaux      │         │ Tools:              │
       │ • Génération   │         │  - assign_checkins  │
       │   rapports     │         │  - record_checkin   │
       │                │         │  - escalate         │
       │ Fallback:      │         │                     │
       │ OpenAI/Whisper │         │ Python + mcp SDK    │
       │ si Slack AI    │         │ Deployé Railway     │
       │ indisponible   │         │ Port 8000           │
       └───────┬────────┘         └──────┬──────────────┘
               │                         │
               │                 ┌───────▼───────────────┐
       ┌───────▼────────┐        │ 5. EXTERNAL APIs      │
       │ REAL-TIME      │        │                       │
       │ SEARCH API     │        │ • Météo-France        │
       │                │        │   (vigilance)         │
       │ • Directives   │        │ • NWS Weather API     │
       │   sanitaires   │        │   (US fallback)       │
       │ • Communiqués  │        │ • OpenStreetMap       │
       │   ARS          │        │   Overpass (POIs)     │
       │ • News locale  │        │ • INSEE (démographie) │
       │                │        │ • data.gouv.fr        │
       │ Cache Redis    │        │   (schéma canicule)   │
       │ ou SQLite      │        │ • WHO Global Health   │
       │ TTL 30 min     │        │   Observatory         │
       └────────────────┘        └───────────────────────┘
```

---

## Composants détaillés

### 1. Slack Workspace (sandbox)

Le workspace `Reseau-Soligarde-Paris` contient :

| Channel | Type | Rôle |
|---------|------|------|
| `#cellule-crise` | Public | Coordination globale, escalades critiques, rapports quotidiens |
| `#secteur-1` à `#secteur-12` | Public | Check-in des bénévoles par arrondissement |
| `#voisins-1` à `#voisins-12` | Public | Communication avec voisins référents |
| DMs bénévole ↔ Vigie | Privé | Affectation des check-in, retours de bénévoles |

Autres surfaces Slack utilisées :
- **App Home** : dashboard personnel du bénévole (5 KPI temps réel, liste du jour)
- **Canvas partagé** : vue cellule de crise (taux de couverture, escalades en cours)
- **Lists** : check-in assignments structurés
- **Modals** : saisie structurée (signaler anomalie, réassigner, escalader)

12 utilisateurs simulés (bénévoles) + 2 coordinateurs médicaux + 50 fiches bénéficiaires simulées.

### 2. Bolt App (Python)

**Stack** : Python 3.11 + slack_bolt ≥ 1.20 + slack_sdk ≥ 3.27

**Handlers** (dans `app/handlers/`) :
- `events.py` : app_mention, app_home_opened, message.im, file_shared, reaction_added, member_joined_channel
- `commands.py` : /vigie, /vigie-checkin, /vigie-escalate, /vigie-report, /vigie-simulate
- `actions.py` : vigie_start_calls, vigie_record_checkin, vigie_escalate_1/2/3, vigie_close_checkin, vigie_confirm_pharmacy, shortcuts
- `views.py` : vigie_modal_checkin, vigie_modal_anomaly, vigie_modal_reassign, vigie_modal_escalate

**Block Kit builders** (dans `app/blocks/`) :
- `dashboard.py` : App Home
- `checkin.py` : messages sectoriels de check-in
- `escalation.py` : messages d'escalade
- `reports.py` : rapport quotidien

**Deployment** :
- Dev : Socket Mode (pas d'URL publique requise)
- Prod : Railway / Render, HTTPS endpoint, signature verification

**OAuth scopes** : voir `manifest/app-manifest.yaml` — 20+ scopes incluant `assistant:write` (Slack AI), `canvas:write`, `lists:write`.

### 3. Slack AI Layer

Quatre tâches distinctes :

1. **Transcription** : notes vocales bénévoles → texte (Slack AI audio translation si dispo, sinon OpenAI Whisper API via MCP)
2. **Extraction JSON** : texte libre → `{state, weak_signals, action_required}` (Slack AI ou LLM via OpenAI fallback)
3. **Classification 4 niveaux** : `{OK, weak_signal, escalate_coord, critical_samu}` (prompt structuré, JSON schema validation)
4. **Génération rapports** : agrégation des check-ins du jour → rapport quotidien 18h00 (Slack AI summary)

Fallback : si Slack AI indisponible dans le sandbox, OpenAI gpt-4o-mini + Whisper-1 via variables d'environnement.

### 4. MCP Server

**Stack** : Python 3.11 + anthropic-mcp SDK (FastMCP) + httpx

**Transport** : streamable-http (production), stdio (test local avec MCP Inspector)

**Resources** (3) :

| URI | Description |
|-----|-------------|
| `vigie://beneficiary-registry` | Registre Plan Canicule (50 fiches simulées) |
| `vigie://beneficiary-registry/{id}` | Bénéficiaire spécifique par ID |
| `vigie://weather-alerts` | Toutes les alertes Météo-France + NWS actives |
| `vigie://weather-alerts/department/{dep}` | Alertes pour un département français |
| `vigie://community-pois/{lat}/{lon}/{radius_m}` | POIs OpenStreetMap autour d'un point |
| `vigie://community-pois/sector/{sector_id}` | POIs pour un secteur Vigie |
| `vigie://community-pois/neighbor-referent/{sector_id}` | Voisin référent d'un secteur |

**Tools** (3) :

| Tool | Description |
|------|-------------|
| `assign_checkins(volunteer_ids, date, sector_filter)` | Affecte les check-in du jour aux bénévoles |
| `record_checkin(beneficiary_id, volunteer_id, transcript, channel_type)` | Enregistre un retour + classification + POI |
| `escalate(beneficiary_id, level, triggered_by, reason)` | Déclenche une escalade niveau 1/2/3 |

**Auth** : token partagé (MCP_SERVER_TOKEN) validé sur chaque appel HTTP.

### 5. External APIs

| API | Usage | Auth | Rate limit |
|-----|-------|------|------------|
| Météo-France vigilance | Alertes canicule France | Bearer token | 60 req/min |
| NWS Weather API | Alertes US (fallback) | Aucune | 60 req/min |
| OpenStreetMap Overpass | POIs (pharmacies, hôpitaux, points d'eau) | Aucune | 2 req/sec |
| INSEE | Démographie par commune | Bearer token | 30 req/min |
| data.gouv.fr | Schéma registre canicule | Aucune | — |
| WHO Global Health Observatory | Indicateurs heat-health | Aucune | — |
| Real-Time Search API (Slack) | Directives sanitaires fraîches | API key | configurable |

---

## Flux de données type (un check-in)

```
[07:30] Vigie (Bolt app) → MCP: assign_checkins(volunteer_ids=all, date=today)
        ↓ MCP server renvoie {assignments: [...]}
[07:30] Vigie → Slack: DM à Marie (volunteer) avec liste de 5 bénéficiaires
        ↓ Marie clique "Démarrer les appels"
[08:15] Marie → Slack DM Vigie: note vocale "Mme Dupont fatiguée, demande médicaments"
        ↓ Bolt app intercepte le message
[08:15] Bolt app → Slack AI: transcription + extraction JSON
        ↓ Slack AI renvoie {transcript, state, signals, recommended_action}
[08:16] Bolt app → MCP: record_checkin(B023, U_MARIE, transcript, "voice")
        ↓ MCP classifie (level 1, medication_request) + fetch POI pharmacie
        ↓ MCP renvoie {anomaly_level, suggested_pois, sector_message}
[08:16] Bolt app → Slack #secteur-11: post sector_message + Block Kit buttons
        ↓ Coordinateur voit le message, peut confirmer pharmacie / escalader / clôturer
[18:00] Bolt app → Slack AI: génère rapport quotidien agrégé
[18:00] Bolt app → Real-Time Search: récupère directives ARS du jour
[18:00] Bolt app → Slack #cellule-crise: post rapport avec citations fraîches
```

Temps total check-in : 2 min 10 s en moyenne (vs 8 min sans Vigie).
Temps total escalade anomalie : 4 min 30 s (vs 45 min sans Vigie).

---

## Schéma de données

### Beneficiary (JSON)

```json
{
  "id": "B001",
  "first_name": "Hélène",
  "last_initial": "M",
  "age": 82,
  "gender": "F",
  "sector": 11,
  "address": {
    "street": "12 Rue des Lilas",
    "postal_code": "75011",
    "city": "Paris",
    "lat": 48.8590,
    "lon": 2.3790
  },
  "phone": "+33 6 12 34 56 78",
  "emergency_contacts": [
    {"type": "neighbor_referent", "name": "M. Bernard", "phone": "+33..."},
    {"type": "doctor", "name": "Dr Martinez", "phone": "+33..."}
  ],
  "medical_conditions": ["hypertension", "arthrose"],
  "medications": ["antihypertenseur", "antalgique"],
  "vulnerability_score": 67,
  "isolation_level": "medium",
  "notes": null,
  "last_checkin_at": null,
  "status": "registered"
}
```

### Volunteer (JSON)

```json
{
  "id": "V01",
  "slack_user_id": "U0XXXXX",
  "name": "Marie Dupont",
  "sector": 11,
  "role": "volunteer",
  "availability": {
    "weekday_morning": true,
    "weekday_afternoon": false,
    "weekend": true,
    "max_checkins_per_day": 5
  },
  "languages": ["fr", "en"],
  "training_completed": ["plan_canicule_basics", "deontology"]
}
```

### Check-in record (runtime)

```json
{
  "checkin_id": "C-B023-1752686400",
  "beneficiary_id": "B023",
  "volunteer_id": "U0XXXXX",
  "timestamp": "2026-07-15T08:15:00+02:00",
  "channel_type": "voice",
  "transcript": "Mme Dupont fatiguée, demande renouvellement ordonnance antihypertenseur",
  "anomaly_level": 1,
  "anomaly_label": "Signal faible",
  "detected_signals": ["medication_request"],
  "recommended_action": "pharmacy",
  "suggested_pois": [
    {"type": "pharmacy", "name": "Pharmacie des Lilas", "distance_m": 200}
  ],
  "sector_message": "..."
}
```

### Escalation record (runtime)

```json
{
  "escalation_id": "E-B003-L3-1752688000",
  "beneficiary_id": "B003",
  "level": 3,
  "triggered_by": "U0XXXXX",
  "reason": "Pas de réponse × 3, voisin a trouvé Mme Martin au sol",
  "actions_taken": [
    "status_updated_to_critical",
    "context_summary_generated",
    "medical_coordinator_dm_queued",
    "samu_protocol_triggered",
    "samu_button_added_to_cellule_crise",
    "neighbor_referent_dm_queued"
  ],
  "samu_triggered": true,
  "context_summary": "...",
  "cellule_crise_message": "..."
}
```

---

## Sécurité et conformité

### OAuth scopes (principe de moindre privilège)

Vigie demande 20+ scopes Slack, tous nécessaires :
- `chat:write` (post messages)
- `assistant:write` (Slack AI)
- `canvas:write` (cellule de crise)
- `lists:write` (check-in assignments)
- Pas de `admin.*` scopes, pas de `team:write`

### Authentification MCP

- Transport streamable-http avec token partagé (`MCP_SERVER_TOKEN`)
- Toutes les requêtes validées via header `Authorization: Bearer <token>`
- Rotation de token possible via variable d'environnement

### Données bénéficiaires (RGPD)

- Aucune donnée réelle de bénéficiaire dans la démo
- Toutes les fiches sont simulées, générées par `scripts/generate_beneficiaries.py`
- Disclaimer dans chaque fiche : `"SIMULATED — no real beneficiary data"`
- En production (post-hackathon) : chiffrement au repos (AES-256), anonymisation des logs, conservation 90 jours max

### Logs structurés

- Format JSON via `structlog`
- Aucune donnée personnelle dans les logs (PII redacted)
- Niveau DEBUG pour le dev, INFO pour la prod, WARNING pour les appels externes
- Conservation 30 jours sur Railway

---

## Diagramme de soumission

Format final du diagramme d'architecture à soumettre au hackathon :
- **Format** : PNG 1600×1200 ou SVG
- **Outil** : Mermaid (avec thème Slack) ou Excalidraw
- **Style** : couleurs Slack officielles
  - Aubergine : `#4A154B`
  - Aloe : `#36C5F0`
  - Vert : `#2EB67D`
- **Encarts** : "Métriques temps réel" (5 KPI) + "Tech stack" + "Pacte 1-1-1"

Le diagramme sera produit le J9 (10 juillet 2026) à partir de ce document.

---

## Plan de déploiement

### Sandbox (développement)

1. Workspace Slack free tier `Reseau-Soligarde-Paris`
2. App Slack créée depuis `manifest/app-manifest.yaml`
3. Socket Mode activé (pas d'URL publique)
4. MCP server en local (`python -m mcp_server.server`, transport stdio)
5. Bolt app en local (`python -m app.main`, Socket Mode)
6. Données simulées dans `mcp_server/data/*.json`

### Production (demo juges)

1. Deploy Railway :
   - Service 1 : Bolt app (`vigie-bot`)
   - Service 2 : MCP server (`vigie-mcp`)
2. Variables d'environnement : `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_APP_TOKEN`, `MCP_SERVER_TOKEN`, etc.
3. HTTPS endpoint Railway pour Slack Event API + Interactivity
4. Sandbox Slack partagé avec `slackhack@salesforce.com` et `testing@devpost.com`

### Post-hackathon (si victoire)

1. Migration vers AWS Lambda + API Gateway (Bolt app) et ECS Fargate (MCP server)
2. Cache Redis managé (ElastiCache) pour RTS API
3. Base de données PostgreSQL pour les check-ins (remplace JSON)
4. Déploiement multi-tenant (1 workspace ONG = 1 tenant)
5. OAuth Slack standard pour installation par ONG tierces

---

## Tests

### Tests unitaires - `tests/test_assign_checkin.py` : distribution, gestion erreurs
- `tests/test_classify_anomaly.py` : 4 niveaux de classification
- `tests/test_escalate.py` : escalade level 1/2/3, erreurs

Coverage target : ≥ 80 % sur `app/` et `mcp_server/`.

### Tests d'intégration - Scénario canicule complet rejoué en accéléré
- Vérification : 50 check-in → 5 escalades → 1 critique → rapport 18h00

### Tests manuels - 3 comptes Slack externes (amis / famille) testent le sandbox
- Scénario : ouvrir Slack, recevoir DM, faire un check-in, escalader
- Capture des frictions → corrections J8

---

## Références

- Règles officielles hackathon : `/home/z/my-project/upload/Pasted Content_1782947530966.txt`
- POINT.md (vision) : `/home/z/my-project/POINT.md`
- POINT.D.md (critères) : `/home/z/my-project/POINT.D.md`
- Slack Bolt Python : https://slack.dev/bolt-python/tutorial/getting-started
- MCP spec : https://modelcontextprotocol.io
- Météo-France API : https://portail-api.meteofrance.fr/
- OpenStreetMap Overpass : https://overpass-api.de/
