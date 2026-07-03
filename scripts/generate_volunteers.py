"""
Vigie — Volunteer generator.

Generates 12 simulated volunteer profiles for the Reseau-Soligarde-Paris
sandbox workspace.

Output: mcp_server/data/volunteers.json
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.scripts.generate_volunteers")

# French first names, mixed genders
FIRST_NAMES = ["Marie", "Sophie", "Camille", "Léa", "Thomas", "Lucas", "Hugo", "Emma",
               "Sarah", "Yasmine", "Karim", "Mohamed", "Fatou", "Aïcha", "Pierre", "Anaïs",
               "Julien", "Nadia", "Rachid", "Elena"]
LAST_NAMES = ["Dupont", "Martin", "Bernard", "Petit", "Leroy", "Moreau", "Lefevre",
              "Roux", "Fournier", "Girard", "Bonnet", "Garcia", "Nguyen", "Benali",
              "Traoré", "Lambert", "Faure", "Rousseau", "Blanc", "Henry"]


def generate_volunteers(output_path: Path, count: int = 12) -> None:
    """Generate `count` simulated volunteers."""
    random.seed(42)

    volunteers: list[dict[str, Any]] = []
    chosen_names = random.sample(
        [(f, ln) for f in FIRST_NAMES for ln in LAST_NAMES],
        k=count,
    )

    for i, (first, last) in enumerate(chosen_names, start=1):
        sector = ((i - 1) % 12) + 1
        volunteer = {
            "id": f"V{i:02d}",
            # In the real sandbox, this will be the Slack user ID
            "slack_user_id": None,  # filled after sandbox setup
            "name": f"{first} {last}",
            "first_name": first,
            "last_name": last,
            "sector": sector,
            "role": "volunteer",
            "phone": f"+33 6 {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}",
            "email": f"{first.lower()}.{last.lower()}@soligarde-Paris.example.org",
            "availability": {
                "weekday_morning": True,
                "weekday_afternoon": random.random() > 0.4,
                "weekend": random.random() > 0.5,
                "max_checkins_per_day": random.choice([3, 5, 5, 8, 10]),
            },
            "languages": random.sample(
                ["fr", "en", "es", "ar", "zh", "pt"],
                k=random.choices([1, 2, 3], weights=[60, 30, 10])[0],
            ),
            "training_completed": ["plan_canicule_basics", "deontology"],
            "joined_date": f"2026-0{random.randint(1, 6)}-{random.randint(1, 28):02d}",
            "disclaimer": "SIMULATED — sandbox user",
        }
        volunteers.append(volunteer)

    # Add 2 medical coordinators (not assigned to a sector)
    for i in range(1, 3):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        volunteers.append({
            "id": f"MC{i:02d}",
            "slack_user_id": None,
            "name": f"Dr {first} {last}",
            "first_name": first,
            "last_name": last,
            "sector": None,
            "role": "medical_coordinator",
            "phone": f"+33 6 {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}",
            "email": f"{first.lower()}.{last.lower()}@soligarde-Paris.example.org",
            "specialty": random.choice(["Médecine générale", "Gériatrie", "Urgences"]),
            "availability": {
                "on_call": True,
                "max_escalations_per_day": 15,
            },
            "disclaimer": "SIMULATED — sandbox user",
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(volunteers, f, ensure_ascii=False, indent=2)

    log.info(
        "vigie.volunteers.generated",
        total=len(volunteers),
        volunteers=sum(1 for v in volunteers if v["role"] == "volunteer"),
        coordinators=sum(1 for v in volunteers if v["role"] == "medical_coordinator"),
        path=str(output_path),
    )


def main() -> None:
    """CLI entry point."""
    import sys

    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("mcp_server/data/volunteers.json")
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    generate_volunteers(output, count=count)


if __name__ == "__main__":
    main()
