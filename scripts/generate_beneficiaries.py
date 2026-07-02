"""
Vigie — Simulated beneficiary generator.

Generates 50 fictitious beneficiary profiles conforming to the
Plan Canicule schema (Décret n° 2006-1089). All data is simulated;
no real beneficiary records are used.

Output: mcp_server/data/beneficiaries.json
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.scripts.generate_beneficiaries")

# Realistic French first names for seniors (born ~1940-1960)
FIRST_NAMES_F = ["Hélène", "Marie", "Jeanne", "Marguerite", "Suzanne", "Yvonne", "Georgette", "Paulette", "Andrée", "Lucienne", "Solenne", "Monique", "Renée", "Thérèse"]
FIRST_NAMES_M = ["Henri", "Pierre", "André", "Robert", "Maurice", "Gaston", "Émile", "Fernand", "Lucien", "Victor", "Georges", "Marcel", "Édouard"]

LAST_INITIALS = list("ABCDEFGHIJKLMNOPRSTVW")

# Paris arrondissements (sectors 1-12 → arrondissements 1-20 mapped)
SECTOR_TO_ARRONDISSEMENT = {
    1: ("75001", 48.8606, 2.3376),
    2: ("75002", 48.8655, 2.3431),
    3: ("75003", 48.8606, 2.3625),
    4: ("75004", 48.8560, 2.3560),
    5: ("75005", 48.8440, 2.3500),
    6: ("75006", 48.8530, 2.3300),
    7: ("75007", 48.8560, 2.3100),
    8: ("75008", 48.8730, 2.3080),
    9: ("75009", 48.8780, 2.3380),
    10: ("75010", 48.8730, 2.3600),
    11: ("75011", 48.8590, 2.3790),
    12: ("75012", 48.8400, 2.3890),
}

STREETS = [
    "Rue des Lilas", "Avenue de la République", "Boulevard Voltaire",
    "Rue Oberkampf", "Rue Saint-Maur", "Rue de Belleville", "Avenue Parmentier",
    "Rue du Faubourg du Temple", "Rue Saint-Ambroise", "Rue de la Roquette",
    "Rue de Charonne", "Boulevard Beaumarchais", "Rue du Chemin Vert",
    "Rue Amelot", "Rue de Turenne", "Rue de Bretagne", "Rue du Temple",
    "Rue Vieille du Temple", "Rue des Rosiers", "Rue des Francs-Bourgeois",
]

MEDICAL_CONDITIONS = [
    "hypertension", "diabète type 2", "arthrose", "démence légère",
    "insuffisance cardiaque", "BPCO", "hypothyroïdie", "dépression",
    "AVC séquellaire", "Parkinson", "Alzheimer début",
]

MEDICATIONS = [
    "antihypertenseur", "metformine", "antalgique", "anticoagulant",
    "diurétique", "insuline", "antidépresseur", "anxiolytique",
    "antiparkinsonien", "antiarythmique",
]


def generate_beneficiaries(output_path: Path, count: int = 50, seed: int = 42) -> None:
    """Generate `count` simulated beneficiaries and write to output_path."""
    random.seed(seed)

    beneficiaries: list[dict[str, Any]] = []
    for i in range(1, count + 1):
        sector = ((i - 1) % 12) + 1
        postal_code, base_lat, base_lon = SECTOR_TO_ARRONDISSEMENT[sector]

        is_female = random.random() > 0.35
        first_name = random.choice(FIRST_NAMES_F if is_female else FIRST_NAMES_M)
        last_initial = random.choice(LAST_INITIALS)

        age = random.randint(72, 94)
        conditions = random.sample(
            MEDICAL_CONDITIONS,
            k=random.choices([0, 1, 2, 3], weights=[5, 35, 40, 20])[0],
        )
        medications = random.sample(
            MEDICATIONS,
            k=random.choices([0, 1, 2, 3, 4], weights=[5, 25, 35, 25, 10])[0],
        )

        # Add small offset to lat/lon for address variation
        lat = base_lat + random.uniform(-0.005, 0.005)
        lon = base_lon + random.uniform(-0.005, 0.005)

        vulnerability_score = _compute_vulnerability_score(age, conditions, medications)

        beneficiary = {
            "id": f"B{i:03d}",
            "first_name": first_name,
            "last_initial": last_initial,
            "age": age,
            "gender": "F" if is_female else "M",
            "sector": sector,
            "address": {
                "street": f"{random.randint(1, 180)} {random.choice(STREETS)}",
                "postal_code": postal_code,
                "city": "Paris",
                "lat": round(lat, 6),
                "lon": round(lon, 6),
            },
            "phone": f"+33 6 {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}",
            "emergency_contacts": _generate_emergency_contacts(sector),
            "medical_conditions": conditions,
            "medications": medications,
            "vulnerability_score": vulnerability_score,
            "isolation_level": _isolation_level(vulnerability_score),
            "language": "fr",
            "notes": None,
            "last_checkin_at": None,
            "status": "registered",
            "registration_date": f"2026-0{random.randint(1, 6)}-{random.randint(1, 28):02d}",
            "disclaimer": "SIMULATED — no real beneficiary data",
        }
        beneficiaries.append(beneficiary)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(beneficiaries, f, ensure_ascii=False, indent=2)

    log.info(
        "vigie.beneficiaries.generated",
        count=len(beneficiaries),
        path=str(output_path),
        avg_vulnerability=sum(b["vulnerability_score"] for b in beneficiaries) / len(beneficiaries),
    )


def _compute_vulnerability_score(age: int, conditions: list[str], medications: list[str]) -> int:
    """Compute a 0-100 vulnerability score based on age, conditions, medications."""
    score = 0
    if age >= 85:
        score += 35
    elif age >= 80:
        score += 25
    elif age >= 75:
        score += 15
    else:
        score += 5

    # Critical conditions
    critical_conditions = {"démence légère", "Alzheimer début", "insuffisance cardiaque", "AVC séquellaire", "Parkinson"}
    score += sum(15 if c in critical_conditions else 8 for c in conditions)

    # Polypharmacy
    if len(medications) >= 4:
        score += 15
    elif len(medications) >= 2:
        score += 8
    elif medications:
        score += 3

    return min(score, 100)


def _isolation_level(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _generate_emergency_contacts(sector: int) -> list[dict[str, Any]]:
    """Generate simulated emergency contacts (neighbor referent + doctor)."""
    contacts = []
    # Neighbor referent
    if random.random() > 0.3:
        contacts.append({
            "type": "neighbor_referent",
            "name": f"M. {'Bernard' if random.random() > 0.5 else 'Moreau'}",
            "sector": sector,
            "phone": f"+33 6 {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}",
            "proximity": "Same building" if random.random() > 0.5 else "Same street",
        })
    # Doctor
    contacts.append({
        "type": "doctor",
        "name": f"Dr {'Martinez' if random.random() > 0.5 else 'Nguyen'}",
        "phone": f"+33 1 42 {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}",
    })
    # Family (if any)
    if random.random() > 0.6:
        contacts.append({
            "type": "family",
            "name": "Fils/Fille (simulated)",
            "phone": f"+33 6 {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}",
            "proximity": "Lives outside Paris",
        })
    return contacts


def main() -> None:
    """CLI entry point."""
    import sys

    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("mcp_server/data/beneficiaries.json")
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    generate_beneficiaries(output, count=count)


if __name__ == "__main__":
    main()
