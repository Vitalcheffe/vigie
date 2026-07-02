"""
Vigie — Remote Slack manifest validator.

Uses the official Slack API endpoint apps.manifest.validate to validate
the manifest against Slack's actual server-side schema.

Requires a Slack app configuration token (xoxe.xoxp-...). Generate one
at https://api.slack.com/apps → "Your App Configuration Tokens" →
"Generate Token".

Usage:
    export SLACK_CONFIG_TOKEN=xoxe.xoxp-...
    python scripts/validate_manifest_remote.py
    # or
    python scripts/validate_manifest_remote.py --token xoxe.xoxp-... --manifest manifest/app-manifest.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx


def validate_manifest_remote(
    manifest: dict[str, Any],
    token: str,
) -> dict[str, Any]:
    """Call Slack's apps.manifest.validate endpoint.

    Args:
        manifest: The manifest dict (will be sent as JSON)
        token: Slack app configuration token (xoxe.xoxp-...)

    Returns:
        Slack API response dict. Key fields:
          - ok: True if valid
          - errors: list of {pointer, message} if invalid
          - warnings: list of {pointer, message} if warnings
    """
    response = httpx.post(
        "https://slack.com/api/apps.manifest.validate",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json={"manifest": manifest},
        timeout=30.0,
    )
    return response.json()


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate the Slack manifest against the real Slack API"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "manifest" / "app-manifest.json",
        help="Path to the manifest JSON (default: manifest/app-manifest.json)",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=os.environ.get("SLACK_CONFIG_TOKEN", ""),
        help="Slack app config token (xoxe.xoxp-...). Defaults to $SLACK_CONFIG_TOKEN.",
    )
    args = parser.parse_args()

    if not args.token:
        print("ERROR: No Slack config token provided.")
        print()
        print("Get one at:")
        print("  1. Go to https://api.slack.com/apps")
        print("  2. Scroll to 'Your App Configuration Tokens'")
        print("  3. Click 'Generate Token'")
        print("  4. Export it: export SLACK_CONFIG_TOKEN=xoxe.xoxp-...")
        print("  5. Re-run this script")
        return 2

    if not args.manifest.exists():
        print(f"ERROR: Manifest file not found: {args.manifest}")
        return 2

    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in manifest: {e}")
        return 2

    print(f"Validating manifest against Slack API: {args.manifest}")
    print(f"Token: {args.token[:20]}...")
    print()

    try:
        result = validate_manifest_remote(manifest, args.token)
    except httpx.HTTPError as e:
        print(f"ERROR: HTTP request failed: {e}")
        return 1

    if result.get("ok"):
        print("✅ Slack says: manifest is valid!")
        warnings = result.get("warnings", [])
        if warnings:
            print(f"⚠️  {len(warnings)} warning(s):")
            for w in warnings:
                print(f"   {w.get('pointer', '?')}: {w.get('message', '?')}")
        else:
            print("   No warnings.")
        return 0
    else:
        print(f"❌ Slack rejected the manifest: {result.get('error', 'unknown error')}")
        print()
        errors = result.get("errors", [])
        if errors:
            print(f"   {len(errors)} error(s):")
            for err in errors:
                ptr = err.get("pointer", "?")
                msg = err.get("message", "?")
                print(f"   - {ptr}: {msg}")
        print()
        print("Full response:")
        print(json.dumps(result, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
