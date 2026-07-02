"""
Vigie — Slack AI service.

Wraps Slack AI capabilities (when available in the workspace) with an
OpenAI fallback for development sandboxes where Slack AI may not be
enabled. Four tasks are exposed:

  - transcribe_audio(file_id)  -> str
  - extract_structured(text)   -> dict (state, signals, action)
  - classify_anomaly(text)     -> tuple[int, list[str], str]
  - generate_daily_report(...) -> str

The fallback is transparent to callers — they always get the same shape
of return value regardless of which backend ran.
"""

from __future__ import annotations

import json
from typing import Any

from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.services.slack_ai")


# Prompts are kept short and deterministic. We want JSON out, not prose.
_TRANSCRIBE_HINT = "Transcription en français, sans ponctuation ajoutée, fidèle au texte original."

_EXTRACT_PROMPT = """Tu es un assistant qui structure des notes de check-in téléphonique de bénévoles.
À partir du texte suivant, produis un JSON strict avec ces champs :
  - state : "ok" | "weak_signal" | "needs_escalation" | "critical"
  - signals : liste de mots-clés parmi [medication_request, fatigue, confusion, unreachable, fall, breathing_issue, distress, isolated, other]
  - action_required : "none" | "pharmacy_lookup" | "neighbor_referent" | "medical_coordinator" | "samu"
  - confidence : float entre 0 et 1

Texte :
\"\"\"{text}\"\"\"

Réponds UNIQUEMENT avec le JSON, sans texte autour."""

_CLASSIFY_PROMPT = """Classifie la gravité d'une note de check-in bénévole en 4 niveaux :
  0 = OK (rien à signaler)
  1 = Signal faible (fatigue, demande médicament, isolation ressentie)
  2 = Escalade coordinateur (injoignable, confusion, chute suspectée)
  3 = Critique SAMU (inconscient, détresse respiratoire, au sol, urgence vitale)

Note :
\"\"\"{text}\"\"\"

Réponds avec un JSON : {{"level": 0|1|2|3, "signals": ["..."], "recommended": "ok"|"pharmacy"|"escalade_coord"|"escalade_samu", "confidence": 0.0-1.0}}"""

_REPORT_PROMPT = """Tu rédiges le rapport quotidien de la cellule de crise Vigie.

Données du jour :
- Date : {date}
- Bénéficiaires à contacter : {total}
- Bénéficiaires contactés : {contacted} ({coverage_pct}%)
- Check-in OK : {ok_count}
- Signaux faibles : {weak_count}
- Escalades coordinateur : {coord_count}
- Escalades critiques (SAMU) : {samu_count}
- Latence moyenne d'escalade : {avg_escalade_latency}
- Bénéficiaires non contactés > 72h : {unreachable_72h}
- Signaux faibles à surveiller demain : {weak_signals_list}

Directives sanitaires fraîches (RTS) :
{rts_directives}

Rédige un rapport en 4 paragraphes :
1. Synthèse du jour (1-2 phrases)
2. Points d'attention (liste à puces)
3. Recommandations pour demain (liste à puces)
4. Sources citées (liste à puces)

Pas de mark-up Slack, juste du texte brut structuré."""


