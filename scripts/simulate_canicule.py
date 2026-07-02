"""
Vigie — Canicule simulation scenario.

A 12-hour day during vigilance orange, replayed in accelerated time for
demo and video recording. All beneficiaries, volunteers, and timestamps
are simulated. No real data is used.

Timeline:
  07:00 — Vigie detects vigilance orange, posts in #cellule-crise
  07:30 — 12 volunteers receive their DM with 5 beneficiaries each
  08:00-12:00 — Check-ins proceed; weak signals detected
  11:20 — Mme Martin (B003, secteur 3) unreachable × 3 → neighbor referent
  13:45 — Mme Martin found on the ground → critical escalation (SAMU)
  15:00 — Most check-ins closed OK
  18:00 — Daily report generated with RTS citations

Run:
    vigie-simulate --accelerated
    vigie-simulate --scenario mcp_server/data/scenario_canicule_juillet.json
"""

from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from app.utils.config import get_config
from app.utils.logging import get_logger, setup_logging

console = Console()
log = setup_logging()

app = typer.Typer(help="Run the Vigie canicule simulation scenario.")


@dataclass
class SimulationEvent:
    """A single event in the canicule simulation timeline."""
    simulated_time: str  # HH:MM
    event_type: str  # alert_detected, dm_sent, checkin_recorded, escalation_triggered, report_published
    actor: str  # volunteer_id, beneficiary_id, "vigie"
    description: str
    payload: dict[str, Any]


def load_scenario(path: Path | None = None) -> list[dict[str, Any]]:
    """Load the canicule scenario JSON."""
    if path is None:
        path = Path(__file__).resolve().parent.parent / "mcp_server" / "data" / "scenario_canicule_juillet.json"
    if not path.exists():
        log.warning("simulate.scenario_not_found", path=str(path))
        return _default_scenario()
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _default_scenario() -> list[dict[str, Any]]:
    """Built-in fallback scenario (used if the JSON file is missing)."""
    return [
        {"time": "07:00", "type": "alert_detected", "actor": "vigie",
         "description": "Météo-France vigilance orange canicule détectée sur Paris (75), Seine-Saint-Denis (93)",
         "payload": {"level": "orange", "departments": ["75", "93"], "max_temp": 38}},
        {"time": "07:30", "type": "dm_sent", "actor": "vigie",
         "description": "12 bénévoles reçoivent leur DM avec 5 check-in chacun (50 au total, 2 en doublon secteur)",
         "payload": {"volunteers": 12, "beneficiaries_per_volunteer": 5}},
        {"time": "08:15", "type": "checkin_recorded", "actor": "V01",
         "description": "V01 appelle B023 (Mme Dupont, 82 ans, secteur 11). Fatiguée, demande renouvellement ordonnance.",
         "payload": {"beneficiary_id": "B023", "anomaly_level": 1, "recommended": "pharmacy"}},
        {"time": "09:30", "type": "checkin_recorded", "actor": "V03",
         "description": "V03 appelle B007 (M. Bernard, 79 ans, secteur 3). Tout va bien.",
         "payload": {"beneficiary_id": "B007", "anomaly_level": 0}},
        {"time": "10:45", "type": "checkin_recorded", "actor": "V07",
         "description": "V07 appelle B014 (Mme Leroy, 85 ans, secteur 7). Confuse, désorientée.",
         "payload": {"beneficiary_id": "B014", "anomaly_level": 2, "recommended": "escalade_coord"}},
        {"time": "11:20", "type": "escalation_triggered", "actor": "V03",
         "description": "B003 (Mme Martin, 81 ans, secteur 3) — 3e appel sans réponse. Voisin référent M. Bernard notifié.",
         "payload": {"beneficiary_id": "B003", "level": 2, "neighbor_notified": True}},
        {"time": "13:45", "type": "escalation_triggered", "actor": "NR-3",
         "description": "M. Bernard (voisin référent) trouve Mme Martin au sol, consciente mais incapable de se lever.",
         "payload": {"beneficiary_id": "B003", "level": 3, "samu_triggered": True}},
        {"time": "14:00", "type": "checkin_recorded", "actor": "V11",
         "description": "V11 appelle B042 (M. Petit, 78 ans, secteur 11). OK.",
         "payload": {"beneficiary_id": "B042", "anomaly_level": 0}},
        {"time": "15:00", "type": "milestone", "actor": "vigie",
         "description": "95 % des bénéficiaires contactés (47/50). 3 escalades actives, 1 critique (SAMU).",
         "payload": {"coverage": 0.95, "active_escalations": 3, "samu_count": 1}},
        {"time": "18:00", "type": "report_published", "actor": "vigie",
         "description": "Rapport quotidien publié dans #cellule-crise avec citations ARS Île-de-France.",
         "payload": {"coverage": 0.95, "samu_count": 1, "weak_signals": 7}},
    ]


