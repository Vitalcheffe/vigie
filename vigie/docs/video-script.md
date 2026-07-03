# Vigie — Video Script (3 minutes)

Shot-by-shot script for the hackathon demo video. Total: 180 seconds.
Format: 16:9, 1920x1080, ambient piano + light pulsation in segment 2.
Voiceover: calm female voice (French), English subtitles required.

## Segment 1 — The problem (0:00 — 1:00)

Emotional hook. No Vigie branding yet. Goal: make the judge think
"this could have been my grandmother."

| Time | Visual | Voiceover / On-screen text |
|------|--------|----------------------------|
| 0:00 - 0:03 | Black screen | "Août 2003. France." (white text, centered) |
| 0:03 - 0:07 | Black screen | "14 802 décès en 3 semaines." — Source: "InVS 2003" (small, bottom) |
| 0:07 - 0:11 | Black screen | "80 % avaient plus de 75 ans." — Source: "INED" |
| 0:11 - 0:15 | Stock photo (Pexels, "elderly alone") — elderly woman by window, soft warm light, ventilator in background | (silence) |
| 0:15 - 0:19 | Black screen | "Été 2022. Europe. 61 672 décès." — Source: "Nature Medicine 2023" |
| 0:19 - 0:24 | Urban concrete in heat, harsh light, no people | (silence) |
| 0:24 - 0:30 | Slow zoom on a fixed-line phone ringing in an empty room | VO: "Chaque été, en France, des milliers de personnes âgées vivent seules la canicule. Le Plan Canicule les inscrit sur un registre." |
| 0:30 - 0:36 | VO continues | "Mais en alerte orange, 30 à 50 % ne sont pas contactées dans les 24 heures." |
| 0:36 - 0:42 | Portrait of an elderly woman (actress or Pexels), apartment, weak ventilator | VO: "Hélène, 82 ans, secteur 11, Paris. Inscrite au registre. Aucun proche." |
| 0:42 - 0:48 | Close-up on a thermometer in the apartment: 39°C | (silence) |
| 0:48 - 0:54 | Phone rings in an empty room, no one answers | VO: "À 11 heures, elle ne répond pas à son téléphone." |
| 0:54 - 1:00 | Black screen | "Sans intervention, le délai avant découverte dépasse souvent 24 heures." |

## Segment 2 — Vigie in action (1:00 — 2:30)

Dense technical demo. Goal: prove Vigie is real engineering, not
"charity washing." Three technologies must be visible on screen.

| Time | Visual | Voiceover / On-screen text |
|------|--------|----------------------------|
| 1:00 - 1:04 | Black screen, then Vigie logo (aubergine + aloe) | "Voici Vigie." |
| 1:04 - 1:08 | Slack workspace "Reseau-Soligarde-Paris", #cellule-crise channel. Vigie auto-message: "Vigilance orange, 187 bénéficiaires à contacter aujourd'hui" | (silence) |
| 1:08 - 1:14 | Same screen, weather alert card overlaid: "Météo-France API" | VO: "À 7 heures, Vigie détecte l'alerte Météo-France, croise le registre Plan Canicule, et affecte automatiquement les check-in aux 12 bénévoles." |
| 1:14 - 1:20 | DM to volunteer "Marie": 5 beneficiaries, full context, "Démarrer les appels" button | (silence) |
| 1:20 - 1:28 | Marie clicks. Animated call. She posts a voice note: "Mme Dupont fatiguée, demande médicaments." | Annotation overlay: "Transcription par Slack AI" |
| 1:28 - 1:36 | Overlay: Slack AI output as JSON: `{state, signals, action}`. Then Vigie posts in #secteur-11 with the closest pharmacy (OpenStreetMap card), buttons "Confirmer / Escalader / Clôturer". | VO: "Trois technologies réelles. Slack AI pour comprendre. MCP server pour croiser registre, météo, cartes. Real-Time Search pour citer la directive sanitaire en cours." |
| 1:36 - 1:42 | #secteur-3, Mme Martin has not answered 3 calls. Vigie identifies the neighbor referent, DMs #voisins-3 | (silence) |
| 1:42 - 1:56 | Critical escalation: #cellule-crise post with red banner, "ESCALADE NIVEAU 3", full context summary, "Appeler le 15" button. Vigie AI summary visible. | VO: "Temps écoulé : 2 h 25. Sans Vigie : 8 à 24 heures." |
| 1:56 - 2:08 | App Home dashboard: 5 KPIs live (95% coverage, 2 min 10 avg, 4 min 30 escalation latency, 0 unreachable > 72h, 7 weak signals) | VO: "À 18 heures, Vigie génère le rapport quotidien." |
| 2:08 - 2:14 | Daily report posted in #cellule-crise: AI narrative + ARS Île-de-France citation (Real-Time Search) | (silence) |
| 2:14 - 2:30 | Three technology logos appear one by one on screen: "Slack AI", "MCP server", "Real-Time Search API" — then "Vigie" | VO: "Stack : Slack AI + MCP server + Real-Time Search API." |

## Segment 3 — Impact and call-to-action (2:30 — 3:00)

| Time | Visual | Voiceover / On-screen text |
|------|--------|----------------------------|
| 2:30 - 2:36 | Return to Hélène. Firefighters at her door. Warm light. | VO: "Hélène est hospitalisée à temps." |
| 2:36 - 2:42 | Hélène waves from a hospital window | VO: "Elle rentre chez elle 4 jours plus tard." |
| 2:42 - 2:50 | Black screen, large text | "Avec Vigie : 95 % des personnes isolées contactées en moins de 2 heures. Contre 38 % sans." |
| 2:50 - 2:56 | Black screen, smaller text | "Stack : Slack AI + MCP server + Real-Time Search API." |
| 2:56 - 3:00 | Vigie logo, tagline | "Pour que la canicule ne tue plus en silence." |

## End card

Final 1-2 seconds:
- Vigie logo
- "Slack Agent Builder Challenge 2026 — Agent for Good track"
- Small print: "Sources: InVS, INED, Nature Medicine 2023, NASEM 2020, Cour des comptes 2020"

## Montage notes

- **Music**: ambient piano, low-register. Pulse only in segment 2 (technical).
- **Color grade**:
  - Segment 1: warm tones (orange, ochre, harsh yellows) for the heat
  - Segment 2: cool tones (alo, white, structured) for the technique
  - Segment 3: golden hour tones for hope
- **Pace**: deliberate, not frantic. 4-second minimum per shot.
- **Captions**: English subtitles required (judges may be non-francophone).
  Use Inter or Helvetica, 36px, high contrast.
- **Voice**: one female voice, calm, never dramatic. The gravity is in the numbers.
- **No copyrighted music**. Use YouTube Audio Library or Artlist (with license).
- **No third-party trademarks** without permission (Slack logo OK, Météo-France logo OK
  with attribution, ARS logo: avoid).

## Tools

- **Editing**: DaVinci Resolve (free) or Final Cut Pro
- **Stock footage**: Pexels (free), or film your own with an actress
- **Screen recording**: OBS Studio (free) for the Slack demo
- **Subtitles**: Auto-translate with DeepL, then manual review

## Filming tips

- For Hélène's apartment: film in a real apartment if possible. Avoid studios.
- The phone-ringing shot is critical — use a real landline phone, not a mobile.
- For the firefighter scene: a friend in a yellow jacket with a flashlight works.
  Don't try to impersonate real SAMU uniforms.
- The "thermometer at 39°C" shot: use an indoor thermometer, place near a heat
  source, film close-up with shallow depth of field.
