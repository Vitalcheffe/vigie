"""
Vigie — Scheduler.

Runs background jobs:
  - Daily report at 18:00 (Europe/Paris) during an active heatwave scenario
  - Canvas refresh every 5 minutes during an active scenario
  - RTS cache refresh every 30 minutes during an active scenario

Uses APScheduler AsyncIOScheduler so jobs run in the same event loop
as the Bolt app.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.utils.logging import get_logger

if TYPE_CHECKING:
    from app.orchestrator import VigieOrchestrator

log = get_logger("vigie.scheduler")

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Return the shared AsyncIOScheduler (created on first call)."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Europe/Paris")
    return _scheduler


def start_scheduler(orchestrator: VigieOrchestrator) -> AsyncIOScheduler:
    """
    Start the background scheduler with all Vigie jobs.

    Args:
        orchestrator: The VigieOrchestrator instance to use for jobs.

    Returns the started scheduler. The caller is responsible for
    awaiting scheduler.start() in the main event loop.
    """
    scheduler = get_scheduler()

    # Job 1: Daily report at 18:00 Europe/Paris (only fires if scenario active)
    scheduler.add_job(
        _job_daily_report,
        trigger=CronTrigger(hour=18, minute=0, timezone="Europe/Paris"),
        id="vigie_daily_report",
        kwargs={"orchestrator": orchestrator},
        replace_existing=True,
    )
    log.info("scheduler.job_added", job="vigie_daily_report", trigger="cron 18:00 Europe/Paris")

    # Job 2: Canvas refresh every 5 minutes (only fires if scenario active)
    scheduler.add_job(
        _job_refresh_canvas,
        trigger=IntervalTrigger(minutes=5),
        id="vigie_canvas_refresh",
        kwargs={"orchestrator": orchestrator},
        replace_existing=True,
    )
    log.info("scheduler.job_added", job="vigie_canvas_refresh", trigger="interval 5 min")

    # Job 3: RTS cache refresh every 30 minutes (proactive, so directives
    # are fresh when the daily report runs)
    scheduler.add_job(
        _job_refresh_rts,
        trigger=IntervalTrigger(minutes=30),
        id="vigie_rts_refresh",
        kwargs={"orchestrator": orchestrator},
        replace_existing=True,
    )
    log.info("scheduler.job_added", job="vigie_rts_refresh", trigger="interval 30 min")

    # Job 4: Check-in reminders every 2 hours (only fires if scenario active)
    scheduler.add_job(
        _job_send_reminders,
        trigger=IntervalTrigger(hours=2),
        id="vigie_reminders",
        kwargs={"orchestrator": orchestrator},
        replace_existing=True,
    )
    log.info("scheduler.job_added", job="vigie_reminders", trigger="interval 2h")

    # Job 5: VLM dashboard snapshot every 15 minutes during an active scenario.
    # Captures the App Home dashboard, runs VLM analysis, logs to audit.
    # Disabled by default — enable via env var VIGIE_VLM_SNAPSHOT_ENABLED=true.
    if os.environ.get("VIGIE_VLM_SNAPSHOT_ENABLED", "false").lower() in ("true", "1", "yes"):
        scheduler.add_job(
            _job_vlm_snapshot,
            trigger=IntervalTrigger(minutes=15),
            id="vigie_vlm_snapshot",
            kwargs={"orchestrator": orchestrator},
            replace_existing=True,
        )
        log.info("scheduler.job_added", job="vigie_vlm_snapshot", trigger="interval 15 min")

    return scheduler


async def _job_daily_report(orchestrator: VigieOrchestrator) -> None:
    """Generate the daily report at 18:00 — only if a scenario is active."""
    state = orchestrator.state
    if not state.is_scenario_active:
        log.debug("scheduler.daily_report.skipped_no_scenario")
        return

    log.info("scheduler.daily_report.firing")
    try:
        result = await orchestrator.generate_daily_report()
        log.info("scheduler.daily_report.done", status=result.get("status"))
    except Exception as e:
        log.error("scheduler.daily_report.failed", error=str(e))


async def _job_refresh_canvas(orchestrator: VigieOrchestrator) -> None:
    """Refresh the cellule-de-crise Canvas every 5 minutes during alert."""
    state = orchestrator.state
    if not state.is_scenario_active:
        return

    try:
        await orchestrator._update_cellule_crise_canvas()  # noqa: SLF001
        log.debug("scheduler.canvas_refresh.done")
    except Exception as e:
        log.warning("scheduler.canvas_refresh.failed", error=str(e))


async def _job_refresh_rts(orchestrator: VigieOrchestrator) -> None:
    """Refresh the RTS cache proactively so directives stay fresh."""
    try:
        orchestrator.rts.clear_cache()
        await orchestrator.rts.get_health_directives(department="75")
        log.debug("scheduler.rts_refresh.done")
    except Exception as e:
        log.warning("scheduler.rts_refresh.failed", error=str(e))


async def _job_send_reminders(orchestrator: VigieOrchestrator) -> None:
    """Send gentle check-in reminders to volunteers with pending check-ins."""
    state = orchestrator.state
    if not state.is_scenario_active:
        return

    try:
        from app.reminders import send_checkin_reminders
        result = await send_checkin_reminders(orchestrator.slack)
        log.info("scheduler.reminders.done", status=result.get("status"))
    except Exception as e:
        log.warning("scheduler.reminders.failed", error=str(e))


async def _job_vlm_snapshot(orchestrator: VigieOrchestrator) -> None:
    """Capture a dashboard snapshot and run VLM analysis every 15 minutes.

    Only fires if a scenario is active AND VIGIE_VLM_SNAPSHOT_ENABLED=true.
    Captures the App Home dashboard, runs VLM analysis, and logs to audit.
    If the VLM detects an ALERT state, posts a warning in #cellule-crise.
    """
    state = orchestrator.state
    if not state.is_scenario_active:
        return

    log.info("scheduler.vlm_snapshot.firing")

    try:
        from app.services.snapshot import capture_app_home_screenshot
        from app.services.vlm import get_vlm_service
        from app.utils.config import get_config

        cfg = get_config()
        # Use the bot's own user ID for the App Home snapshot
        # (the bot can always read its own App Home)
        bot_user_id = os.environ.get("VIGIE_BOT_USER_ID", "")
        if not bot_user_id:
            log.debug("scheduler.vlm_snapshot.skipped_no_bot_user_id")
            return

        # Capture screenshot
        snapshot_path = await capture_app_home_screenshot(
            slack_client=orchestrator.slack,
            user_id=bot_user_id,
            output_path=f"/tmp/vigie_vlm_snapshot_{int(__import__('time').time())}.png",
        )

        # Run VLM analysis (use_cache=False since the dashboard changes over time)
        service = get_vlm_service()
        analysis = await service.analyze_screenshot(snapshot_path, use_cache=False)

        log.info(
            "scheduler.vlm_snapshot.done",
            health=analysis.dashboard_health,
            coverage=analysis.coverage_percent,
            l3=analysis.l3_count,
            latency_ms=analysis.latency_ms,
        )

        # If ALERT state, post a warning in #cellule-crise
        if analysis.dashboard_health == "ALERT" and analysis.l3_count and analysis.l3_count > 0:
            try:
                await orchestrator.slack.chat_postMessage(
                    channel=cfg.slack.cellule_crise_channel_id or "",
                    text=(
                        f":eyes: *Vigie-VLM snapshot alert*\n"
                        f"Dashboard health: *ALERT*\n"
                        f"Coverage: {analysis.coverage_percent}%\n"
                        f"L2 (no answer): {analysis.l2_count}\n"
                        f"L3 (unconscious): {analysis.l3_count}\n\n"
                        f"_Summary:_ {analysis.summary}\n\n"
                        f"_Automated snapshot analysis — see audit log for details._"
                    ),
                )
            except Exception as post_err:
                log.warning("scheduler.vlm_snapshot.post_failed", error=str(post_err))

        # Clean up the snapshot file (keep last 3 for debugging)
        _cleanup_old_snapshots(keep=3)

    except Exception as e:
        log.warning("scheduler.vlm_snapshot.failed", error=str(e))


def _cleanup_old_snapshots(keep: int = 3) -> None:
    """Keep only the `keep` most recent VLM snapshots in /tmp."""
    import glob
    import time
    pattern = "/tmp/vigie_vlm_snapshot_*.png"
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    for old_file in files[keep:]:
        try:
            os.unlink(old_file)
        except OSError:
            pass


def stop_scheduler() -> None:
    """Shut down the scheduler (for graceful shutdown).

    Safe to call even if the scheduler was never started.
    """
    global _scheduler
    if _scheduler is not None:
        try:
            if _scheduler.running:
                _scheduler.shutdown(wait=False)
        except Exception as e:
            log.warning("scheduler.stop_failed", error=str(e))
        _scheduler = None
        log.info("scheduler.stopped")