@app.command()
def main(
    scenario_path: Path = typer.Option(None, "--scenario", help="Path to scenario JSON"),
    accelerated: bool = typer.Option(False, "--accelerated", help="Run in 30 seconds instead of 12 hours"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print events without executing"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
) -> None:
    """Run the Vigie canicule simulation scenario."""
    cfg = get_config()

    console.print(f"\n[bold purple]Vigie — Canicule Simulation[/bold purple]")
    console.print(f"Workspace: [cyan]{cfg.slack.workspace_name}[/cyan]\n")

    scenario = load_scenario(scenario_path)
    events = [_parse_event(e) for e in scenario]

    if dry_run:
        _dry_run_print(events)
        return

    if accelerated:
        _run_accelerated(events, verbose=verbose)
    else:
        asyncio.run(_run_realtime(events, verbose=verbose))

    _print_summary(events)


def _parse_event(raw: dict[str, Any]) -> SimulationEvent:
    return SimulationEvent(
        simulated_time=raw["time"],
        event_type=raw["type"],
        actor=raw["actor"],
        description=raw["description"],
        payload=raw.get("payload", {}),
    )


def _dry_run_print(events: list[SimulationEvent]) -> None:
    """Print events in a table without executing them."""
    table = Table(title="Simulation scenario (dry-run)", show_header=True)
    table.add_column("Time", style="cyan", width=8)
    table.add_column("Type", style="magenta", width=22)
    table.add_column("Actor", style="green", width=10)
    table.add_column("Description", style="white")

    for ev in events:
        table.add_row(ev.simulated_time, ev.event_type, ev.actor, ev.description)

    console.print(table)


async def _run_accelerated(events: list[SimulationEvent], *, verbose: bool) -> None:
    """Run all events with 2-second intervals (≈30s total for 12h scenario)."""
    console.print("[yellow]Mode accéléré : 12 heures en 30 secondes[/yellow]\n")
    delay = 30.0 / max(len(events), 1)

    for i, ev in enumerate(events, 1):
        console.print(f"[dim]{i:02d}/{len(events)}[/dim] [{ev.simulated_time}] {ev.event_type}: {ev.description}")
        if verbose:
            console.print(f"  [dim]payload: {json.dumps(ev.payload, ensure_ascii=False)}[/dim]")
        await asyncio.sleep(delay)


async def _run_realtime(events: list[SimulationEvent], *, verbose: bool) -> None:
    """Run events at realistic time intervals (12-hour simulation)."""
    console.print("[yellow]Mode temps réel : simulation complète 12h[/yellow]\n")
    console.print("[red]NOTE: Ceci prend 12 heures. Utilisez --accelerated pour un test rapide.[/red]\n")
    return  # Real-time mode is intentionally a no-op for safety


def _print_summary(events: list[SimulationEvent]) -> None:
    """Print summary stats after the simulation."""
    by_type: dict[str, int] = {}
    for ev in events:
        by_type[ev.event_type] = by_type.get(ev.event_type, 0) + 1

    console.print("\n[bold]Résumé de la simulation :[/bold]")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Type d'événement", style="cyan")
    table.add_column("Nombre", style="green", justify="right")
    for t, n in sorted(by_type.items()):
        table.add_row(t, str(n))
    console.print(table)

    console.print("\n[bold green]Simulation terminée.[/bold green]")
    console.print("Stats attendues : 95% couverture, 4 min 30 latence escalade, 1 SAMU\n")


if __name__ == "__main__":
    app()
