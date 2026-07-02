# Vigie — Setup Guide

This guide walks through setting up the Vigie sandbox from scratch. Total time: ~2 hours.

## Prerequisites

- Python 3.11+
- A free Slack workspace (create one at https://slack.com/get-started)
- A Slack app (created from our manifest)
- Optional: OpenAI API key (for Slack AI fallback)

## Step 1 — Clone and install

```bash
git clone https://github.com/Vitalcheffe/vigie.git
cd vigie
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

Verify the install:

```bash
pytest                # 32 tests should pass
ruff check .          # should be clean
```

## Step 2 — Create the Slack workspace

1. Go to https://slack.com/get-started → "Create a new workspace"
2. Workspace name: `Reseau-Soligarde-Paris`
3. Add your personal email as the first member
4. (Optional) Add 2-3 fake email addresses as additional "volunteers"

## Step 3 — Create the Slack app from manifest

1. Go to https://api.slack.com/apps → "Create New App" → "From an app manifest"
2. Pick your `Reseau-Soligarde-Paris` workspace
3. Paste the contents of `manifest/app-manifest.yaml` (or upload the file if Slack allows)
4. Click "Create"

The app is now created with all 20+ OAuth scopes, 5 slash commands, 5 event subscriptions, and 2 shortcuts pre-configured.

## Step 4 — Get your credentials

In the Slack app config page (left sidebar):

1. **Basic Information** → copy:
   - Signing Secret → `SLACK_SIGNING_SECRET`
   - App-Level Token (generate one with `connections:write` scope) → `SLACK_APP_TOKEN`

2. **OAuth & Permissions** → "Install to Workspace" → copy:
   - Bot User OAuth Token (starts with `xoxb-`) → `SLACK_BOT_TOKEN`

## Step 5 — Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```bash
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-secret
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_WORKSPACE_NAME=Reseau-Soligarde-Paris

# Optional — for Slack AI fallback (transcription, classification)
OPENAI_API_KEY=sk-your-openai-key

# MCP server auth (any random string)
MCP_SERVER_TOKEN=generate-a-random-string-here
```

## Step 6 — Seed the sandbox

This creates the channels (`#cellule-crise`, `#secteur-1..12`, `#voisins-1..12`) and generates the simulated beneficiary + volunteer data.

```bash
vigie-seed
```

The script prints the channel IDs as it creates them. Copy the `cellule-crise` ID back into `.env`:

```bash
SLACK_CELLULE_CRISE_CHANNEL_ID=C12345678
```

## Step 7 — Invite Vigie to channels

The bot is auto-invited to channels it creates. To verify:

1. Open `#cellule-crise` in Slack
2. Type `/vigie help` — Vigie should respond

If Vigie is not in a channel, use `/invite @Vigie` in that channel.

## Step 8 — Add test judges' access

The hackathon requires giving sandbox access to:

- `slackhack@salesforce.com`
- `testing@devpost.com`

In Slack → workspace admin panel → "Manage members" → invite both emails as members.

## Step 9 — Start the bot

In two separate terminals:

```bash
# Terminal 1 — MCP server
make run-mcp

# Terminal 2 — Slack bot (Socket Mode)
make run-bot
```

You should see in the bot logs:

```
vigie.starting workspace=Reseau-Soligarde-Paris socket_mode=True
vigie.socket_mode.starting
```

## Step 10 — Run the canicule simulation

In Slack, type:

```
/vigie start
```

Vigie will:
1. Detect the (simulated) Météo-France vigilance orange
2. Post in `#cellule-crise`
3. Assign 5 beneficiaries to each volunteer via DM
4. Wait for your check-in notes (post a DM to Vigie with any text)
5. Classify the note and post in the sector channel

To replay the full 12-hour scenario in 30 seconds:

```bash
vigie-simulate --accelerated
```

## Step 11 — Production deploy (optional)

For the hackathon demo, the bot can stay in Socket Mode. For a production deploy on Railway:

1. Push the repo to GitHub
2. Create a new Railway project from the repo
3. Add the env vars from `.env` as Railway variables
4. Set the start command to `python -m app.main` for the bot
5. Create a second service for the MCP server with `python -m mcp_server.server`
6. Add a Redis service (Railway will auto-provision)
7. Update the Slack app config with the Railway HTTPS URL for Event Subscriptions and Interactivity

## Troubleshooting

**Bot doesn't respond to /vigie**
- Check the bot is in the channel (`/invite @Vigie`)
- Check Socket Mode is enabled in the Slack app config
- Verify `SLACK_APP_TOKEN` is set and starts with `xapp-`

**MCP server unreachable**
- Verify the MCP server is running (`curl http://localhost:8000/health`)
- Verify `MCP_SERVER_TOKEN` matches in both bot and server

**Slack AI not transcribing voice notes**
- Slack AI requires a paid workspace. Use the OpenAI fallback (`OPENAI_API_KEY` in `.env`)
- Voice notes are only transcribed if posted as file shares in DM with Vigie

**Tests failing**
- Make sure you installed with `pip install -e ".[dev]"`
- Run `pytest --no-cov` to see the full output

## Next steps

- Read `docs/architecture.md` for the technical deep-dive
- Read `docs/video-script.md` for the 3-minute demo script
- Check `POINT.md` and `POINT.D.md` (project anchor files) for the vision and criteria
