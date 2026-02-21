"""Base generator class implementing the Facts-First, LLM-Last pattern.

This module provides the foundation for recap generators that:
1. Extract immutable facts from WeeklySummary data
2. Render deterministically (always works, no external dependencies)
3. Optionally enhance with LLM using facts as structured JSON input
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict, is_dataclass
from enum import Enum
from typing import Optional, Any
import time
import logging

from ai_text.summary_generator import WeeklySummary

logger = logging.getLogger(__name__)


class RenderingMode(str, Enum):
    """How the recap was rendered."""
    DETERMINISTIC = "deterministic"
    LLM = "llm"
    FALLBACK = "fallback"  # LLM failed, fell back to deterministic


@dataclass
class GeneratorResult:
    """Result from a generator.

    Attributes:
        title: The recap title
        content: The recap content/body
        rendering_mode: How the recap was generated
        warnings: List of warning messages for logging/monitoring
        metadata: Additional metadata including the facts_pack used
        latency_ms: Time taken to generate the recap in milliseconds
        llm_provider: Which LLM provider was used (if any)
    """
    title: str
    content: str
    rendering_mode: RenderingMode
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    latency_ms: Optional[int] = None
    llm_provider: Optional[str] = None


class BaseGenerator(ABC):
    """Base class for recap generators.

    Implements the Facts-First, LLM-Last pattern:
    1. extract_facts() - Convert WeeklySummary to immutable FactsPack
    2. render_deterministic() - Template-based rendering (always works)
    3. build_llm_prompt() - Pass facts as JSON to LLM

    This architecture ensures:
    - LLM only sees structured, validated facts
    - Deterministic fallback is always available
    - Facts can be stored for debugging/auditing
    - LLM cannot hallucinate data not in the facts
    """

    @abstractmethod
    async def extract_facts(self, summary: WeeklySummary) -> Any:
        """Extract immutable facts from WeeklySummary.

        This method transforms the mutable WeeklySummary into an immutable
        FactsPack dataclass specific to this generator type. The FactsPack
        should contain only the facts needed for this specific recap type.

        Args:
            summary: The weekly summary data from the league

        Returns:
            A frozen FactsPack dataclass specific to this generator type
        """
        pass

    @abstractmethod
    def render_deterministic(self, facts: Any) -> tuple[str, str]:
        """Render facts deterministically using templates.

        This method must always succeed and produce valid output.
        It serves as both the primary output for non-LLM mode and
        the fallback when LLM generation fails.

        Args:
            facts: The FactsPack extracted from the summary

        Returns:
            Tuple of (title, content)
        """
        pass

    @abstractmethod
    def build_llm_prompt(self, facts: Any, persona: str) -> str:
        """Build LLM prompt with facts as JSON.

        The prompt should include strict rules about only using facts
        from the provided JSON. The LLM should enhance the presentation
        but never invent new data.

        Args:
            facts: The FactsPack to include in the prompt
            persona: The desired writing persona/style

        Returns:
            Complete prompt string for the LLM
        """
        pass

    async def generate(
        self,
        summary: WeeklySummary,
        persona: Optional[str] = None,
        use_llm: bool = True,
        llm_handler: Optional[Any] = None,
        league_context: Optional[dict] = None,
    ) -> GeneratorResult:
        """Generate a recap using the facts-first pattern.

        Flow:
        1. Extract facts from summary
        2. If use_llm and llm_handler provided, attempt LLM generation
        3. Fall back to deterministic if LLM fails or not requested

        Args:
            summary: The weekly summary data
            persona: Writing persona for LLM generation
            use_llm: Whether to attempt LLM generation
            llm_handler: Handler for LLM API calls

        Returns:
            GeneratorResult with the generated recap and metadata
        """
        start_time = time.time()
        warnings: list[str] = []

        # Step 1: Extract facts
        facts = await self.extract_facts(summary)
        facts_dict = self._facts_to_dict(facts)

        logger.debug(
            "Facts extracted for recap generation",
            extra={
                "generator": self.__class__.__name__,
                "league": summary.league_name,
                "week": summary.week,
            }
        )

        # Step 2: Generate deterministic version (always available as fallback)
        det_title, det_content = self.render_deterministic(facts)

        # Build system prompt if persona is provided
        system_prompt = None
        if persona:
            from ai_text.llm_handler import build_system_prompt
            from ai_text.sports_news import fetch_sports_news
            sport = league_context.get("sport", "football") if league_context else "football"
            news = fetch_sports_news(sport)
            system_prompt = build_system_prompt(persona, league_context, news)

        # Step 3: Attempt LLM if requested
        if use_llm and llm_handler and persona:
            try:
                prompt = self.build_llm_prompt(facts, persona)
                llm_result = await self._call_llm(llm_handler, prompt, persona, system_prompt)

                if llm_result:
                    latency_ms = int((time.time() - start_time) * 1000)

                    logger.info(
                        "LLM recap generated successfully",
                        extra={
                            "generator": self.__class__.__name__,
                            "persona": persona,
                            "latency_ms": latency_ms,
                            "rendering_mode": RenderingMode.LLM.value,
                        }
                    )

                    return GeneratorResult(
                        title=self._extract_title(llm_result) or det_title,
                        content=llm_result,
                        rendering_mode=RenderingMode.LLM,
                        warnings=warnings,
                        metadata={"facts_pack": facts_dict},
                        latency_ms=latency_ms,
                        llm_provider="openai"
                    )
            except Exception as e:
                logger.warning(
                    f"LLM generation failed: {e}",
                    extra={
                        "generator": self.__class__.__name__,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )
                warnings.append(f"LLM failed: {str(e)}, using deterministic fallback")

        # Return deterministic result
        latency_ms = int((time.time() - start_time) * 1000)
        mode = RenderingMode.FALLBACK if (use_llm and persona) else RenderingMode.DETERMINISTIC

        logger.info(
            "Deterministic recap generated",
            extra={
                "generator": self.__class__.__name__,
                "latency_ms": latency_ms,
                "rendering_mode": mode.value,
                "had_llm_attempt": use_llm and persona is not None,
            }
        )

        return GeneratorResult(
            title=det_title,
            content=det_content,
            rendering_mode=mode,
            warnings=warnings,
            metadata={"facts_pack": facts_dict},
            latency_ms=latency_ms,
            llm_provider=None
        )

    async def _call_llm(
        self,
        llm_handler: Any,
        prompt: str,
        persona: str,
        system_prompt: Optional[str] = None,
    ) -> Optional[str]:
        """Call LLM handler with the prompt.

        Args:
            llm_handler: The LLM handler instance
            prompt: The complete prompt to send
            persona: The persona being used
            system_prompt: Optional system prompt for persona/context

        Returns:
            Generated text from the LLM, or None on failure
        """
        if llm_handler is None:
            return None
        return await llm_handler.call_prompt(prompt, provider="openai", system_prompt=system_prompt)

    async def _call_llm_for_plan(
        self,
        llm_handler: Any,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Optional[str]:
        """Call LLM to get a JSON plan.

        Used by two-phase LLM generators to get structured JSON output
        from the LLM. The prompt should instruct the LLM to return only
        valid JSON with no additional text.

        Args:
            llm_handler: The LLM handler instance
            prompt: The planner prompt requesting JSON output
            system_prompt: Optional system prompt for persona/context

        Returns:
            JSON string from LLM, or None on failure
        """
        if llm_handler is None:
            return None
        return await llm_handler.call_prompt(prompt, provider="openai", system_prompt=system_prompt)

    def _use_two_phase_llm(self) -> bool:
        """Whether this generator uses two-phase LLM.

        Two-phase LLM separates planning (LLM returns JSON) from
        rendering (Python builds final text). This makes validation
        trivial and prevents hallucination rants.

        Subclasses can override to enable two-phase planning.

        Returns:
            True if this generator should use two-phase LLM, False otherwise
        """
        return False

    def _facts_to_dict(self, facts: Any) -> dict:
        """Convert facts dataclass to dict for storage and serialization.

        Args:
            facts: A dataclass instance (typically a FactsPack)

        Returns:
            Dictionary representation of the facts
        """
        if is_dataclass(facts):
            return asdict(facts)
        return {}

    def _extract_title(self, llm_output: str) -> Optional[str]:
        """Extract title from LLM output if present.

        Attempts to identify a title in the LLM output by looking for
        the first line that appears to be a title (short, no period).

        Args:
            llm_output: Raw output from the LLM

        Returns:
            Extracted title or None if no title found
        """
        lines = llm_output.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            # Check if first line looks like a title:
            # - Under 100 characters
            # - Doesn't end with a period
            # - Not empty
            if first_line and len(first_line) < 100 and not first_line.endswith('.'):
                return first_line
        return None
