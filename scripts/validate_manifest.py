"""
Vigie — Manifest validator.

Validates the Slack app manifest against the known Slack manifest spec
rules. Catches errors BEFORE you paste the YAML into Slack.

Usage:
    python scripts/validate_manifest.py
    # or
    python scripts/validate_manifest.py --manifest path/to/manifest.yaml

Rules validated:
  - YAML syntax is valid
  - Required top-level sections exist (display_information, oauth_config, settings)
  - All OAuth scopes are in the Slack scope registry
  - All bot_events are in the Slack event registry
  - No empty strings (Slack rejects them)
  - No deprecated/removed fields
  - socket_mode_enabled requires no request_url
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


# ============================================================
# Slack OAuth scopes registry (bot scopes only, public API)
# Source: https://api.slack.com/scopes
# ============================================================
VALID_BOT_SCOPES = {
    # Messaging
    "chat:write",
    "chat:write.public",
    "chat:write.customize",
    "chat:write.invite",
    "im:history",
    "im:read",
    "im:write",
    "mpim:history",
    "mpim:read",
    "mpim:write",
    # Channels
    "channels:history",
    "channels:read",
    "channels:write",
    "channels:manage",
    "channels:join",
    # Groups (private channels)
    "groups:history",
    "groups:read",
    "groups:write",
    # Files
    "files:read",
    "files:write",
    # Users
    "users:read",
    "users:write",
    "users.profile:read",
    "users.profile:write",
    # Reactions
    "reactions:read",
    "reactions:write",
    # Bookmarks
    "bookmarks:read",
    "bookmarks:write",
    "bookmarks:group:write",
    # Pins
    "pins:read",
    "pins:write",
    # Usergroups
    "usergroups:read",
    "usergroups:write",
    # Team
    "team:read",
    # App mentions
    "app_mentions:read",
    # Commands
    "commands",
    # Workflows
    "workflows:read",
    "workflows:write",
    # Assistant (Slack AI — beta)
    "assistant:write",
    # Email
    "reminders:read",
    "reminders:write",
    # Stars
    "stars:read",
    "stars:write",
    # Search
    "search:read",
    # Links
    "links:read",
    "links:write",
    # Incoming webhook
    "incoming-webhook",
    # Bot user
    "bot",
    # DND
    "dnd:read",
    "dnd:write",
    # Emoji
    "emoji:read",
    # Views
    "views:read",
    # Workflow steps
    "workflow.steps:execute",
}


# ============================================================
# Slack bot events registry
# Source: https://api.slack.com/events
# ============================================================
VALID_BOT_EVENTS = {
    # Messages
    "message.channels",
    "message.im",
    "message.mpim",
    "message.groups",
    "message.app_home",
    "message.app_mentions",
    # App interactions
    "app_mention",
    "app_home_opened",
    "app_uninstalled",
    "app_rate_limits",
    "app_unfurl_domain",
    # Team
    "team_join",
    "team_rename",
    "team_domain_change",
    "emoji_changed",
    # Channels
    "channel_created",
    "channel_deleted",
    "channel_archive",
    "channel_unarchive",
    "channel_rename",
    "channel_id_changed",
    "member_joined_channel",
    "member_left_channel",
    # Groups
    "group_open",
    "group_close",
    "group_archive",
    "group_unarchive",
    "group_rename",
    "group_left",
    "group_history",
    # Files
    "file_created",
    "file_deleted",
    "file_public",
    "file_shared",
    "file_unshared",
    "file_change",
    "file_comment_added",
    "file_comment_edited",
    "file_comment_deleted",
    # Reactions
    "reaction_added",
    "reaction_removed",
    # Pins
    "pin_added",
    "pin_removed",
    # Stars
    "star_added",
    "star_removed",
    # User
    "user_change",
    "user_resource_removed",
    "user_resource_granted",
    # DND
    "dnd_updated",
    "dnd_updated_user",
    # Subteam
    "subteam_created",
    "subteam_updated",
    "subteam_members_changed",
    # Email domain
    "email_domain_changed",
    # Workflow
    "workflow_step_execute",
    "workflow_deleted",
    "workflow_published",
    "workflow_unpublished",
    "workflow_step_deleted",
    "workflow_steps_changed",
    # Functions (Slack Functions)
    "function_executed",
    # Shared channels
    "shared_channel_invite_received",
    "shared_channel_invite_accepted",
    "shared_channel_invite_approved",
    "shared_channel_invite_declined",
    "shared_channel_invite_revoked",
}


# ============================================================
# Known deprecated/removed manifest fields
# ============================================================
DEPRECATED_FIELDS = {
    "metadata": "Removed — not part of manifest spec",
    "message_menu_options": "Removed — non-standard field",
    "workflow_steps": "Deprecated — use new Workflow Builder steps",
    "always_online": "Removed — not a valid bot_user field",
    "first_name": "Removed — not a valid bot_user field",
    "last_name": "Removed — not a valid bot_user field",
}


class ManifestValidator:
    """Validates a Slack app manifest YAML."""

    def __init__(self, manifest_path: Path):
        self.path = manifest_path
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self) -> bool:
        """Run all validations. Returns True if no errors."""
        self.errors.clear()
        self.warnings.clear()

        # 1. YAML syntax
        try:
            text = self.path.read_text(encoding="utf-8")
            manifest = yaml.safe_load(text)
        except yaml.YAMLError as e:
            self.errors.append(f"YAML syntax error: {e}")
            return False
        except FileNotFoundError:
            self.errors.append(f"File not found: {self.path}")
            return False

        if not isinstance(manifest, dict):
            self.errors.append("Manifest must be a YAML mapping (dict)")
            return False

        # 2. Required sections
        self._check_required_sections(manifest)

        # 3. No empty strings
        self._check_no_empty_strings(manifest, path="root")

        # 4. Deprecated fields
        self._check_deprecated_fields(manifest, path="root")

        # 5. OAuth scopes
        self._check_oauth_scopes(manifest)

        # 6. Bot events
        self._check_bot_events(manifest)

        # 7. Socket Mode consistency
        self._check_socket_mode(manifest)

        return len(self.errors) == 0

    # ============================================================
    # Individual checks
    # ============================================================

    def _check_required_sections(self, manifest: dict) -> None:
        """Check that required top-level sections exist."""
        required = ["display_information", "oauth_config", "settings"]
        for section in required:
            if section not in manifest:
                self.errors.append(f"Missing required section: {section}")

        # display_information must have a name
        di = manifest.get("display_information", {})
        if not isinstance(di, dict) or not di.get("name"):
            self.errors.append("display_information.name is required")

        # oauth_config must have scopes.bot
        oc = manifest.get("oauth_config", {})
        if not isinstance(oc, dict):
            self.errors.append("oauth_config must be a mapping")
            return
        scopes = oc.get("scopes", {})
        if not isinstance(scopes, dict) or not scopes.get("bot"):
            self.errors.append("oauth_config.scopes.bot is required (must be a non-empty list)")

    def _check_no_empty_strings(self, obj: Any, path: str) -> None:
        """Recursively check for empty strings (Slack rejects them)."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if v == "":
                    self.errors.append(f"Empty string at {path}.{k} — Slack rejects empty values")
                else:
                    self._check_no_empty_strings(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                self._check_no_empty_strings(v, f"{path}[{i}]")

    def _check_deprecated_fields(self, obj: Any, path: str) -> None:
        """Check for deprecated/removed manifest fields."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in DEPRECATED_FIELDS:
                    self.errors.append(f"Deprecated field '{k}' at {path}: {DEPRECATED_FIELDS[k]}")
                else:
                    self._check_deprecated_fields(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                self._check_deprecated_fields(v, f"{path}[{i}]")

    def _check_oauth_scopes(self, manifest: dict) -> None:
        """Check that all bot scopes are valid."""
        scopes = manifest.get("oauth_config", {}).get("scopes", {}).get("bot", [])
        if not isinstance(scopes, list):
            return

        for scope in scopes:
            if scope not in VALID_BOT_SCOPES:
                self.warnings.append(f"Unknown OAuth scope: '{scope}' — may be invalid or beta")

    def _check_bot_events(self, manifest: dict) -> None:
        """Check that all bot_events are valid."""
        events = manifest.get("settings", {}).get("event_subscriptions", {}).get("bot_events", [])
        if not isinstance(events, list):
            return

        for event in events:
            if event not in VALID_BOT_EVENTS:
                self.errors.append(f"Invalid bot_event: '{event}'")

    def _check_socket_mode(self, manifest: dict) -> None:
        """Check Socket Mode consistency.

        If socket_mode_enabled is true, request_url should NOT be set
        (Socket Mode doesn't use HTTP endpoints).
        """
        settings = manifest.get("settings", {})
        if not isinstance(settings, dict):
            return

        socket_mode = settings.get("socket_mode_enabled", False)
        event_sub = settings.get("event_subscriptions", {})
        if isinstance(event_sub, dict):
            request_url = event_sub.get("request_url", "")
            if socket_mode and request_url:
                self.warnings.append(
                    "socket_mode_enabled=true but request_url is set — "
                    "Socket Mode doesn't use HTTP endpoints"
                )


def main() -> int:
    """CLI entry point. Returns 0 on success, 1 on validation errors."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate a Slack app manifest")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "manifest" / "app-manifest.yaml",
        help="Path to the manifest YAML (default: manifest/app-manifest.yaml)",
    )
    args = parser.parse_args()

    print(f"Validating manifest: {args.manifest}")
    print()

    validator = ManifestValidator(args.manifest)
    success = validator.validate()

    if validator.errors:
        print(f"❌ {len(validator.errors)} error(s):")
        for err in validator.errors:
            print(f"   ERROR: {err}")
        print()

    if validator.warnings:
        print(f"⚠️  {len(validator.warnings)} warning(s):")
        for warn in validator.warnings:
            print(f"   WARN:  {warn}")
        print()

    if success:
        print("✅ Manifest is valid (no errors).")
        if not validator.warnings:
            print("   No warnings either — ready to paste into Slack.")
        return 0
    else:
        print("❌ Manifest has errors — fix them before pasting into Slack.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
