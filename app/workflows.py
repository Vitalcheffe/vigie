"""
Vigie — Slack Workflow Builder custom steps.

Defines 2 custom workflow steps that admins can use in Slack's
Workflow Builder to integrate Vigie into custom automations:

  1. vigie_workflow_checkin — "Vigie — Assigner un check-in"
     Inputs: beneficiary_id, volunteer_id
     Outputs: checkin_id, anomaly_level

  2. vigie_workflow_alert — "Vigie — Vérifier alerte canicule"
     Inputs: department
     Outputs: alert_active, alert_level

These steps let non-developers build Vigie-powered workflows in the
Slack UI (e.g., "When a new member joins #onboarding, automatically
assign them a heatwave check-in roster").
"""

from __future__ import annotations

from typing import Any

from slack_bolt.async_app import AsyncApp
from slack_bolt.context.ack.async_ack import AsyncAck

from app.utils.logging import get_logger

log = get_logger("vigie.workflows")


def register(app: AsyncApp) -> None:
    """Register Vigie's custom Workflow Builder steps."""

    # ============================================================
    # Step 1: vigie_workflow_checkin
    # ============================================================

    @app.workflow_step("vigie_workflow_checkin")
    async def handle_checkin_step_edit(ack: AsyncAck, step: dict, body: dict, client) -> None:
        """Called when a user edits the step in Workflow Builder.

        Opens a configuration modal where the admin selects the
        beneficiary_id and volunteer_id inputs (can be workflow variables).
        """
        await ack()
        log.info("vigie.workflow.checkin.edit", user=body.get("user", {}).get("id"))

        modal = _build_checkin_step_modal(step)
        await client.views_open(trigger_id=body["trigger_id"], view=modal)

    @app.workflow_step("vigie_workflow_checkin")
    async def handle_checkin_step_execute(
        ack: AsyncAck,
        step: dict,
        body: dict,
        client,
    ) -> None:
        """Called when the workflow executes the step.

        Calls the Vigie orchestrator to assign a check-in.
        """
        await ack()
        log.info("vigie.workflow.checkin.execute", step_id=step.get("step_id"))

        inputs = step.get("inputs", {})
        beneficiary_id = inputs.get("beneficiary_id", {}).get("value")
        volunteer_id = inputs.get("volunteer_id", {}).get("value")

        if not beneficiary_id or not volunteer_id:
            await client.api_call(
                "workflows.stepFailed",
                json={
                    "workflow_step_execute_id": body.get("workflow_step_execute_id"),
                    "error": {"message": "beneficiary_id and volunteer_id are required"},
                },
            )
            return

        # Route through the orchestrator
        from slack_sdk.web.async_client import AsyncWebClient

        from app.orchestrator import VigieOrchestrator
        from app.utils.config import get_config

        cfg = get_config()
        slack_client = AsyncWebClient(token=cfg.slack.bot_token.get_secret_value())
        orch = VigieOrchestrator(slack_client=slack_client)

        try:
            result = await orch.process_volunteer_message(
                volunteer_id=volunteer_id,
                text=f"{beneficiary_id}: Workflow-triggered check-in",
            )

            if result.get("status") == "ok":
                await client.api_call(
                    "workflows.stepCompleted",
                    json={
                        "workflow_step_execute_id": body.get("workflow_step_execute_id"),
                        "outputs": {
                            "checkin_id": result.get("checkin_id", ""),
                            "anomaly_level": str(result.get("anomaly_level", 0)),
                            "beneficiary_id": beneficiary_id,
                        },
                    },
                )
            else:
                await client.api_call(
                    "workflows.stepFailed",
                    json={
                        "workflow_step_execute_id": body.get("workflow_step_execute_id"),
                        "error": {"message": result.get("message", "unknown error")},
                    },
                )
        except Exception as e:
            log.error("vigie.workflow.checkin.failed", error=str(e))
            await client.api_call(
                "workflows.stepFailed",
                json={
                    "workflow_step_execute_id": body.get("workflow_step_execute_id"),
                    "error": {"message": str(e)},
                },
            )

    # ============================================================
    # Step 2: vigie_workflow_alert
    # ============================================================

    @app.workflow_step("vigie_workflow_alert")
    async def handle_alert_step_edit(ack: AsyncAck, step: dict, body: dict, client) -> None:
        """Configuration modal for the alert-check step."""
        await ack()
        log.info("vigie.workflow.alert.edit", user=body.get("user", {}).get("id"))

        modal = _build_alert_step_modal(step)
        await client.views_open(trigger_id=body["trigger_id"], view=modal)

    @app.workflow_step("vigie_workflow_alert")
    async def handle_alert_step_execute(
        ack: AsyncAck,
        step: dict,
        body: dict,
        client,
    ) -> None:
        """Execute the alert-check step: query Météo-France for the department."""
        await ack()
        log.info("vigie.workflow.alert.execute", step_id=step.get("step_id"))

        inputs = step.get("inputs", {})
        department = inputs.get("department", {}).get("value", "75")

        from mcp_server.resources.weather_alerts import (
            fetch_meteo_france_vigilance,
        )

        try:
            alerts = await fetch_meteo_france_vigilance()
            dept_alerts = [a for a in alerts if a.get("department") == department]
            alert_active = any(
                a.get("phenomenon") == "canicule" and a.get("level") in ("orange", "rouge")
                for a in dept_alerts
            )
            alert_level = max(
                (a.get("level", "vert") for a in dept_alerts if a.get("phenomenon") == "canicule"),
                key=lambda x: {"vert": 0, "jaune": 1, "orange": 2, "rouge": 3}.get(x, 0),
                default="vert",
            )

            await client.api_call(
                "workflows.stepCompleted",
                json={
                    "workflow_step_execute_id": body.get("workflow_step_execute_id"),
                    "outputs": {
                        "alert_active": str(alert_active).lower(),
                        "alert_level": alert_level,
                        "department": department,
                        "alert_count": str(len(dept_alerts)),
                    },
                },
            )
        except Exception as e:
            log.error("vigie.workflow.alert.failed", error=str(e))
            await client.api_call(
                "workflows.stepFailed",
                json={
                    "workflow_step_execute_id": body.get("workflow_step_execute_id"),
                    "error": {"message": str(e)},
                },
            )

    log.debug("vigie.workflows.registered")


