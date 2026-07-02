"""
Vigie — Startup wrapper for Railway.

Catches all errors during startup and prints them to stdout so they
appear in Railway's deploy logs. Without this, Railway just shows
"FAILED" with no explanation.
"""

import sys
import traceback


def main() -> None:
    print("=== Vigie starting ===", flush=True)
    print(f"Python: {sys.version}", flush=True)
    print(f"Args: {sys.argv}", flush=True)

    # Check env vars
    import os
    required = ["SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET", "SLACK_APP_TOKEN"]
    for var in required:
        val = os.environ.get(var, "")
        if val:
            print(f"  ✓ {var} is set ({val[:20]}...)", flush=True)
        else:
            print(f"  ✗ {var} is MISSING", flush=True)

    print(f"  MCP_IN_PROCESS={os.environ.get('MCP_IN_PROCESS', 'false')}", flush=True)
    print(f"  PORT={os.environ.get('PORT', 'not set')}", flush=True)

    # Try importing modules
    try:
        print("=== Importing modules ===", flush=True)
        from app.utils.config import get_config
        print("  ✓ app.utils.config", flush=True)

        from app.utils.logging import setup_logging
        print("  ✓ app.utils.logging", flush=True)

        from slack_bolt.async_app import AsyncApp
        print("  ✓ slack_bolt.async_app", flush=True)

        from app.orchestrator import VigieOrchestrator
        print("  ✓ app.orchestrator", flush=True)

        from app.handlers import register_all
        print("  ✓ app.handlers", flush=True)

    except Exception as e:
        print(f"❌ IMPORT ERROR: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)

    # Try starting the app
    try:
        print("=== Starting app ===", flush=True)
        # On Railway (MCP_IN_PROCESS=true), skip the health server
        # because it conflicts with asyncio.run() in the main thread.
        # Socket Mode doesn't need an HTTP endpoint.
        if os.environ.get("MCP_IN_PROCESS", "false").lower() in ("true", "1", "yes"):
            print("  Skipping health server (Railway/Socket Mode mode)", flush=True)
            # Start the bot directly without the health server
            import asyncio
            from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
            from app.main import create_app, get_orchestrator
            from app.scheduler import start_scheduler

            app = create_app()
            orchestrator = get_orchestrator(app)
            scheduler = start_scheduler(orchestrator)

            import signal
            import sys

            def shutdown(signum, frame):
                print(f"Shutdown signal {signum}", flush=True)
                from app.scheduler import stop_scheduler
                stop_scheduler()
                sys.exit(0)

            signal.signal(signal.SIGINT, shutdown)
            signal.signal(signal.SIGTERM, shutdown)

            cfg = __import__("app.utils.config", fromlist=["get_config"]).get_config()
            if cfg.slack.app_token:
                print("  Starting Socket Mode...", flush=True)

                async def _run():
                    scheduler.start()
                    print("  Scheduler started", flush=True)
                    handler = AsyncSocketModeHandler(
                        app_token=cfg.slack.app_token.get_secret_value(),
                        app=app,
                    )
                    await handler.start_async()

                asyncio.run(_run())
            else:
                print("  ERROR: SLACK_APP_TOKEN not set", flush=True)
                sys.exit(1)
        else:
            # Normal mode (local dev) — use app.main.main()
            from app.main import main as app_main
            app_main()
    except Exception as e:
        print(f"❌ STARTUP ERROR: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