class SlackAIService:
    """Cognitive layer for Vigie — transcription, extraction, classification, reports."""

    def __init__(self) -> None:
        cfg = get_config().slack_ai
        self.use_native_slack_ai = cfg.enabled
        self.openai_key = cfg.openai_api_key.get_secret_value() if cfg.openai_api_key else None
        self.openai_model = cfg.openai_model
        self.whisper_model = cfg.openai_whisper_model

        if not self.use_native_slack_ai and not self.openai_key:
            log.warning("slack_ai.no_backend_configured")
        else:
            log.info(
                "slack_ai.configured",
                backend="slack_native" if self.use_native_slack_ai else "openai_fallback",
                model=cfg.model if self.use_native_slack_ai else self.openai_model,
            )

    async def transcribe_audio(self, file_bytes: bytes, filename: str) -> str:
        """
        Transcribe a voice note (audio file) to text.

        Tries Slack AI audio translation first, falls back to OpenAI Whisper.
        """
        if self.use_native_slack_ai:
            try:
                return await self._slack_ai_transcribe(file_bytes, filename)
            except Exception as e:
                log.warning("slack_ai.native_transcribe_failed", error=str(e))

        if self.openai_key:
            return await self._openai_whisper(file_bytes, filename)

        log.error("slack_ai.no_transcription_backend")
        raise RuntimeError("No transcription backend available")

    async def extract_structured(self, text: str) -> dict[str, Any]:
        """
        Extract structured data (state, signals, action) from a free-text note.

        Returns:
            {
                "state": "ok" | "weak_signal" | "needs_escalation" | "critical",
                "signals": [...],
                "action_required": "none" | "pharmacy_lookup" | ...,
                "confidence": 0.0-1.0
            }
        """
        prompt = _EXTRACT_PROMPT.format(text=text[:2000])
        raw = await self._chat_complete(prompt, json_mode=True)
        return _safe_json(raw, default={"state": "ok", "signals": [], "action_required": "none", "confidence": 0.5})

    async def classify_anomaly(self, text: str) -> tuple[int, list[str], str]:
        """
        Classify the anomaly level of a check-in note.

        Returns (level, signals, recommended_action).
        level: 0 (OK) / 1 (weak) / 2 (escalate coord) / 3 (SAMU)
        recommended: "ok" / "pharmacy" / "escalade_coord" / "escalade_samu"
        """
        prompt = _CLASSIFY_PROMPT.format(text=text[:2000])
        raw = await self._chat_complete(prompt, json_mode=True)
        parsed = _safe_json(
            raw,
            default={"level": 0, "signals": [], "recommended": "ok", "confidence": 0.5},
        )

        level = int(parsed.get("level", 0))
        level = max(0, min(3, level))
        signals = parsed.get("signals", []) or []
        recommended = parsed.get("recommended", "ok")
        valid_actions = {"ok", "pharmacy", "escalade_coord", "escalade_samu"}
        if recommended not in valid_actions:
            recommended = "ok" if level == 0 else "escalade_coord" if level == 2 else "escalade_samu"

        return level, signals, recommended

    async def generate_daily_report(
        self,
        date: str,
        total: int,
        contacted: int,
        ok_count: int,
        weak_count: int,
        coord_count: int,
        samu_count: int,
        avg_escalade_latency: str,
        unreachable_72h: int,
        weak_signals_list: list[str],
        rts_directives: list[str],
    ) -> str:
        """Generate the daily Vigie report for the cellule de crise."""
        coverage_pct = int((contacted / total) * 100) if total > 0 else 0
        prompt = _REPORT_PROMPT.format(
            date=date,
            total=total,
            contacted=contacted,
            coverage_pct=coverage_pct,
            ok_count=ok_count,
            weak_count=weak_count,
            coord_count=coord_count,
            samu_count=samu_count,
            avg_escalade_latency=avg_escalade_latency,
            unreachable_72h=unreachable_72h,
            weak_signals_list=", ".join(weak_signals_list) or "aucun",
            rts_directives="\n".join(f"- {d}" for d in rts_directives) or "- (aucune directive fraîche)",
        )
        return await self._chat_complete(prompt, json_mode=False, max_tokens=800)

    # ============================================================
    # Backend implementations
    # ============================================================

    async def _slack_ai_transcribe(self, file_bytes: bytes, filename: str) -> str:
        """
        Use Slack AI's native audio translation.

        TODO: Slack AI audio API endpoint TBD. For now, this is a placeholder
        that the slack_bolt Assistant API will populate. When Slack AI is enabled
        in the workspace, the bot's assistant:write scope allows direct
        conversation with Slack AI.

        As a stop-gap, we delegate to OpenAI Whisper even when Slack AI is
        "preferred" — this keeps the demo functional in sandboxes where Slack
        AI audio is not yet available.
        """
        if self.openai_key:
            return await self._openai_whisper(file_bytes, filename)
        raise RuntimeError("Slack AI audio endpoint not yet wired; OpenAI key missing for fallback")

    async def _openai_whisper(self, file_bytes: bytes, filename: str) -> str:
        """Transcribe with OpenAI Whisper-1."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.openai_key)
        log.debug("slack_ai.whisper.call", filename=filename, bytes=len(file_bytes))
        try:
            result = await client.audio.transcriptions.create(
                model=self.whisper_model,
                file=(filename, file_bytes),
                language="fr",
                prompt=_TRANSCRIBE_HINT,
            )
            return result.text
        finally:
            await client.close()

    async def _chat_complete(self, prompt: str, *, json_mode: bool, max_tokens: int = 400) -> str:
        """Chat completion via OpenAI (fallback for Slack AI native chat)."""
        if not self.openai_key:
            raise RuntimeError("No chat backend available (openai_api_key not set)")

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.openai_key)
        try:
            kwargs: dict[str, Any] = {
                "model": self.openai_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": max_tokens,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = await client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        finally:
            await client.close()


def _safe_json(text: str, *, default: dict[str, Any]) -> dict[str, Any]:
    """Parse JSON from a possibly-noisy model output. Returns default on failure."""
    if not text:
        return default
    text = text.strip()
    # Strip ```json fences if present
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find the first { ... } block
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        log.warning("slack_ai.json_parse_failed", text_preview=text[:200])
        return default


# Singleton accessor
_service: SlackAIService | None = None


def get_slack_ai_service() -> SlackAIService:
    """Return the shared SlackAIService instance."""
    global _service
    if _service is None:
        _service = SlackAIService()
    return _service
