# Devpost Project Details — Complete Content

## 1. PROJECT STORY

See: `devpost_project_story.md` (already generated)

Copy-paste the full content of that file into the "About the project" field.

---

## 2. BUILT WITH (tags — up to 25)

Add these tags one by one in the "Built with" field:

```
Slack
Slack Bolt
Slack Block Kit
Slack App Home
Slack Canvas
Python
Slack SDK
MCP
Model Context Protocol
Z-AI
Z-AI LLM
Z-AI VLM
glm-4.6v
Vision Language Model
FastAPI
APScheduler
Railway
AsyncIO
Pydantic
JSON
Audit Log
Heatwave
Elderly Care
Crisis Management
Public Health
```

(25 tags — exactly the max allowed)

---

## 3. TRY IT OUT LINKS

Add these links in the "Try it out" section:

### Link 1
- **Label:** GitHub — Source code
- **URL:** `https://github.com/[your-org]/vigie`
- *(Replace with your actual GitHub repo URL)*

### Link 2
- **Label:** Live bot on Railway
- **URL:** `https://vigie.up.railway.app/health`
- *(Replace with your actual Railway URL)*

### Link 3
- **Label:** Slack workspace invite
- **URL:** `https://join.slack.com/t/[your-workspace]/shared_invite/...`
- *(Replace with your actual Slack invite link — create one in Slack admin)*

### Link 4 (optional)
- **Label:** API health endpoint
- **URL:** `https://vigie.up.railway.app/vlm/health`
- *(Shows live VLM service stats)*

### Link 5 (optional)
- **Label:** Audit log (live)
- **URL:** `https://vigie.up.railway.app/audit`
- *(Shows the last 100 audit entries including vlm_analyze events)*

---

## 4. IMAGE GALLERY (up to 15 images, 3:2 ratio)

Upload these 5 images from `/home/z/my-project/download/`:

| # | File | Description (use as alt text) |
|---|------|-------------------------------|
| 1 | `vigie_thumbnail.png` | Vigie — 14,802 reasons to never forget. Split-screen banner: tragedy (left) vs solution (right). |
| 2 | `vigie_gallery_1_slack.png` | Slack workspace showing #cellule-crise with alert banner, L3 escalation card with SAMU button, KPI panel, and beneficiary list with Z-AI classification levels. |
| 3 | `vigie_gallery_2_architecture.png` | System architecture: 4-layer diagram (Frontend → Bot Core → AI Layer → Data) with Slack, Python, Z-AI LLM/VLM, MCP Server, and Railway. |
| 4 | `vigie_gallery_3_classification.png` | Z-AI 4-level severity triage: L0 (OK), L1 (weak signal), L2 (coordinator), L3 (SAMU) — each with real volunteer note examples and automated actions. |
| 5 | `vigie_gallery_4_vlm.png` | Z-AI VLM dashboard analysis: screenshot being analyzed with scan-line effect, extracted JSON fields, and ALERT health verdict. |

**Recommended upload order:** thumbnail first (it becomes the cover), then 2→3→4→5 in story order.

---

## 5. VIDEO DEMO

### Option A: Use the existing video script
See: `/home/z/my-project/docs/video-script.md`

### Option B: Quick demo outline (2-3 minutes)

**0:00–0:15 — Hook**
- Black screen → "14,802" appears in large serif font
- Voiceover: "In August 2003, 14,802 people died alone during a heatwave in France."
- Fade to: "23 years later, climate change has made heatwaves more deadly. But the systems meant to protect the vulnerable are still reactive."

**0:15–0:40 — The problem**
- Show: stock footage of elderly person alone in apartment
- Voiceover: "They had no one to call. No one checked on them. They died in silence."
- Cut to: "Vigie exists to break that silence."

**0:40–1:30 — How it works**
- Screen recording: Slack workspace
- Type `/vigie demo` in Slack
- Show: alert banner appears in #cellule-crise
- Show: volunteer DMs with beneficiary lists
- Show: volunteer types check-in note → Z-AI classifies L1
- Show: `/vigie-escalate B003 3 "On the ground, unconscious"` → L3 card with SAMU button
- Voiceover explains each step

**1:30–2:10 — The VLM layer**
- Screen recording: `/vigie inspect /tmp/screenshot.png`
- Show: VLM analysis returns with health verdict ALERT
- Show: audit log entry with `vlm_analyze` action
- Show: `/vlm/health` endpoint returning cache stats

**2:10–2:30 — The numbers**
- Animated text: "94% coverage · 7min latency · 152 tests · 14,802 reasons to never forget"
- Voiceover: "Vigie — so the heatwave no longer kills in silence."

**2:30 — Logo + tagline**
- Vigie logo
- "vigie-bot.up.railway.app"
- "Built with Slack, Z-AI, and MCP"

### Recording tips
- Use OBS Studio or Loom
- Record Slack in dark mode for consistency with the gallery images
- Keep it under 3 minutes — judges have many projects to review
- Upload to YouTube as unlisted, paste the URL in Devpost

---

## 6. CHECKLIST

- [ ] Project name: `Vigie — 14,802 reasons to never forget`
- [ ] Elevator pitch: (from previous message)
- [ ] Thumbnail: `vigie_thumbnail.png` uploaded
- [ ] Project story: copy-paste from `devpost_project_story.md`
- [ ] Built with: add all 25 tags
- [ ] Try it out: add 3-5 links
- [ ] Image gallery: upload 5 images (thumbnail + 4 gallery)
- [ ] Video demo: record and paste YouTube URL
- [ ] Save & continue through all steps

---

## 7. FILES TO DOWNLOAD

All in `/home/z/my-project/download/`:

| File | Size | Purpose |
|------|------|---------|
| `devpost_project_story.md` | 8 KB | Project story (Markdown) |
| `vigie_thumbnail.png` | 1.2 MB | Main thumbnail |
| `vigie_gallery_1_slack.png` | 144 KB | Slack workspace screenshot |
| `vigie_gallery_2_architecture.png` | 771 KB | Architecture diagram |
| `vigie_gallery_3_classification.png` | 701 KB | L0-L3 classification |
| `vigie_gallery_4_vlm.png` | 515 KB | VLM analysis |

Download all of these and upload to Devpost.
