"""
Vigie — Modal view builders.

Builds the Slack view payloads for structured-data modals:
  - vigie_modal_checkin   : volunteer submits a structured check-in
  - vigie_modal_anomaly   : user submits an anomaly report
  - vigie_modal_reassign  : user submits a reassignment
  - vigie_modal_escalate  : user submits manual escalation details
"""

from __future__ import annotations

from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.blocks.modals")


def build_checkin_modal(
    beneficiary_id: str,
    beneficiary_name: str,
    sector: str | int | None = None,
) -> dict[str, Any]:
    """Modal for a volunteer to submit a structured check-in."""
    private_metadata = f"checkin:{beneficiary_id}"
    return {
        "type": "modal",
        "callback_id": "vigie_modal_checkin",
        "private_metadata": private_metadata,
        "title": {"type": "plain_text", "text": "Check-in bénéficiaire", "emoji": True},
        "submit": {"type": "plain_text", "text": "Enregistrer", "emoji": True},
        "close": {"type": "plain_text", "text": "Annuler", "emoji": True},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Bénéficiaire :* {beneficiary_name} (`{beneficiary_id}`)\n"
                        + (f"*Secteur :* {sector}\n" if sector else "")
                        + "Renseignez l'état observé après votre appel téléphonique."
                    ),
                },
            },
            {"type": "divider"},
            {
                "type": "input",
                "block_id": "state_block",
                "label": {"type": "plain_text", "text": "État général"},
                "element": {
                    "type": "static_select",
                    "action_id": "state",
                    "placeholder": {"type": "plain_text", "text": "Sélectionnez un état"},
                    "options": [
                        {"text": {"type": "plain_text", "text": "OK — va bien"}, "value": "ok"},
                        {"text": {"type": "plain_text", "text": "Signal faible (fatigue, médicament...)"}, "value": "weak"},
                        {"text": {"type": "plain_text", "text": "Injoignable (3 appels sans réponse)"}, "value": "unreachable"},
                        {"text": {"type": "plain_text", "text": "Confus / désorienté"}, "value": "confused"},
                        {"text": {"type": "plain_text", "text": "Critique (au sol, inconscient...)"}, "value": "critical"},
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "notes_block",
                "optional": True,
                "label": {"type": "plain_text", "text": "Notes (observations libres)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "notes",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Ex: Mme Dupont fatiguée, demande renouvellement ordonnance antihypertenseur."},
                },
            },
            {
                "type": "input",
                "block_id": "action_block",
                "optional": True,
                "label": {"type": "plain_text", "text": "Action recommandée"},
                "element": {
                    "type": "static_select",
                    "action_id": "action",
                    "placeholder": {"type": "plain_text", "text": "Laissez Vigie décider"},
                    "options": [
                        {"text": {"type": "plain_text", "text": "Aucune (clôturer)"}, "value": "ok"},
                        {"text": {"type": "plain_text", "text": "Recherche pharmacie"}, "value": "pharmacy"},
                        {"text": {"type": "plain_text", "text": "Contacter voisin référent"}, "value": "neighbor"},
                        {"text": {"type": "plain_text", "text": "Escalader coordinateur médical"}, "value": "coord"},
                        {"text": {"type": "plain_text", "text": "Escalader SAMU (15)"}, "value": "samu"},
                    ],
                },
            },
        ],
    }


def build_anomaly_modal(trigger_message_ts: str, trigger_channel: str) -> dict[str, Any]:
    """Modal for the 'Signaler une anomalie' shortcut."""
    private_metadata = f"anomaly:{trigger_channel}:{trigger_message_ts}"
    return {
        "type": "modal",
        "callback_id": "vigie_modal_anomaly",
        "private_metadata": private_metadata,
        "title": {"type": "plain_text", "text": "Signaler une anomalie", "emoji": True},
        "submit": {"type": "plain_text", "text": "Envoyer", "emoji": True},
        "close": {"type": "plain_text", "text": "Annuler", "emoji": True},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Décrivez l'anomalie observée. Vigie l'analysera et proposera une action.",
                },
            },
            {
                "type": "input",
                "block_id": "beneficiary_block",
                "label": {"type": "plain_text", "text": "ID du bénéficiaire (ex: B023)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "beneficiary_id",
                    "placeholder": {"type": "plain_text", "text": "B023"},
                },
            },
            {
                "type": "input",
                "block_id": "level_block",
                "label": {"type": "plain_text", "text": "Niveau de gravité estimé"},
                "element": {
                    "type": "static_select",
                    "action_id": "level",
                    "options": [
                        {"text": {"type": "plain_text", "text": "Signal faible (niveau 1)"}, "value": "1"},
                        {"text": {"type": "plain_text", "text": "Escalade coordinateur (niveau 2)"}, "value": "2"},
                        {"text": {"type": "plain_text", "text": "Critique SAMU (niveau 3)"}, "value": "3"},
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "reason_block",
                "label": {"type": "plain_text", "text": "Motif / observation"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "reason",
                    "multiline": True,
                },
            },
        ],
    }


def build_reassign_modal(beneficiary_id: str) -> dict[str, Any]:
    """Modal for reassigning a beneficiary to another volunteer."""
    private_metadata = f"reassign:{beneficiary_id}"
    return {
        "type": "modal",
        "callback_id": "vigie_modal_reassign",
        "private_metadata": private_metadata,
        "title": {"type": "plain_text", "text": "Réassigner le bénéficiaire", "emoji": True},
        "submit": {"type": "plain_text", "text": "Réassigner", "emoji": True},
        "close": {"type": "plain_text", "text": "Annuler", "emoji": True},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Réassigner `{beneficiary_id}` à un autre bénévole.",
                },
            },
            {
                "type": "input",
                "block_id": "volunteer_block",
                "label": {"type": "plain_text", "text": "ID Slack du nouveau bénévole (ex: U12345)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "volunteer_id",
                    "placeholder": {"type": "plain_text", "text": "U12345"},
                },
            },
            {
                "type": "input",
                "block_id": "reason_block",
                "optional": True,
                "label": {"type": "plain_text", "text": "Motif (optionnel)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "reason",
                },
            },
        ],
    }


def build_escalate_modal(beneficiary_id: str) -> dict[str, Any]:
    """Modal for manual escalation with custom reason."""
    private_metadata = f"escalate:{beneficiary_id}"
    return {
        "type": "modal",
        "callback_id": "vigie_modal_escalate",
        "private_metadata": private_metadata,
        "title": {"type": "plain_text", "text": "Escalade manuelle", "emoji": True},
        "submit": {"type": "plain_text", "text": "Confirmer l'escalade", "emoji": True},
        "close": {"type": "plain_text", "text": "Annuler", "emoji": True},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":rotating_light: Vous allez déclencher une escalade pour `{beneficiary_id}`.",
                },
            },
            {
                "type": "input",
                "block_id": "level_block",
                "label": {"type": "plain_text", "text": "Niveau d'escalade"},
                "element": {
                    "type": "static_select",
                    "action_id": "level",
                    "options": [
                        {"text": {"type": "plain_text", "text": "1 — Signal faible (surveillance renforcée)"}, "value": "1"},
                        {"text": {"type": "plain_text", "text": "2 — Coordinateur médical"}, "value": "2"},
                        {"text": {"type": "plain_text", "text": "3 — Critique SAMU (15)"}, "value": "3"},
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "reason_block",
                "label": {"type": "plain_text", "text": "Motif détaillé"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "reason",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Décrivez la situation observée."},
                },
            },
        ],
    }
