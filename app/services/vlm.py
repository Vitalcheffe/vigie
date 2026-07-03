"""
Vigie — Z-AI VLM (Vision Language Model) service.

Analyzes Slack dashboard screenshots to extract crisis-cell state and
detect anomalies invisible to text-only LLMs. Used by:
  - Boot-time self-check (verifies VLM is reachable)
  - Periodic dashboard snapshots (future use)
  - On-demand screenshot analysis via `/vigie inspect`

Backend: `z-ai vision` CLI subprocess (same pattern as zai_llm.py).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

from app.utils.logging import get_logger

log = get_logger("vigie.services.vlm")


# ============================================================
# System prompt — Vigie-VLM
# ============================================================
# This prompt is the single source of truth for what the VLM must extract
# from any Vigie dashboard screenshot. Keep it stable across calls so that
# metrics from the stress test remain comparable.
# ============================================================

VIGIE_VLM_SYSTEM_PROMPT = """Tu es Vigie-VLM, un assistant visuel dédié à l'analyse de captures d'écran du bot Slack Vigie (prévention des décès par isolation pendant les canicules).

Ta mission : analyser une capture d'écran du dashboard Vigie et produire un rapport structuré.

Tu dois extraire ces champs :
1. COVERAGE_PERCENT: pourcentage de couverture affiché (ENTIER sans signe %, ex: 94 ; null si absent)
2. AVG_LATENCY_MIN: latence moyenne de check-in affichée en minutes (ENTIER, ex: 7 ; null si absent)
3. L2_COUNT: nombre d'escalades L2 - bénéficiaires sans réponse (ENTIER, ex: 2)
4. L3_COUNT: nombre d'escalades L3 - bénéficiaires inconscients (ENTIER, ex: 1)
5. CRISIS_MSG_COUNT: nombre de messages dans #cellule-crise (ENTIER, ex: 43)
6. TOP_SECTORS: liste des noms de secteurs visibles (ARRAY de STRINGS, ex: ["secteur-1", "secteur-2"])
7. ACTIVE_ALERTS: liste des bénéficiaires en alerte L1/L2/L3 (ARRAY d'objets {"name": "B018 - Monique B.", "level": "L3"} où level ∈ {"L1", "L2", "L3"})
8. DASHBOARD_HEALTH: "OK" si COVERAGE_PERCENT >= 90 ET L3_COUNT == 0, sinon "ALERT" (STRING)
9. SUMMARY: 1 phrase en français résumant l'état global du dispositif (STRING)

RÈGLES STRICTES:
- Réponds UNIQUEMENT avec un objet JSON valide. Pas de texte avant. Pas de texte après. Pas de markdown. Pas de ```json.
- Tous les nombres (COVERAGE_PERCENT, AVG_LATENCY_MIN, L2_COUNT, L3_COUNT, CRISIS_MSG_COUNT) DOIVENT être des entiers JSON (ex: 94), JAMAIS des strings (ex: "94%").
- Si une valeur numérique n'est pas visible, utilise null (pas 0, pas "N/A").
- Si un array est vide ou non visible, utilise [].
- Ne suppose JAMAIS une valeur non visible. Si tu hésites, mets null ou [].
- Pour ACTIVE_ALERTS, inclus uniquement les bénéficiaires explicitement marqués L1/L2/L3 dans la capture.
- Pour les noms dans ACTIVE_ALERTS, utilise le format "B<id> - <Prénom> <Initiale>." si visible (ex: "B018 - Monique B."), sinon juste le nom.

EXEMPLE DE RÉPONSE ATTENDUE:
{"COVERAGE_PERCENT": 94, "AVG_LATENCY_MIN": 7, "L2_COUNT": 2, "L3_COUNT": 1, "CRISIS_MSG_COUNT": 43, "TOP_SECTORS": ["secteur-1", "secteur-2", "secteur-3"], "ACTIVE_ALERTS": [{"name": "B018 - Monique B.", "level": "L3"}, {"name": "B007 - Lucien P.", "level": "L2"}], "DASHBOARD_HEALTH": "ALERT", "SUMMARY": "Cellule active, 1 cas critique SAMU en cours sur 47 bénéficiaires suivis."}"""

VIGIE_VLM_USER_PROMPT = "Analyse cette capture du dashboard Vigie et réponds en JSON."


# ============================================================
# Data model
# ============================================================


@dataclass
class DashboardAnalysis:
    """Structured analysis of a Vigie dashboard screenshot."""

    coverage_percent: int | None = None
    avg_latency_min: int | None = None
    l2_count: int | None = None
    l3_count: int | None = None
    crisis_msg_count: int | None = None
    top_sectors: list[str] = field(default_factory=list)
    active_alerts: list[dict[str, str]] = field(default_factory=list)
    dashboard_health: str = "UNKNOWN"
    summary: str = ""
    raw_content: str = ""
    parse_error: str | None = None
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "coverage_percent": self.coverage_percent,
            "avg_latency_min": self.avg_latency_min,
            "l2_count": self.l2_count,
            "l3_count": self.l3_count,
            "crisis_msg_count": self.crisis_msg_count,
            "top_sectors": self.top_sectors,
            "active_alerts": self.active_alerts,
            "dashboard_health": self.dashboard_health,
            "summary": self.summary,
            "latency_ms": self.latency_ms,
            "parse_error": self.parse_error,
        }


# ============================================================
# VLM Service
# ============================================================


class VigieVLMService:
    """Vision Language Model service for Vigie dashboard analysis."""

    # Cache: keyed by (image_path, image_mtime) -> DashboardAnalysis
    # Avoids re-analyzing the same screenshot (15s per call saved).
    _cache: dict[tuple[str, float], DashboardAnalysis] = {}
    _cache_max_size: int = 32

    # Counters for health endpoint
    _stats: dict[str, int] = {
        "calls_total": 0,
        "calls_ok": 0,
        "calls_failed": 0,
        "cache_hits": 0,
        "parse_errors": 0,
    }

    def __init__(self, timeout: float = 180.0) -> None:
        self.timeout = timeout
        log.info("vigie.vlm.service_initialized", timeout=timeout)

    async def analyze_screenshot(self, image_path: str, *, use_cache: bool = True) -> DashboardAnalysis:
        """
        Analyze a Vigie dashboard screenshot and return a structured analysis.

        Args:
            image_path: Absolute path to the PNG/JPG screenshot.
            use_cache: If True, return cached result when the image hasn't changed.

        Returns:
            DashboardAnalysis with extracted fields, or with parse_error set.
        """
        # Check cache (keyed by path + mtime to invalidate on file change)
        cache_key = None
        if use_cache:
            try:
                mtime = os.path.getmtime(image_path)
                cache_key = (image_path, mtime)
                cached = self._cache.get(cache_key)
                if cached is not None:
                    self._stats["cache_hits"] += 1
                    log.info(
                        "vigie.vlm.cache_hit",
                        image_path=image_path,
                        coverage=cached.coverage_percent,
                    )
                    return cached
            except OSError:
                # File may not exist yet — let the subprocess fail naturally
                pass

        self._stats["calls_total"] += 1
        start = asyncio.get_event_loop().time()
        try:
            # z-ai vision CLI has no --system flag, so the system prompt is
            # embedded in the user prompt as a single combined --prompt argument.
            combined_prompt = f"{VIGIE_VLM_SYSTEM_PROMPT}\n\n{VIGIE_VLM_USER_PROMPT}"
            proc = await asyncio.create_subprocess_exec(
                "z-ai", "vision",
                "-p", combined_prompt,
                "-i", image_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)

            latency_ms = (asyncio.get_event_loop().time() - start) * 1000.0

            if proc.returncode != 0:
                err = stderr.decode("utf-8", errors="replace")[:300]
                self._stats["calls_failed"] += 1
                log.warning(
                    "vigie.vlm.call_failed",
                    returncode=proc.returncode,
                    error=err,
                    latency_ms=latency_ms,
                )
                return DashboardAnalysis(
                    parse_error=f"rc={proc.returncode}: {err}",
                    latency_ms=latency_ms,
                )

            raw = stdout.decode("utf-8", errors="replace")
            content = self._extract_content(raw)
            analysis = self._parse_analysis(content)
            analysis.latency_ms = latency_ms
            analysis.raw_content = content

            # Update stats
            self._stats["calls_ok"] += 1
            if analysis.parse_error:
                self._stats["parse_errors"] += 1

            # Cache the result (LRU-ish: evict oldest entry if cache is full)
            if cache_key is not None and not analysis.parse_error:
                if len(self._cache) >= self._cache_max_size:
                    # Evict oldest entry (FIFO — simple, good enough for this use case)
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                self._cache[cache_key] = analysis

            log.info(
                "vigie.vlm.analyzed",
                coverage=analysis.coverage_percent,
                l2=analysis.l2_count,
                l3=analysis.l3_count,
                health=analysis.dashboard_health,
                latency_ms=latency_ms,
                cached=False,
            )
            return analysis

        except asyncio.TimeoutError:
            latency_ms = (asyncio.get_event_loop().time() - start) * 1000.0
            self._stats["calls_failed"] += 1
            log.warning("vigie.vlm.timeout", timeout=self.timeout, latency_ms=latency_ms)
            return DashboardAnalysis(
                parse_error=f"timeout_{self.timeout}s",
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (asyncio.get_event_loop().time() - start) * 1000.0
            self._stats["calls_failed"] += 1
            log.warning("vigie.vlm.error", error=str(e), latency_ms=latency_ms)
            return DashboardAnalysis(
                parse_error=f"exc={type(e).__name__}:{str(e)[:200]}",
                latency_ms=latency_ms,
            )

    def health(self) -> dict[str, Any]:
        """Return VLM service health metrics for the /vlm/health endpoint."""
        return {
            "ok": self._stats["calls_failed"] < max(1, self._stats["calls_total"]),
            "stats": dict(self._stats),
            "cache_size": len(self._cache),
            "cache_max": self._cache_max_size,
            "timeout_s": self.timeout,
        }

    def clear_cache(self) -> int:
        """Clear the VLM result cache. Returns the number of entries cleared."""
        n = len(self._cache)
        self._cache.clear()
        log.info("vigie.vlm.cache_cleared", entries_cleared=n)
        return n

    def _extract_content(self, raw_stdout: str) -> str:
        """Extract the assistant message content from z-ai CLI JSON output.

        The CLI prints `🚀 Initializing...` then a JSON block. We find the
        first balanced `{...}` block and pull choices[0].message.content.
        """
        start = raw_stdout.find("{")
        if start == -1:
            return raw_stdout.strip()
        try:
            decoder = json.JSONDecoder()
            data, _ = decoder.raw_decode(raw_stdout[start:])
            if isinstance(data, dict):
                choices = data.get("choices") or []
                if choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content", "") or ""
                    if content:
                        return content
                # Fallback: maybe a flat shape
                return data.get("content", "") or data.get("response", "") or raw_stdout
            return str(data)
        except (json.JSONDecodeError, ValueError):
            return raw_stdout.strip()

    def _parse_analysis(self, content: str) -> DashboardAnalysis:
        """Parse the VLM JSON content into a DashboardAnalysis."""
        analysis = DashboardAnalysis()

        # Strip markdown fences if present
        text = content.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1] if text.count("```") >= 2 else text
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        # Find the JSON object
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            analysis.parse_error = "no_json_object_found"
            analysis.summary = text[:200]
            return analysis

        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as e:
            analysis.parse_error = f"json_decode_error:{e}"
            analysis.summary = text[:200]
            return analysis

        # Map fields (tolerant of snake_case or SCREAMING_SNAKE)
        def _get(*keys: str) -> Any:
            for k in keys:
                if k in data and data[k] is not None:
                    return data[k]
            return None

        coverage = _get("COVERAGE_PERCENT", "coverage_percent", "coverage")
        if coverage is not None:
            try:
                analysis.coverage_percent = int(str(coverage).replace("%", "").strip())
            except (ValueError, TypeError):
                pass

        latency = _get("AVG_LATENCY_MIN", "avg_latency_min", "avg_latency")
        if latency is not None:
            try:
                # Could be "7min" or "7 min" or "7"
                cleaned = str(latency).lower().replace("min", "").replace("m", "").strip()
                analysis.avg_latency_min = int(cleaned)
            except (ValueError, TypeError):
                pass

        l2 = _get("L2_COUNT", "l2_count")
        if l2 is not None:
            try:
                analysis.l2_count = int(l2)
            except (ValueError, TypeError):
                pass

        l3 = _get("L3_COUNT", "l3_count")
        if l3 is not None:
            try:
                analysis.l3_count = int(l3)
            except (ValueError, TypeError):
                pass

        crisis_msg = _get("CRISIS_MSG_COUNT", "crisis_msg_count")
        if crisis_msg is not None:
            try:
                analysis.crisis_msg_count = int(crisis_msg)
            except (ValueError, TypeError):
                pass

        sectors = _get("TOP_SECTORS", "top_sectors")
        if isinstance(sectors, list):
            analysis.top_sectors = [str(s) for s in sectors]

        alerts = _get("ACTIVE_ALERTS", "active_alerts")
        if isinstance(alerts, list):
            cleaned_alerts: list[dict[str, str]] = []
            for a in alerts:
                if isinstance(a, dict):
                    cleaned_alerts.append({
                        "name": str(a.get("name", a.get("nom", ""))),
                        "level": str(a.get("level", a.get("niveau", ""))),
                    })
            analysis.active_alerts = cleaned_alerts

        health = _get("DASHBOARD_HEALTH", "dashboard_health")
        if isinstance(health, str) and health.upper() in {"OK", "ALERT"}:
            analysis.dashboard_health = health.upper()
        else:
            # Compute from rules
            if (
                analysis.coverage_percent is not None
                and analysis.l3_count is not None
            ):
                analysis.dashboard_health = (
                    "OK" if analysis.coverage_percent >= 90 and analysis.l3_count == 0 else "ALERT"
                )

        summary = _get("SUMMARY", "summary")
        if isinstance(summary, str):
            analysis.summary = summary

        return analysis


# ============================================================
# Boot-time self-check
# ============================================================


async def boot_self_check(image_path: str | None = None) -> dict[str, Any]:
    """
    Run a boot-time self-check of the VLM service.

    If image_path is provided, runs a real VLM call. Otherwise just verifies
    the z-ai CLI is reachable.

    Returns a dict suitable for logging / health endpoint.
    """
    log.info("vigie.vlm.boot_self_check.start", image_path=image_path)

    # Step 1: verify z-ai CLI is installed
    try:
        proc = await asyncio.create_subprocess_exec(
            "z-ai", "--help",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10.0)
        cli_ok = proc.returncode == 0 or proc.returncode == 1  # --help may exit 1 on this CLI
    except Exception as e:
        log.error("vigie.vlm.boot_self_check.cli_missing", error=str(e))
        return {
            "ok": False,
            "step": "cli_check",
            "error": f"z-ai CLI not reachable: {e}",
        }

    if not image_path:
        log.info("vigie.vlm.boot_self_check.cli_ok")
        return {"ok": True, "step": "cli_check", "image_analyzed": False}

    # Step 2: real VLM call
    service = VigieVLMService(timeout=60.0)
    analysis = await service.analyze_screenshot(image_path)

    if analysis.parse_error:
        log.warning(
            "vigie.vlm.boot_self_check.parse_error",
            error=analysis.parse_error,
            latency_ms=analysis.latency_ms,
        )
        return {
            "ok": False,
            "step": "vlm_call",
            "error": analysis.parse_error,
            "latency_ms": analysis.latency_ms,
        }

    log.info(
        "vigie.vlm.boot_self_check.ok",
        coverage=analysis.coverage_percent,
        health=analysis.dashboard_health,
        latency_ms=analysis.latency_ms,
    )
    return {
        "ok": True,
        "step": "vlm_call",
        "image_analyzed": True,
        "analysis": analysis.to_dict(),
    }


# ============================================================
# Singleton
# ============================================================

_service: VigieVLMService | None = None


def get_vlm_service() -> VigieVLMService:
    """Return the shared VigieVLMService instance."""
    global _service
    if _service is None:
        _service = VigieVLMService()
    return _service