# ============================================================
# Modal builders
# ============================================================


def _build_checkin_step_modal(step: dict[str, Any]) -> dict[str, Any]:
    """Build the configuration modal for the check-in workflow step."""
    inputs = step.get("inputs", {})
    return {
        "type": "workflow_step",
        "callback_id": "vigie_workflow_checkin_modal",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Vigie — Assigner un check-in", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "Cet étape déclenche un check-in Vigie pour un bénéficiaire donné, "
                        "affecté à un bénévole. Vous pouvez utiliser des variables de workflow."
                    ),
                },
            },
            {"type": "divider"},
            {
                "type": "input",
                "block_id": "beneficiary_id_block",
                "label": {"type": "plain_text", "text": "ID du bénéficiaire (ex: B023)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "beneficiary_id",
                    "initial_value": inputs.get("beneficiary_id", {}).get("value", ""),
                    "placeholder": {"type": "plain_text", "text": "B023"},
                },
            },
            {
                "type": "input",
                "block_id": "volunteer_id_block",
                "label": {"type": "plain_text", "text": "ID Slack du bénévole (ex: U0123ABC)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "volunteer_id",
                    "initial_value": inputs.get("volunteer_id", {}).get("value", ""),
                    "placeholder": {"type": "plain_text", "text": "U0123ABC"},
                },
            },
        ],
    }


def _build_alert_step_modal(step: dict[str, Any]) -> dict[str, Any]:
    """Build the configuration modal for the alert-check workflow step."""
    inputs = step.get("inputs", {})
    return {
        "type": "workflow_step",
        "callback_id": "vigie_workflow_alert_modal",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Vigie — Vérifier alerte canicule", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "Cet étape interroge l'API Météo-France pour vérifier si une alerte "
                        "canicule est active dans le département spécifié. "
                        "Sorties : `alert_active`, `alert_level`, `alert_count`."
                    ),
                },
            },
            {"type": "divider"},
            {
                "type": "input",
                "block_id": "department_block",
                "label": {"type": "plain_text", "text": "Code département (ex: 75, 93, 13)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "department",
                    "initial_value": inputs.get("department", {}).get("value", "75"),
                    "placeholder": {"type": "plain_text", "text": "75"},
                },
            },
        ],
    }
