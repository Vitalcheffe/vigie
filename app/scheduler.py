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
