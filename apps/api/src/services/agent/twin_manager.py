"""Manages digital twins — per-user personalization profiles.

Pattern extracted from Claude Code's autoDream system.
Supports both rule-based and LLM-powered dream consolidation.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.twin import TwinObservation, UserTwin

logger = logging.getLogger(__name__)

CONSOLIDATION_PROMPT = """\
You are analyzing a GCC lawyer's interaction patterns with their AI legal colleague, Amin.
Your task is to update their personalization profile based on new observations.

## Current Profile
```json
{current_profile}
```

## New Observations Since Last Consolidation
{observations_text}

## Instructions
Analyze the observations and return a JSON object with these fields (only include fields that have meaningful updates):

{{
  "profile": {{}},           // name, title, firm, jurisdiction focus, practice areas
  "preferences": {{}},       // language, response style, formality, detail level
  "work_patterns": {{}},     // active hours, tool usage frequency, topic focus areas
  "drafting_style": {{}},    // clause preferences, template preferences, formatting
  "review_priorities": {{}}, // risk areas they care most about, common focus areas
  "learned_corrections": [], // array of correction summaries from this batch
  "personality_model": {{}}  // communication style traits, stress indicators
}}

Merge new insights with existing profile data. Preserve existing values unless observations
clearly supersede them. Be concise — each value should be a brief insight, not a paragraph.
Return ONLY valid JSON, no markdown fencing or explanation.\
"""


class TwinManager:
    """Manages the digital twin lifecycle."""

    @staticmethod
    async def get_or_create_twin(db: AsyncSession, user_id: str) -> UserTwin:
        """Get the user's twin, creating it if it doesn't exist."""
        result = await db.execute(
            select(UserTwin).where(UserTwin.user_id == user_id)
        )
        twin = result.scalar_one_or_none()
        if twin is None:
            twin = UserTwin(user_id=user_id)
            db.add(twin)
            await db.flush()
        return twin

    @staticmethod
    async def record_observation(
        db: AsyncSession,
        user_id: str,
        obs_type: str,
        data: dict[str, Any],
    ) -> TwinObservation:
        """Insert a raw observation for later consolidation."""
        obs = TwinObservation(
            user_id=user_id,
            observation_type=obs_type,
            observation_data=data,
        )
        db.add(obs)
        await db.flush()
        return obs

    @staticmethod
    def extract_observations_from_interaction(
        user_message: str,
        assistant_message: str,
        tool_results: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Analyze an interaction to extract twin observations."""
        observations: list[dict[str, Any]] = []

        arabic_chars = sum(1 for c in user_message if "\u0600" <= c <= "\u06ff")
        total_chars = max(len(user_message), 1)
        if arabic_chars / total_chars > 0.3:
            observations.append({
                "type": "language_preference",
                "data": {"language": "ar", "confidence": arabic_chars / total_chars},
            })
        else:
            observations.append({
                "type": "language_preference",
                "data": {"language": "en", "confidence": 1 - arabic_chars / total_chars},
            })

        observations.append({
            "type": "message_length",
            "data": {"user_chars": len(user_message), "assistant_chars": len(assistant_message)},
        })

        if tool_results:
            for tr in tool_results:
                observations.append({
                    "type": "tool_usage",
                    "data": {"tool": tr.get("tool", "unknown")},
                })

        correction_signals = [
            "actually", "no,", "that's wrong", "not what I",
            "I meant", "correction:", "please fix",
            "لا،", "غلط", "أقصد", "تصحيح",
        ]
        lower_msg = user_message.lower()
        for signal in correction_signals:
            if signal in lower_msg:
                observations.append({
                    "type": "correction",
                    "data": {"user_message": user_message[:500]},
                })
                break

        return observations

    @staticmethod
    async def run_dream_cycle(
        db: AsyncSession,
        user_id: str,
    ) -> UserTwin:
        """Rule-based consolidation (fast fallback, no LLM needed)."""
        twin = await TwinManager.get_or_create_twin(db, user_id)

        result = await db.execute(
            select(TwinObservation)
            .where(
                TwinObservation.user_id == user_id,
                TwinObservation.consolidated.is_(False),
            )
            .order_by(TwinObservation.created_at)
            .limit(200)
        )
        observations = list(result.scalars().all())

        if not observations:
            return twin

        lang_counts: dict[str, int] = {}
        tool_counts: dict[str, int] = {}
        corrections: list[dict[str, Any]] = []
        total_user_chars = 0
        interaction_count = 0

        for obs in observations:
            data = obs.observation_data
            if obs.observation_type == "language_preference":
                lang = data.get("language", "en")
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
            elif obs.observation_type == "tool_usage":
                tool = data.get("tool", "unknown")
                tool_counts[tool] = tool_counts.get(tool, 0) + 1
            elif obs.observation_type == "message_length":
                total_user_chars += data.get("user_chars", 0)
                interaction_count += 1
            elif obs.observation_type == "correction":
                corrections.append({
                    "message": data.get("user_message", ""),
                    "timestamp": obs.created_at.isoformat() if obs.created_at else "",
                })

        prefs = dict(twin.preferences or {})
        if lang_counts:
            primary_lang = max(lang_counts, key=lambda k: lang_counts[k])
            prefs["preferred_language"] = primary_lang
            prefs["language_distribution"] = lang_counts
        twin.preferences = prefs

        patterns = dict(twin.work_patterns or {})
        if tool_counts:
            patterns["tool_usage"] = tool_counts
        if interaction_count > 0:
            patterns["avg_message_length"] = total_user_chars // interaction_count
            patterns["total_interactions"] = (
                patterns.get("total_interactions", 0) + interaction_count
            )
        twin.work_patterns = patterns

        if corrections:
            existing = twin.learned_corrections
            if isinstance(existing, list):
                existing.extend(
                    {"summary": c["message"][:200], "timestamp": c["timestamp"]}
                    for c in corrections
                )
                twin.learned_corrections = existing[-50:]
            else:
                twin.learned_corrections = [
                    {"summary": c["message"][:200], "timestamp": c["timestamp"]}
                    for c in corrections[-50:]
                ]

        twin.consolidated_at = datetime.now(timezone.utc)
        twin.updated_at = datetime.now(timezone.utc)

        obs_ids = [obs.id for obs in observations]
        if obs_ids:
            await db.execute(
                update(TwinObservation)
                .where(TwinObservation.id.in_(obs_ids))
                .values(consolidated=True)
            )

        await db.flush()
        logger.info("Rule-based consolidation: %d observations for user %s", len(observations), user_id)
        return twin

    @staticmethod
    async def run_llm_dream_cycle(
        db: AsyncSession,
        user_id: str,
    ) -> UserTwin:
        """LLM-powered dream consolidation.

        Uses an LLM to analyze raw observations and generate rich,
        nuanced twin profile updates. Falls back to rule-based
        consolidation if the LLM call fails.
        """
        twin = await TwinManager.get_or_create_twin(db, user_id)

        result = await db.execute(
            select(TwinObservation)
            .where(
                TwinObservation.user_id == user_id,
                TwinObservation.consolidated.is_(False),
            )
            .order_by(TwinObservation.created_at)
            .limit(200)
        )
        observations = list(result.scalars().all())

        if not observations:
            return twin

        # Build the current profile snapshot
        current_profile = {
            "profile": twin.profile or {},
            "preferences": twin.preferences or {},
            "work_patterns": twin.work_patterns or {},
            "drafting_style": twin.drafting_style or {},
            "review_priorities": twin.review_priorities or {},
            "learned_corrections": twin.learned_corrections or [],
            "personality_model": twin.personality_model or {},
        }

        # Format observations for the prompt
        obs_lines: list[str] = []
        for obs in observations:
            ts = obs.created_at.strftime("%Y-%m-%d %H:%M") if obs.created_at else "unknown"
            obs_lines.append(
                f"- [{ts}] {obs.observation_type}: {json.dumps(obs.observation_data, ensure_ascii=False)[:300]}"
            )
        observations_text = "\n".join(obs_lines)

        prompt_text = CONSOLIDATION_PROMPT.format(
            current_profile=json.dumps(current_profile, indent=2, ensure_ascii=False),
            observations_text=observations_text,
        )

        try:
            from src.services.agent.llm_router import chat_completion

            response = await chat_completion(
                messages=[
                    {"role": "system", "content": "You are a profile analysis engine. Return only valid JSON."},
                    {"role": "user", "content": prompt_text},
                ],
                tools=None,
                model="gpt-4o-mini",
            )

            raw_content = response.choices[0].message.content or ""
            # Strip markdown code fences if present
            cleaned = raw_content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            updates = json.loads(cleaned)

            # Merge updates into twin
            if isinstance(updates.get("profile"), dict) and updates["profile"]:
                twin.profile = {**(twin.profile or {}), **updates["profile"]}
            if isinstance(updates.get("preferences"), dict) and updates["preferences"]:
                twin.preferences = {**(twin.preferences or {}), **updates["preferences"]}
            if isinstance(updates.get("work_patterns"), dict) and updates["work_patterns"]:
                twin.work_patterns = {**(twin.work_patterns or {}), **updates["work_patterns"]}
            if isinstance(updates.get("drafting_style"), dict) and updates["drafting_style"]:
                twin.drafting_style = {**(twin.drafting_style or {}), **updates["drafting_style"]}
            if isinstance(updates.get("review_priorities"), dict) and updates["review_priorities"]:
                twin.review_priorities = {**(twin.review_priorities or {}), **updates["review_priorities"]}
            if isinstance(updates.get("personality_model"), dict) and updates["personality_model"]:
                twin.personality_model = {**(twin.personality_model or {}), **updates["personality_model"]}

            new_corrections = updates.get("learned_corrections")
            if isinstance(new_corrections, list) and new_corrections:
                existing = twin.learned_corrections if isinstance(twin.learned_corrections, list) else []
                existing.extend(new_corrections)
                twin.learned_corrections = existing[-50:]

            twin.consolidated_at = datetime.now(timezone.utc)
            twin.updated_at = datetime.now(timezone.utc)

            obs_ids = [obs.id for obs in observations]
            if obs_ids:
                await db.execute(
                    update(TwinObservation)
                    .where(TwinObservation.id.in_(obs_ids))
                    .values(consolidated=True)
                )

            await db.flush()
            logger.info("LLM dream consolidation: %d observations for user %s", len(observations), user_id)
            return twin

        except Exception as e:
            logger.warning("LLM dream cycle failed, falling back to rule-based: %s", e)
            return await TwinManager.run_dream_cycle(db, user_id)
