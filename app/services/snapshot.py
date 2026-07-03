"""
Vigie — Dashboard snapshot capture.

Captures a screenshot of the Vigie Slack App Home dashboard (or any channel)
using the Slack API + renders it to a PNG file using a headless approach.

For the hackathon, we use a simple approach:
  1. Fetch the App Home dashboard blocks from Slack API
  2. Render them to a static HTML page using a Block Kit renderer
  3. Screenshot the HTML page using agent-browser (Playwright under the hood)

The resulting PNG is then passed to the VLM service for analysis.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from app.utils.logging import get_logger

log = get_logger("vigie.services.snapshot")


async def capture_app_home_screenshot(
    *,
    slack_client,
    user_id: str,
    output_path: str | None = None,
) -> str:
    """Capture a screenshot of the Vigie App Home dashboard for a user.

    Args:
        slack_client: AsyncWebClient instance with bot token.
        user_id: Slack user ID whose App Home to capture.
        output_path: Optional path for the PNG. If None, a temp file is used.

    Returns:
        Absolute path to the saved PNG file.

    Raises:
        RuntimeError: If Slack API call or screenshot capture fails.
    """
    # Step 1: Publish the dashboard to the user's App Home
    from app.blocks.dashboard import build_app_home_dashboard
    from app.state import get_state

    state = get_state()
    metrics = state.get_metrics()
    view = build_app_home_dashboard(metrics=metrics, user_id=user_id)

    try:
        await slack_client.views_publish(user_id=user_id, view=view)
    except Exception as e:
        log.warning("vigie.snapshot.publish_failed", error=str(e), user_id=user_id)
        # Continue anyway — the App Home may already have content from a previous publish

    # Step 2: Render the dashboard blocks to HTML
    html = _render_blocks_to_html(view.get("blocks", []))

    # Step 3: Save HTML to a temp file
    html_path = output_path.replace(".png", ".html") if output_path else None
    if html_path is None:
        html_fd, html_path = tempfile.mkstemp(suffix=".html", prefix="vigie_snapshot_")
        os.close(html_fd)
    Path(html_path).write_text(html, encoding="utf-8")

    # Step 4: Screenshot via agent-browser
    if output_path is None:
        png_fd, output_path = tempfile.mkstemp(suffix=".png", prefix="vigie_snapshot_")
        os.close(png_fd)

    try:
        proc = await asyncio.create_subprocess_exec(
            "agent-browser", "open", f"file://{html_path}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=30.0)

        # Set viewport
        proc = await asyncio.create_subprocess_exec(
            "agent-browser", "set", "viewport", "1440", "900",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10.0)

        # Wait for network idle
        proc = await asyncio.create_subprocess_exec(
            "agent-browser", "wait", "--load", "networkidle",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15.0)

        # Take full-page screenshot
        proc = await asyncio.create_subprocess_exec(
            "agent-browser", "screenshot", "--full", output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15.0)

        # Close browser
        proc = await asyncio.create_subprocess_exec(
            "agent-browser", "close",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=5.0)

    except asyncio.TimeoutError:
        raise RuntimeError("agent-browser timeout while capturing screenshot")
    except FileNotFoundError:
        raise RuntimeError("agent-browser CLI not found — install with: npm install -g agent-browser")

    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        raise RuntimeError(f"Screenshot capture failed or produced empty file: {output_path}")

    log.info(
        "vigie.snapshot.captured",
        path=output_path,
        size_bytes=os.path.getsize(output_path),
        user_id=user_id,
    )
    return output_path


def _render_blocks_to_html(blocks: list[dict]) -> str:
    """Render Slack Block Kit blocks to a standalone HTML page.

    This is a minimal renderer that covers the block types used in the Vigie
    dashboard (header, section, context, divider, actions). For production,
    consider using the official Slack Block Kit renderer.
    """
    import html as html_lib
    import json

    css = """
    <style>
        body {
            font-family: 'Lato', 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background: #1a1d21;
            color: #d1d2d3;
            margin: 0;
            padding: 24px;
            font-size: 15px;
            line-height: 1.46668;
        }
        .block { margin-bottom: 8px; }
        .header { font-size: 22px; font-weight: 700; padding: 8px 0; color: #ffffff; }
        .section { background: #1a1d21; padding: 8px 0; }
        .section .text { color: #d1d2d3; white-space: pre-wrap; }
        .context { font-size: 13px; color: #ababad; padding: 8px 0; }
        .divider { border-top: 1px solid #2e3235; margin: 16px 0; }
        .actions { display: flex; gap: 8px; padding: 8px 0; }
        .button {
            display: inline-block;
            padding: 0 12px;
            height: 28px;
            line-height: 28px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 700;
            text-decoration: none;
        }
        .button-primary { background: #007a5a; color: #ffffff; }
        .button-danger { background: #e01e5a; color: #ffffff; }
        .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 16px 0; }
        .kpi-card {
            background: #2e3235;
            padding: 16px;
            border-radius: 8px;
            text-align: center;
        }
        .kpi-value { font-size: 28px; font-weight: 700; color: #ffffff; }
        .kpi-label { font-size: 12px; color: #ababad; margin-top: 4px; }
        .alert { background: #e01e5a; color: white; padding: 12px; border-radius: 4px; margin: 12px 0; }
        .ok { background: #007a5a; color: white; padding: 12px; border-radius: 4px; margin: 12px 0; }
        table { width: 100%; border-collapse: collapse; margin: 12px 0; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #2e3235; }
        th { color: #ababad; font-size: 12px; text-transform: uppercase; }
    </style>
    """

    body_parts = []
    for block in blocks:
        btype = block.get("type")
        if btype == "header":
            text = block.get("text", {}).get("text", "")
            body_parts.append(f'<div class="block header">{html_lib.escape(text)}</div>')
        elif btype == "section":
            text = block.get("text", {})
            ttype = text.get("type", "plain_text")
            content = text.get("text", "")
            if ttype == "mrkdwn":
                # Minimal markdown: bold, italic, code
                content = (content
                    .replace("*", "**", 1) if "*" in content else content)
                import re
                content = re.sub(r"\*([^*]+)\*", r"<strong>\1</strong>", content)
                content = re.sub(r"_([^_]+)_", r"<em>\1</em>", content)
                content = re.sub(r"`([^`]+)`", r"<code>\1</code>", content)
            body_parts.append(f'<div class="block section"><div class="text">{content}</div></div>')
        elif btype == "context":
            elements = block.get("elements", [])
            parts = []
            for el in elements:
                if el.get("type") == "mrkdwn":
                    parts.append(el.get("text", ""))
                elif el.get("type") == "plain_text":
                    parts.append(html_lib.escape(el.get("text", "")))
            body_parts.append(f'<div class="block context">{" · ".join(parts)}</div>')
        elif btype == "divider":
            body_parts.append('<div class="block divider"></div>')
        elif btype == "actions":
            elements = block.get("elements", [])
            buttons = []
            for el in elements:
                if el.get("type") == "button":
                    text = html_lib.escape(el.get("text", {}).get("text", ""))
                    style = el.get("style", "")
                    cls = "button button-primary" if style == "primary" else "button button-danger" if style == "danger" else "button"
                    buttons.append(f'<span class="{cls}">{text}</span>')
            body_parts.append(f'<div class="block actions">{" ".join(buttons)}</div>')

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Vigie — Dashboard Snapshot</title>
    {css}
</head>
<body>
    {''.join(body_parts)}
</body>
</html>"""
