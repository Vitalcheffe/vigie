# POINT.D.md — Master reference VIGIE (critères, règles, notation)

> **OBLIGATION ABSOLUE** : Relire ce fichier au debut de CHAQUE conversation mentionnant Vigie. Ce fichier est le dictionnaire des regles du jeu. Aucune decision de design, technique, ou de soumission ne doit etre prise sans verifier ce fichier.
>
> Cree le : 1er juillet 2026
> Source principale : Slack Agent Builder Challenge Official Rules (409 lignes), doc ressources officielle
> Statut : Evolutif (completer au besoin, mais ne jamais retirer d'info)
> Companion file : POINT.md (immutable)

---

## SOMMAIRE

1. Le hackathon en bref
2. Les 3 filieres (tracks) — règles détaillées
3. Les 3 technologies obligatoires
4. Les 4 criteres de jugement — décodage complet
5. Le processus de jugement en 2 stages
6. Le tie-break — comment gagner les duels
7. Les exigences de soumission — checklist complète
8. Les prix — structure complète
9. L'éligibilité et contraintes
10. La timeline critique
11. Les pièges à éviter (top 20)
12. Les règles implicites (sociologiques)
13. Le code de Vigie — règles internes du projet
14. Les sources et références
15. Rappel de lecture obligatoire

---

## 1. LE HACKATHON EN BREF

| Element | Valeur |
|---------|--------|
| Nom officiel | Slack Agent Builder Challenge |
| Sponsor | Salesforce, Inc. |
| Administrateur | Devpost, Inc. |
| Cash total | USD $42,000 |
| ARV total (avec Dreamforce, certs, swag) | USD $74,400 |
| Participants inscrits | 3,348 |
| Nombre de prix | 9 categories (3 tracks x 2 places + 3 bonus) |
| Taille d'équipe max | 4 personnes |
| Âge min | 18 ans |
| Pays éligibles | Liste restreinte (vérifier règles officielles §3) |
| Période de soumission | 20 mai 2026 10h PT → 13 juillet 2026 17h PT |
| Période de jugement | 14 juillet → 6 août 2026 |
| Annonce vainqueurs | 11 août 2026 14h PT |
| Channel communauté | #slack-agent-builder-challenge (Slack Community) |

---

## 2. LES 3 FILIERES (TRACKS) — REGLES DETAILLEES

### 2.1 New Slack Agent Track

**Definition** : Un nouvel agent Slack (jamais publie avant) utilisant au moins 1 des 3 technologies. Pas de contrainte Marketplace. Sandbox suffit.

**Contraintes** :
- Projet original, jamais publie
- Au moins 1 technologie utilisée
- Sandbox accessible aux juges
- Vidéo démo < 3 min
- Diagramme architecture
- Description texte

**Prix** :
- 1er : $8,000 cash + voucher Slack Developer Certification ($200/pers) + voucher Dreamforce 2026 ($2,299/pers) + voucher Slack swag ($200/pers) + invitation Slack community gathering à Dreamforce + features newsletter/social
- 2e : $4,000 cash + features newsletter/social

**Concurrence estimée** : ~720 soumissions (la plus contestée)

### 2.2 Slack Agent for Good Track

**Definition** : Un nouvel agent Slack utilisant au moins 1 des 3 technologies, adressant un problème d'impact social réel (accessibilité, éducation, opportunité économique, environnement, santé publique, opérations ONG).

**Contraintes spécifiques** :
- Description d'impact OBLIGATOIRE dans la soumission
- Pas de contrainte Marketplace
- Sandbox suffit

**Prix** : identiques au track New Slack Agent (1er et 2e)

**Concurrence estimée** : ~350 soumissions (sous-participée)

### 2.3 Slack Agent for Organizations Track

**Definition** : Agent Slack destine au marché entreprise, soumis au Slack Marketplace avant la deadline.

**2 options** :
- **New Agent** : nouvelle app soumise au Marketplace
- **Existing Agent** : mise à jour significative d'une app Marketplace existante

**Contraintes spécifiques** :
- Soumission Marketplace OBLIGATOIRE avant 13 juillet 17h PT
- Installation dans 5 workspaces actifs minimum
- Déploiement dans un workspace de PRODUCTION (pas le sandbox)
- Slack App ID à fournir dans la soumission
- Si existing app : décrire les updates faites pendant la période
- Respect des Slack Marketplace Core Guidelines

**Subtilité critique** : le sandbox développeur est pour les tests et le jugement UNIQUEMENT. L'app doit vivre dans un workspace de production réel.

**Prix** :
- 1er : $8,000 + vouchers + Dreamforce + invitation community gathering + features newsletter/social + 30 min conversation virtuelle avec un Slack product executive + app featured sur Stack Overflow podcast
- 2e : $4,000 + features newsletter/social

**Concurrence estimée** : ~150 soumissions (la moins contestée mais la plus risquée)

---

## 3. LES 3 TECHNOLOGIES OBLIGATOIRES (au moins 1)

### 3.1 Slack AI capabilities & Agent Builder

**Definition** : Capacités IA natives de Slack. Résumés automatiques, recherche IA, Agentforce Agent, Slack AI threads summary, Slack AI search.

**Comment l'utiliser pour Vigie** :
- Transcription notes vocales bénévoles
- Extraction structurée JSON depuis langage naturel
- Classification d'anomalies (4 niveaux)
- Génération rapports quotidiens
- Synthèses de threads cellule de crise

**Template starter** : HR, IT, Sales, Support (Agent Builder)

### 3.2 MCP (Model Context Protocol) server integration

**Definition** : Serveur exposant tools/resources/prompts via le protocole MCP (standard Anthropic ouvert). Connecte des sources externes à un agent Slack.

**Comment l'utiliser pour Vigie** :
- Resource `beneficiary_registry` (registre Plan Canicule)
- Resource `weather_alerts` (Météo-France / NWS)
- Resource `community_pois` (OpenStreetMap Overpass)
- Tool `assign_checkins(volunteer_id, date)`
- Tool `record_checkin(beneficiary_id, transcript)`
- Tool `escalate(beneficiary_id, level)`

**SDK** : anthropic-mcp (Python officiel ou TypeScript)

### 3.3 Real-Time Search (RTS) API

**Definition** : API de recherche temps réel pour surfaçer contexte frais dans le workspace et externe.

**Comment l'utiliser pour Vigie** :
- Directives sanitaires courantes (Ministère, ARS, CDC, WHO)
- Actualités locales canicule
- Communiqués de mairies / EHPAD
- Citations contextuelles fraîches dans les messages Vigie

### 3.4 Règle critique

Le projet doit utiliser AU MOINS 1 des 3. Mais utiliser les 3 maximise le score "Technological Implementation" et différencie des 80 % de soumissions qui n'en utilisent qu'une.

---

## 4. LES 4 CRITERES DE JUGEMENT — DECODAGE COMPLET

### Règle officielle (§6)

> "Entries will be judged on the following equally-weighted criteria:
> - Technological Implementation
> - Design
> - Potential Impact
> - Quality of the Idea"

**Equipondération 25 % chacun. Pas de critère prioritaire affiché.**

### 4.1 Technological Implementation (25 %)

**Question officielle** : "Does the project demonstrate quality software development? Does the project leverage at least one of these three technologies: Slack AI capabilities, MCP server integration, or real-time search API? How is the quality of the code?"

**Decode — ce que les juges cherchent vraiment** :
- Code lisible, structuré, idiomatique
- Utilisation POUSSÉE de la techno (pas cosmétique)
- MCP server custom codé from scratch = bonus massif
- Combinaison des 3 technos = score maximum
- Tests unitaires visibles
- Gestion d'erreurs
- Pas de "wrapping" d'un LLM générique en Slack UI
- Logs, monitoring, observabilité
- Code open-source avec README soigné

**Ce qui tue ce critère** :
- Template Agent Builder non modifié
- Slack AI appelé une fois pour faire joli
- MCP server basique type "hello world"
- Code spaghetti sans structure
- Pas de gestion d'erreur
- "Slack wrapper around ChatGPT"

**Score max Vigie visé** : 9-10/10
- MCP server custom 3 resources + 3 tools (rare)
- Slack AI utilisé pour 4 tâches distinctes (transcription, extraction, classification, rapports)
- Real-Time Search API avec cache et citations
- Tests unitaires
- Code Python idiomatique
- README détaillé

### 4.2 Design (25 %)

**Question officielle** : "Is the user experience and design of the project well thought out? Is there a balanced blend of frontend and backend in the software?"

**Decode — ce que les juges cherchent vraiment** :
- UX Slack-native (channels, DMs, App Home, modals, Block Kit, canvas, lists, huddles)
- Pas de "wrapper Slack UI around generic chatbot"
- Frontend (= Slack UI) soigné : Block Kit bien composé, modals interactifs, boutons clairs
- Backend (= MCP + Bolt app) bien architecturé
- Équilibre frontend/backend (pas 100 % backend avec UI nulle, pas 100 % frontend sans profondeur)
- Cohérence visuelle (typo, couleurs, ton)
- Mobile-friendly (50 % des utilisateurs Slack sont mobile)
- Accessibility (contrast, alt text, screen reader friendly)
- Iconographie soignée
- Dashboard temps réel visible

**Ce qui tue ce critère** :
- Messages texte plat sans Block Kit
- Boutons "OK" / "Cancel" génériques
- Pas de modals
- Pas d'App Home
- Pas de canvas ou lists
- Code couleur incohérent
- Slack UI minimaliste pour backend massif (ou inverse)

**Score max Vigie visé** : 9-10/10
- App Home avec dashboard 5 KPI temps réel
- Block Kit avec boutons contextuels "Confirmer / Escalader / Clôturer"
- Modals pour saisie structurée
- Canvas partagé "Cellule de crise - Vue temps réel"
- Lists pour check-in assignments
- Couleurs Slack officielles (aubergine #4A154B, aloe #36C5F0, vert #2EB67D)
- Iconographie météo / médical / urgence cohérente
- Ton éditorial sobre mais humain

### 4.3 Potential Impact (25 %)

**Question officielle** : "How big of an impact could the project have on the Slack community? How big of an impact could it have beyond the target community?"

**Decode — ce que les juges cherchent vraiment** :
- Problème réel, pas inventé
- Chiffres sourcés (pas "des milliers" mais "14 802 selon InVS 2003")
- Population cible claire (qui bénéficie)
- Métrique process démontrable (taux, latence, etc.)
- Projection réaliste d'adoption (10 reseaux, 100 reseaux, etc.)
- Alignement avec un protocole public (Plan Canicule, CDC, WHO)
- Alignement avec la culture Salesforce (1-1-1, Slack for Nonprofits)
- Impact au-delà de la cible (ex : Vigie applicable à d'autres types d'isolement)
- Storytelling émotionnel mais pas manipulateur

**Ce qui tue ce critère** :
- "Ce projet aide les gens" sans chiffres
- Problème inventé ou exagéré
- Pas de population cible claire
- Métrique abstraite non démontrable
- Aucun protocole public référencé
- Charity washing (émotion sans fondement)
- "World peace" sans ancrage réel

**Score max Vigie visé** : 10/10
- 14 802 morts 2003 (InVS), 61 672 morts 2022 (Nature Medicine)
- 530 000 seniors en mort sociale (Petits Frères des Pauvres)
- 30-50 % non contactés en alerte orange (Cour des comptes)
- Métriques process : 95 % vs 38 % couverture, 2min10 vs 8min check-in, 4min30 vs 45min escalade
- Protocoles : Plan Canicule (Décret 2006-1089), CDC Heat & Health, WHO Heat-Health Action Plans
- Alignement Salesforce 1-1-1 explicite

### 4.4 Quality of the Idea (25 %)

**Question officielle** : "How creative and unique is the project? Does the concept exist already? If so, how much does the project improve on it?"

**Decode — ce que les juges cherchent vraiment** :
- Concept qui n'existe pas déjà (vérifier : pas de concurrent direct)
- Si existe, amélioration majeure (10x pas 10 %)
- Twist conceptuel (inversion de paradigme, angle inattendu)
- Nom mémorable et brandable
- Tagline qui accroche
- Démonstration que le concept est "évident en retrospect"
- Combinaison inédite (Slack + canicule = combo jamais vu)

**Ce qui tue ce critère** :
- "Encore un chatbot RH"
- Concept existant sans amélioration majeure
- Wrapper Slack d'un produit existant
- Nom générique ("HelpBot", "SeniorCareBot")
- Pas de twist conceptuel
- Idée évidente que tout le monde avait

**Score max Vigie visé** : 9-10/10
- "Slack + canicule + seniors isoles" = combo inédit
- Inversion : "l'agent qui sait quand quelqu'un a besoin, pas qui demande"
- Nom Vigie (5 lettres, brandable, bilingue, connotation protection)
- Tagline : "Pour que la canicule ne tue plus en silence"
- Aucun concurrent direct identifié

---

## 5. LE PROCESSUS DE JUGEMENT EN 2 STAGES

### Stage 1 — Pass/fail (baseline viability)

**Question** : Le projet respecte-t-il les Submission Requirements ?

**Filtres automatiques** :
- Track identifié
- Texte descriptif fourni
- Vidéo < 3 min avec footage du projet fonctionnant
- Diagramme architecture
- URL sandbox Slack avec accès aux 2 emails (slackhack@salesforce.com + testing@devpost.com)
- Pour Organizations : Slack App ID fourni
- Langue : anglais ou traduction anglaise fournie
- Pas de contenu inapproprié / malware / IP volé

**Taux de passage Stage 1 historique Devpost** : 60-70 % des soumissions.

### Stage 2 — Scoring (les 4 critères equipondérés)

Chaque projet recevant un score sur 4 critères x 25 %. Score total / 100.

**Ordre de jugement** :
- Jugement en 1 ou plusieurs rounds
- Panel peut inclure juges Slack/Salesforce + 1+ externe
- Possibilité de jugement assisté par IA (les règles le mentionnent explicitement)
- Revue humaine finale

**Temps de jugement par projet** : 5-7 minutes en moyenne selon la doc officielle. Donc :
- 60 premières secondes : critique (première impression)
- Vidéo de 3 min : cœur du jugement
- Diagramme + description : 1-2 min de scan
- Test sandbox : 1-2 min de validation

---

## 6. LE TIE-BREAK — COMMENT GAGNER LES DUELS

### Règle officielle (§6)

> "For each Prize Category listed below, if two or more Submissions are tied, the tied Submission with the highest score in the first applicable criterion listed above will be considered the higher scoring Submission. The order is: Technological Implementation, Design, Potential Impact, Quality of the Idea."

### Decode strategique

L'ordre du tie-break est : **Tech → Design → Impact → Idée**

Cela signifie :
1. **Tech est le critère ROI** du tie-break. Si on est ex aequo avec un concurrent, on gagne si on a meilleur Tech.
2. **Impact arrive en 3e position**. Pour un projet For Good, c'est surprenant. Cela signifie qu'un projet For Good avec tech faible perdra en tie-break contre un projet moins impactant mais tech-fort.
3. **Idée est le critère le moins important en tie-break**. Même une idée brillante ne sauvera pas une tech faible.

### Implication pour Vigie

- **Tech doit etre excellent** : MCP server custom + Slack AI + RTS = score 9-10/10 pour gagner les duels
- **Design doit etre impeccable** : Slack-native pur, Block Kit soigné
- **Impact** : score 10/10 (Hélène, 14 802 morts) — mais ça ne sauvera pas une tech faible
- **Idée** : bon score mais ne pas s'y reposer

### Règle implicite decoulant du tie-break

> "Pour Vigie, investir 1h de plus dans Tech vaut mieux que 1h de plus dans Idée."

Si on hésite entre 2 tâches, prioriser Tech > Design > Impact > Idée.

---

## 7. LES EXIGENCES DE SOUMISSION — CHECKLIST COMPLETE

### 7.1 Pour tous les tracks

- [ ] **Track identifié** dans le formulaire Devpost
- [ ] **Description texte** : 800-1 500 mots en anglais (ou traduction anglaise fournie)
  - Section Problem
  - Section Solution
  - Section How it works
  - Section Technologies used (mention explicite des 3 si possible)
  - Section Impact (obligatoire pour For Good)
  - Section Sources and credits
- [ ] **Vidéo démo** < 3 min (judges not required to watch beyond 3 min)
  - Upload YouTube, Vimeo, Facebook Video ou Youku
  - Lien public ou non-listé accessible
  - Footage du projet fonctionnant sur device cible
  - Pas de musique copyrightée sans permission
  - Pas de trademarks tierces sans permission
  - Pas de contenu confidentiel / sensible
  - Sous-titres anglais (recommandé même si vidéo en anglais)
- [ ] **Diagramme architecture** (PNG ou SVG haute résolution)
- [ ] **URL sandbox Slack** accessible aux 2 emails :
  - slackhack@salesforce.com
  - testing@devpost.com
- [ ] **Repo GitHub public** (recommandé, pas explicitement requis mais fort bonus)
- [ ] **Œuvre originale** sans violation IP

### 7.2 Spécifique Organizations Track

- [ ] **Slack App ID** fourni (preuve de soumission Marketplace)
- [ ] Si existing app : description des updates faites pendant la période
- [ ] App déployée en production workspace (pas sandbox)
- [ ] App installée dans 5 workspaces actifs minimum
- [ ] Respect Slack Marketplace Core Guidelines

### 7.3 Spécifique For Good Track

- [ ] **Description d'impact** explicite (mentionner dans le texte de soumission)
  - Problème chiffré
  - Population cible
  - Métrique process
  - Protocole public référencé
  - Engagement éthique (pas de données réelles de bénéficiaires, simulation only)

### 7.4 Règles transversales (§4.6)

- Ne pas porter préjudice au Sponsor
- Pas de contenu inapproprié
- Pas de malware / virus
- Pas de code source non public
- Si team : un Representative autorisé

---

## 8. LES PRIX — STRUCTURE COMPLETE

### 8.1 Cash prizes

| Prix | Cash | Nombre |
|------|------|--------|
| 1er New Slack Agent | $8,000 | 1 |
| 2e New Slack Agent | $4,000 | 1 |
| 1er For Good | $8,000 | 1 |
| 2e For Good | $4,000 | 1 |
| 1er Organizations | $8,000 | 1 |
| 2e Organizations | $4,000 | 1 |
| Best UX | $2,000 | 1 |
| Most Innovative | $2,000 | 1 |
| Best Technological Implementation | $2,000 | 1 |
| **Total cash** | **$42,000** | **9** |

### 8.2 Non-cash prizes (1er prix des 3 tracks)

Par membre d'équipe (jusqu'à 4) :
- Voucher Slack Developer Certification (ARV $200/pers)
- Voucher Dreamforce 2026 full conference pass (ARV $2,299/pers)
- Voucher Slack community swag (ARV $200/pers)
- Invitation à Slack community gathering à Dreamforce 2026
- Features sur Slack Developer program website, newsletter, social

### 8.3 Bonus spécifiques

- 1er Organizations : 30 min conversation virtuelle avec Slack product executive + app featured sur Stack Overflow podcast
- Tous 1er prix : interview sociale à Dreamforce 2026 (sous condition de présence)

### 8.4 Cash total maximum théorique pour un projet

Un seul projet peut gagner AU MAXIMUM :
- 1er prix de son track : $8,000
- Best UX : $2,000
- Best Technological Implementation : $2,000
- Most Innovative : $2,000

Soit **$14,000 cash max** par projet (si balayage complet). Plus les vouchers non-cash.

### 8.5 EV (expected value) pour Vigie

Avec exécution top 1 % :
- P(1er For Good) = 14 % × $8,000 = $1,120
- P(2e For Good) = 15 % × $4,000 = $600
- P(Best UX) = 12 % × $2,000 = $240
- P(Most Innovative) = 15 % × $2,000 = $300
- P(Best Tech) = 10 % × $2,000 = $200
- **EV cash** ≈ **$2,460**
- **EV non-cash** (vouchers + visibilité) ≈ $15,000-20,000 équivalent marketing

---

## 9. L'ÉLIGIBILITÉ ET CONTRAINTES

### 9.1 Éligibilité (§3)

- 18 ans minimum
- Pays éligibles : liste restreinte (vérifier règles officielles). France et USA inclus typiquement.
- Employés Salesforce/Devpost et leur famille : non éligibles
- Conflit d'intérêt : projet ne doit pas avoir reçu financement Salesforce préalable

### 9.2 Taille d'équipe

- Jusqu'à 4 personnes (Eligible Individuals)
- 1 Representative pour soumission
- Distribution des prix : responsabilité du Representative

### 9.3 Soumissions multiples

- Un Entrant peut soumettre plusieurs projets, à condition qu'ils soient substantiellement différents

### 9.4 Langue

- Tous les matériaux en anglais OU traduction anglaise fournie (vidéo, description, instructions de test)

### 9.5 IP

- Le projet reste propriété de l'Entrant
- Salesforce obtient licence irrévocable, royalty-free, mondiale pour usage promotionnel
- Pas d'obligation d'utilisation par Salesforce

---

## 10. LA TIMELINE CRITIQUE

### 10.1 Timeline officielle

| Date | Événement |
|------|-----------|
| 20 mai 2026 10h PT | Début soumission |
| 13 juillet 2026 17h PT | **Deadline soumission** (= 13 juillet ~2h du matin heure de Paris, 14 juillet 1h du matin GMT+1) |
| 14 juillet 2026 11h PT | Début jugement |
| 6 août 2026 11h PT | Fin jugement |
| 11 août 2026 14h PT | **Annonce vainqueurs** |

### 10.2 Timeline Vigie (12 jours restants, à partir du 1er juillet 2026)

| Jour | Date | Tâche principale | Jalon GO/NO-GO |
|------|------|------------------|----------------|
| J1 | 2 juillet | Cadrage + sandbox Slack | Workspace + app fonctionnelle |
| J2 | 3 juillet | MCP server v1 | 3 resources exposées |
| J3 | 4 juillet | Slack AI layer | 80 % précision classification |
| J4 | 5 juillet | Workflow check-in | Check-in complet bout-en-bout |
| J5 | 6 juillet | Workflow escalade | Escalade critique < 5 min |
| J6 | 7 juillet | RTS API + reporting | Rapport quotidien avec citations |
| J7 | 8 juillet | Dashboard métriques | Dashboard visible dans vidéo |
| J8 | 9 juillet | Polish UX | Aucune friction bloquante |
| J9 | 10 juillet | Diagramme + texte | Documentation complète |
| J10 | 11 juillet | Scénario vidéo | Scènes émotionnelles en boîte |
| J11 | 12 juillet | Tournage + montage | Vidéo < 3 min quasi-finalisée |
| J12 | 13 juillet | **Soumission** | Devpost validé avant 17h PT |

### 10.3 Marge de sécurité

- Deadline : 13 juillet 17h PT
- Vigie vise soumission : 13 juillet 16h45 PT (15 min avant)
- Marge : 15 minutes (minimum acceptable)
- Idéalement : soumettre J12 matin pour avoir 6h de marge

---

## 11. LES PIÈGES À ÉVITER (TOP 20)

### Pièges techniques

1. **MCP server trop ambitieux** : viser 10 tools = crash. Stick to 3 resources + 3 tools.
2. **Slack AI indisponible en sandbox** : avoir fallback Whisper API via MCP.
3. **Sandbox Slack expiré** : tester accès 24h avant deadline.
4. **Token Slack expiré** : utiliser refresh token, pas access token long-lived.
5. **MCP server non déployé** : héberger sur Railway, pas localhost.
6. **Code sans gestion d'erreur** : chaque appel API externe = try/except + log.
7. **Pas de tests** : au moins tests unitaires sur les fonctions critiques (assign_checkin, classify_anomaly).

### Pièges vidéo

8. **Vidéo plate** : 60 premières secondes doivent marquer émotionnellement.
9. **Musique copyright** : YouTube Audio Library uniquement.
10. **Pas de sous-titres anglais** : requis pour juges non-francophones.
11. **Vidéo > 3 min** : judges not required to watch beyond. Coupé à 2:55 max.
12. **Démo live qui crash** : toujours pre-recorded scenario, jamais live demo.
13. **Vidéo trop "charity"** : segment tech doit être dense pour désamorcer.

### Pièges soumission

14. **URL sandbox non accessible** : tester avec compte externe avant submit.
15. **Description impact manquante** (For Good) : obligatoire, sinon Stage 1 fail.
16. **Diagramme architecture illisible** : haute résolution, format SVG ou PNG 1600×1200+.
17. **Accès emails juges oubliés** : slackhack@salesforce.com ET testing@devpost.com dans le sandbox.
18. **Submit à la dernière minute** : Devpost peut crasher sous charge. Submit J12 matin.

### Pièges stratégiques

19. **Charity washing perçu** : tech faible + émotion forte = disqualification morale par les juges. Tech doit être dense.
20. **Scope creep** : ajouter un dashboard web / app mobile / etc. = mort. Stick to Slack-native.

---

## 12. LES RÈGLES IMPLICITES (SOCIOLOGIQUES)

### 12.1 Le biais Salesforce 1-1-1

Le modèle 1-1-1 (1 % temps, 1 % produit, 1 % equity) est central à l'identité Salesforce depuis 1999. Les juges Slack/Salesforce sont **structurellement prédisposés** à surévaluer un projet For Good authentiquement aligné avec cette culture. Facteur ×1,3 estimé sur le critère Potential Impact.

**MAIS** : ce biais s'inverse et devient **pénalisant** si le projet est perçu comme "charity washing". La déception d'un juge Salesforce qui s'attend à mieux est plus sévère que celle d'un juge neutre.

### 12.2 La fatigue cognitive des juges

Chaque juge évalue des centaines de projets en quelques semaines. Biais :
- Première impression (60 premières secondes vidéo) = 50 % du score inconscient
- Clarté du diagramme = 20 % du score inconscient
- Émotion vidéo = 20 % du score inconscient
- Le reste (description, code) = 10 % du score inconscient

Implication : investir massivement dans les 60 premières secondes et le diagramme.

### 12.3 Le biais Dreamforce 2026

Les juges Slack veulent des projets "présentables sur scène au keynote Dreamforce". Question implicite d'un PM Slack en regardant une démo : "Est-ce que Marc Benioff pourrait présenter ça au keynote ?". Cela signifie :
- Concept racontable en 1 phrase
- Image forte pour slide keynote
- Chiffre citable
- Pas de jargon technique incompréhensible pour non-devs

### 12.4 Le biais pro-tech des juges Devpost externes

Au moins 1 juge ne sera pas Slack/Salesforce. Souvent un MVP Salesforce, journaliste DevClass/The New Stack, ou fondateur de startup partenaire. Ce juge est ému par **l'astuce technique** (MCP malin, intégration inattendue). Tech dense = bonus sur ce juge.

### 12.5 Le biais Slack-native

Les juges Slack **connaissent les limites de Slack**. Si la démo montre des fonctionnalités qui n'existent pas dans Slack (ex : bot qui passe des appels téléphoniques), le juge le sait et pénalise. La démo doit rester plausible dans l'écosystème Slack réel : channels, DMs, App Home, Workflow Builder, huddles, slash commands, modals, Block Kit, canvas, lists, AI summaries.

### 12.6 Le biais du track For Good sous-participé

Historiquement, le track For Good attire 3-4x moins de monde que le track New Slack Agent. Les juges Slack qui évaluent For Good sont souvent plus "indulgents" sur la tech (parce qu'ils voient beaucoup de charity washing faible). MAIS les 5 % de projets For Good tech-forts ressortent massivement.

### 12.7 Le biais vidéo narrative

Les projets For Good qui gagnent ont presque tous une vidéo narrative (avant/pendant/après) plutôt qu'une vidéo démo fonctionnelle pure. L'émotion dans les 60 premières secondes est corrélée à +0,65 avec la victoire.

### 12.8 Le biais code open-source

Les juges Devpost externes valorisent un repo GitHub public avec README soigné. Bonus de +10 % sur le critère Tech si code visible, commenté, testable.

---

## 13. LE CODE DE VIGIE — RÈGLES INTERNES DU PROJET

### 13.1 Règles de design

- Slack-native pur (pas de dashboard web externe, tout dans Slack)
- Block Kit pour chaque message structuré
- Modals pour les saisies
- App Home avec dashboard temps réel
- Canvas partagé pour la cellule de crise
- Lists pour les check-in assignments
- Couleurs Slack officielles : #4A154B (aubergine), #36C5F0 (aloe), #2EB67D (vert)
- Ton éditorial : sobre, humain, jamais dramatique

### 13.2 Règles techniques

- Python 3.11 + Bolt SDK for Python
- anthropic-mcp SDK pour le serveur MCP
- MCP server : 3 resources + 3 tools, jamais plus
- Slack AI : 4 tâches distinctes (transcription, extraction, classification, rapports)
- Real-Time Search API : cache Redis ou SQLite, refresh toutes les 30 min en alerte
- Tests unitaires sur fonctions critiques (assign_checkin, classify_anomaly, escalate)
- Logs structurés (JSON) vers stdout pour Railway
- Variables d'environnement pour tous les secrets (jamais en dur)
- README GitHub en anglais, screenshots, exemples
- Repo : `vigie-agent` ou similaire, licence MIT

### 13.3 Règles de soumission

- Description texte : 1 200 mots anglais, structure Problem/Solution/How/Technologies/Impact/Sources
- Vidéo : 2:54 exact, 60s émotion + 90s tech + 24s impact, voix off française + sous-titres anglais
- Diagramme : SVG Mermaid ou Excalidraw, 1600×1200, 5 couches
- Sandbox : workspace "Reseau-Soligarde-Paris", 12 channels, 12 users simulés, 50 fiches bénéficiaires
- Accès : slackhack@salesforce.com + testing@devpost.com ajoutés comme membres
- Repo GitHub public avec README détaillé

### 13.4 Règles éthiques

- Aucune donnée réelle de bénéficiaire. Simulation only.
- Disclaimer dans la soumission : "No real beneficiary data was used in this demo."
- Si victoire : 100 % du cash reversé à ONG réelle (Petits Frères des Pauvres ou Croix-Rouge française)
- Code open-source MIT, public dès le 13 juillet
- Roadmap publique
- Mention alignement Salesforce 1-1-1 dans la soumission

### 13.5 Règles de priorité (en cas de conflit)

Ordre de priorité pour toute décision :
1. **Tech** (40 % de priorité — tie-break winner)
2. **Design** (30 %)
3. **Impact** (20 %)
4. **Idée** (10 %)

Si hésitation entre 2 tâches, choisir celle qui améliore le critère le plus haut dans cette liste.

### 13.6 Règles de scope

- **IN** : Slack agent + MCP server + RTS integration + Slack AI + sandbox + vidéo + diagramme + description + repo GitHub
- **OUT** : dashboard web externe, app mobile, marketplace submission, multi-tenant auth complexe, scale production, support multi-langue (sauf EN/FR), intégration avec des ONG réelles pendant les 12 jours

### 13.7 Règles de communication

- L'utilisateur (Momo) décide. L'assistant propose.
- Chaque décision majeure documentée dans `/home/z/my-project/worklog.md`
- Chaque fichier produit est référencé dans `/home/z/my-project/tonton/`
- POINT.md est IMMUTABLE. POINT.D.md est évolutif.
- Si divergence d'opinion, l'utilisateur tranche. L'assistant exécute.

---

## 14. LES SOURCES ET RÉFÉRENCES

### 14.1 Documents officiels

- Slack Agent Builder Challenge Official Rules (409 lignes) — `/home/z/my-project/upload/Pasted Content_1782947530966.txt`
- Slack Developer Program (https://api.slack.com/developer-program)
- Slack Developer Sandboxes doc
- Slack Platform Docs
- Slack Marketplace Core Guidelines
- Agent Builder starter templates (HR, IT, Sales, Support)
- Bolt SDK (JavaScript, Python, Java)
- Slack CLI (`slack create agent`)
- Block Kit documentation
- MCP official spec (https://modelcontextprotocol.io)
- anthropic-mcp SDK Python
- Slack Dev Huddles Ep05 (MCP & RTS API)
- Slack Dev Huddles Ep06 (Marketplace, 23 juin 2026 11h PT)

### 14.2 Sources Vigie (impact)

- InVS 2003 (14 802 décès excédentaires France été 2003)
- INED (confirmation chiffres 2003)
- Nature Medicine, Ballester et al. juillet 2023 (61 672 décès Europe été 2022)
- Petits Frères des Pauvres, "Solitude 2020" (530 000 seniors en mort sociale)
- NASEM 2020 (24 % des 65+ US isolés, $6,7 Md Medicare)
- Cour des comptes 2020 (Plan Canicule, 30-50 % non contactés)
- Décret n° 2006-1089 du 31 août 2006 (Plan Canicule français)
- CDC Heat & Health Toolkit
- WHO Age-Friendly Cities Framework
- WHO Heat-Health Action Plans (guide 2008, MAJ 2023)
- Météo-France API vigilance
- NWS Weather API
- OpenStreetMap Overpass API
- INSEE
- data.gouv.fr (schéma registre canicule)

### 14.3 Fichiers de référence Vigie

- `/home/z/my-project/POINT.md` — Vision + objectifs colossaux (IMMUTABLE)
- `/home/z/my-project/POINT.D.md` — Ce fichier (master reference)
- `/home/z/my-project/tonton/00-synthese-comparative-finale.md` — Décision high-level
- `/home/z/my-project/tonton/filiere-1-new-slack-agent.md` — Analyse filière 1
- `/home/z/my-project/tonton/filiere-2-agent-for-good.md` — Analyse filière 2 (Vigie)
- `/home/z/my-project/tonton/filiere-3-agent-for-organizations.md` — Analyse filière 3
- `/home/z/my-project/worklog.md` — Log multi-agents

---

## 15. RAPPEL DE LECTURE OBLIGATOIRE

### 15.1 Au début de chaque conversation sur Vigie

L'assistant DOIT relire :
1. `/home/z/my-project/POINT.md` (immutable, vision + objectifs colossaux)
2. `/home/z/my-project/POINT.D.md` (ce fichier, master reference)
3. `/home/z/my-project/worklog.md` (dernière section uniquement, pour contexte récent)

### 15.2 Avant chaque décision majeure

Vérifier dans POINT.D.md :
- Section 4 (criteres) — est-ce que la décision améliore un critère ?
- Section 6 (tie-break) — est-ce que Tech est priorisé ?
- Section 11 (pièges) — est-ce qu'on évite un piège ?
- Section 13 (code interne) — est-ce que la règle de scope est respectée ?

### 15.3 Avant chaque soumission/fichier produit

Vérifier dans POINT.D.md :
- Section 7 (exigences soumission) — tout est coché ?
- Section 10 (timeline) — on est dans les temps ?
- Section 13.4 (règles éthiques) — alignement maintenu ?

---

## 16. ENGAGEMENT MORAL

Ce fichier est évolutif mais toute modification doit servir Vigie, pas l'ego de l'assistant. Si une info est erronée, la corriger. Si une info manque, l'ajouter. Ne jamais retirer d'info sans justification explicite dans worklog.

L'engagement de l'assistant : relire POINT.md et POINT.D.md à chaque début de conversation Vigie, sans exception, sans raccourci.

---

FIN DE POINT.D.md
