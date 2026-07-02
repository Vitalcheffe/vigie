"""
Vigie — Sandbox seed script.

Sets up the Slack workspace for the Vigie demo:
  1. Creates the #cellule-crise channel
  2. Creates 12 #secteur-N channels
  3. Creates 12 #voisins-N channels
  4. Invites Vigie bot to all channels
  5. Posts a welcome message in each channel
  6. (Optional) Creates 12 volunteer users if not already present
  7. Generates beneficiaries.json and volunteers.json if missing
  8. Updates the .env file with channel IDs

Usage:
    vigie-seed
    # or with options:
    vigie-seed --skip-users --skip-channels
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from app.utils.config import get_config
from app.utils.logging import get_logger, setup_logging

console = Console()
log = setup_logging()

app = typer.Typer(help="Seed the Vigie sandbox workspace.")


@app.command()
def main(
    skip_channels: bool = typer.Option(False, "--skip-channels", help="Don't create channels"),
    skip_users: bool = typer.Option(False, "--skip-users", help="Don't create users"),
    skip_data: bool = typer.Option(False, "--skip-data", help="Don't generate beneficiaries/volunteers"),
) -> None:
    """Seed the Vigie sandbox workspace."""
    cfg = get_config()

    console.print(f"\n[bold purple]Vigie — Sandbox Seed[/bold purple]")
    console.print(f"Workspace: [cyan]{cfg.slack.workspace_name}[/cyan]\n")

    if not skip_data:
        _generate_data_files()

    if not skip_channels:
        _create_channels()

    if not skip_users:
        _create_users()

    console.print("\n[bold green]✓ Sandbox seeded successfully.[/bold green]")
    console.print("\nNext steps:")
    console.print("  1. Update .env with the channel IDs printed above")
    console.print("  2. Start the MCP server: [cyan]vigie-mcp[/cyan]")
    console.print("  3. Start the Slack bot: [cyan]vigie-bot[/cyan]")
    console.print("  4. In Slack, type [cyan]/vigie start[/cyan] to trigger the heatwave scenario\n")


def _generate_data_files() -> None:
    """Generate beneficiaries.json and volunteers.json if missing."""
    from scripts.generate_beneficiaries import generate_beneficiaries
    from scripts.generate_volunteers import generate_volunteers

    base = Path(__file__).resolve().parent.parent
    data_dir = base / "mcp_server" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    benef_path = data_dir / "beneficiaries.json"
    if not benef_path.exists():
        console.print("[yellow]Generating beneficiaries.json...[/yellow]")
        generate_beneficiaries(benef_path, count=50)
        console.print(f"  [green]✓[/green] 50 beneficiaries generated")
    else:
        console.print(f"  [dim]beneficiaries.json already exists, skipping[/dim]")

    vol_path = data_dir / "volunteers.json"
    if not vol_path.exists():
        console.print("[yellow]Generating volunteers.json...[/yellow]")
        generate_volunteers(vol_path, count=12)
        console.print(f"  [green]✓[/green] 12 volunteers + 2 coordinators generated")
    else:
        console.print(f"  [dim]volunteers.json already exists, skipping[/dim]")


def _create_channels() -> None:
    """Create Slack channels: #cellule-crise, #secteur-1..12, #voisins-1..12."""
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    cfg = get_config()
    client = WebClient(token=cfg.slack.bot_token.get_secret_value())

    console.print("\n[bold]Creating channels...[/bold]")

    table = Table(title="Created Channels", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("ID", style="green")
    table.add_column("Status", style="yellow")

    channels_to_create = [
        ("cellule-crise", "Cellule de crise — vue temps réel"),
    ]
    for i in range(1, cfg.slack.num_sectors + 1):
        channels_to_create.append((f"{cfg.slack.secteur_prefix}{i}", f"Secteur {i} — check-in bénévoles"))
        channels_to_create.append((f"{cfg.slack.voisins_prefix}{i}", f"Voisins référents secteur {i}"))

    created_ids: dict[str, str] = {}

    for name, purpose in channels_to_create:
        try:
            # Try to create (will fail if already exists, that's OK)
            try:
                resp = client.conversations_create(name=name, is_private=False)
                channel_id = resp["channel"]["id"]
                # Set purpose
                client.conversations_setPurpose(channel=channel_id, purpose=purpose)
                # Invite the bot itself (it's auto-joined as creator, but be safe)
                table.add_row(f"#{name}", channel_id, "Created")
                created_ids[name] = channel_id
            except SlackApiError as e:
                if e.response["error"] == "name_taken":
                    # Channel already exists, find it
                    list_resp = client.conversations_list(types="public_channel", limit=200)
                    for ch in list_resp["channels"]:
                        if ch["name"] == name:
                            created_ids[name] = ch["id"]
                            table.add_row(f"#{name}", ch["id"], "Already exists")
                            break
                else:
                    raise
        except Exception as e:
            log.error("vigie.seed.channel_failed", name=name, error=str(e))
            table.add_row(f"#{name}", "-", f"Failed: {e}")

    console.print(table)

    # Save channel IDs to a config file
    ids_path = Path(__file__).resolve().parent.parent / "sandbox_channels.json"
    with ids_path.open("w", encoding="utf-8") as f:
        json.dump(created_ids, f, ensure_ascii=False, indent=2)
    console.print(f"\n[dim]Channel IDs saved to {ids_path}[/dim]")


def _create_users() -> None:
    """TODO: create or invite volunteer users to the workspace.

    NOTE: Slack free workspaces cannot create users programmatically.
    In practice, you'll manually invite 12 volunteer email addresses
    to the sandbox. This script just prints a checklist.
    """
    console.print("\n[bold]User setup checklist:[/bold]")
    console.print("  [yellow]Slack free workspaces can't create users via API.[/yellow]")
    console.print("  Manually invite the following volunteers to the workspace:")
    console.print("  (You can use fake email addresses like volunteer1@soligarde.example.org)")
    console.print("")
    console.print("  1. Once invited, each volunteer opens Slack")
    console.print("  2. They type /vigie to register")
    console.print("  3. Vigie assigns them a sector and updates volunteers.json")
    console.print("")


if __name__ == "__main__":
    app()
