"""Robust LLM error handling with circuit breaker and deterministic fallback.

This module provides production-grade error handling for LLM API calls with:
- Timeout handling (30s default)
- Smart retry logic for transient errors only
- Circuit breaker pattern to prevent cascading failures
- Automatic fallback to deterministic rendering
- Comprehensive structured logging
"""
import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Callable, Awaitable, Any
from enum import Enum

import backoff
from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError
from anthropic import Anthropic, APIError as AnthropicAPIError, RateLimitError as AnthropicRateLimitError

from ai_text.summary_generator import WeeklySummary


# Configure structured logging
logger = logging.getLogger(__name__)


class RecapMode(str, Enum):
    """Recap generation mode."""
    LLM = "llm"
    DETERMINISTIC = "deterministic"
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class RecapResult:
    """Result object for recap generation with metadata.

    Attributes:
        text: The generated recap text
        mode: How the recap was generated (llm, deterministic, circuit_open)
        warnings: List of warning messages for logging/monitoring
        provider: Which LLM provider was used (openai, anthropic, or None)
        latency_ms: Time taken to generate the recap in milliseconds
    """
    text: str
    mode: RecapMode
    warnings: List[str] = field(default_factory=list)
    provider: Optional[str] = None
    latency_ms: Optional[int] = None


@dataclass
class FailureRecord:
    """Record of an LLM failure for circuit breaker tracking."""
    timestamp: datetime
    error_type: str
    provider: str


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures exceed threshold, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker implementation for LLM providers.

    Tracks failures over a time window and opens the circuit after too many failures.
    Automatically recovers after a cooldown period.

    Configuration:
        - Failure threshold: 5 failures
        - Time window: 10 minutes
        - Cooldown period: 30 minutes
    """

    # Circuit breaker configuration
    FAILURE_THRESHOLD = 5
    FAILURE_WINDOW_MINUTES = 10
    COOLDOWN_MINUTES = 30

    def __init__(self, provider: str):
        """Initialize circuit breaker for a specific provider.

        Args:
            provider: Provider name (e.g., "openai", "anthropic")
        """
        self.provider = provider
        self.failures: deque[FailureRecord] = deque()
        self.state = CircuitState.CLOSED
        self.opened_at: Optional[datetime] = None
        logger.info(
            "Circuit breaker initialized",
            extra={
                "provider": provider,
                "failure_threshold": self.FAILURE_THRESHOLD,
                "window_minutes": self.FAILURE_WINDOW_MINUTES,
                "cooldown_minutes": self.COOLDOWN_MINUTES,
            }
        )

    def _clean_old_failures(self) -> None:
        """Remove failures outside the time window."""
        cutoff = datetime.utcnow() - timedelta(minutes=self.FAILURE_WINDOW_MINUTES)
        while self.failures and self.failures[0].timestamp < cutoff:
            self.failures.popleft()

    def _get_failure_count(self) -> int:
        """Get count of failures in the current time window."""
        self._clean_old_failures()
        return len(self.failures)

    def record_failure(self, error_type: str) -> None:
        """Record a failure and potentially open the circuit.

        Args:
            error_type: Type of error that occurred
        """
        failure = FailureRecord(
            timestamp=datetime.utcnow(),
            error_type=error_type,
            provider=self.provider
        )
        self.failures.append(failure)

        failure_count = self._get_failure_count()

        if failure_count >= self.FAILURE_THRESHOLD and self.state == CircuitState.CLOSED:
            self.state = CircuitState.OPEN
            self.opened_at = datetime.utcnow()
            logger.warning(
                "Circuit breaker OPENED",
                extra={
                    "provider": self.provider,
                    "failure_count": failure_count,
                    "threshold": self.FAILURE_THRESHOLD,
                    "recent_errors": [f.error_type for f in list(self.failures)[-5:]],
                }
            )
        else:
            logger.info(
                "Failure recorded",
                extra={
                    "provider": self.provider,
                    "error_type": error_type,
                    "failure_count": failure_count,
                    "threshold": self.FAILURE_THRESHOLD,
                    "state": self.state.value,
                }
            )

    def record_success(self) -> None:
        """Record a successful call and potentially close the circuit."""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.opened_at = None
            self.failures.clear()
            logger.info(
                "Circuit breaker CLOSED after successful recovery",
                extra={"provider": self.provider}
            )

    def can_attempt(self) -> tuple[bool, Optional[str]]:
        """Check if an LLM call can be attempted.

        Returns:
            Tuple of (can_attempt, reason_if_not)
        """
        if self.state == CircuitState.CLOSED:
            return True, None

        if self.state == CircuitState.OPEN:
            # Check if cooldown period has elapsed
            if self.opened_at:
                cooldown_elapsed = datetime.utcnow() - self.opened_at
                if cooldown_elapsed.total_seconds() >= (self.COOLDOWN_MINUTES * 60):
                    self.state = CircuitState.HALF_OPEN
                    logger.info(
                        "Circuit breaker entering HALF_OPEN state",
                        extra={
                            "provider": self.provider,
                            "cooldown_elapsed_seconds": cooldown_elapsed.total_seconds(),
                        }
                    )
                    return True, None

            remaining = self.COOLDOWN_MINUTES
            if self.opened_at:
                elapsed = (datetime.utcnow() - self.opened_at).total_seconds() / 60
                remaining = max(0, self.COOLDOWN_MINUTES - int(elapsed))

            reason = f"Circuit breaker open for {self.provider}, retry in ~{remaining} minutes"
            return False, reason

        # HALF_OPEN state - allow single attempt to test recovery
        return True, None

    def get_status(self) -> dict[str, Any]:
        """Get current circuit breaker status for monitoring."""
        return {
            "provider": self.provider,
            "state": self.state.value,
            "failure_count": self._get_failure_count(),
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
        }


class ErrorClassifier:
    """Classify errors as transient (retryable) or permanent."""

    # Error types that should trigger retry
    TRANSIENT_ERRORS = {
        "timeout",
        "connection_error",
        "rate_limit",
        "service_unavailable",
        "internal_server_error",
        "bad_gateway",
    }

    @staticmethod
    def classify_openai_error(error: Exception) -> tuple[str, bool]:
        """Classify an OpenAI error.

        Args:
            error: Exception from OpenAI API

        Returns:
            Tuple of (error_type, is_transient)
        """
        if isinstance(error, APITimeoutError):
            return "timeout", True
        elif isinstance(error, RateLimitError):
            return "rate_limit", True
        elif isinstance(error, APIConnectionError):
            return "connection_error", True
        elif isinstance(error, APIError):
            # Check status code for transient errors
            if hasattr(error, 'status_code'):
                if error.status_code == 500:
                    return "internal_server_error", True
                elif error.status_code == 502:
                    return "bad_gateway", True
                elif error.status_code == 503:
                    return "service_unavailable", True
                elif error.status_code == 401:
                    return "authentication_error", False
                elif error.status_code == 400:
                    return "invalid_request", False
            return "api_error", False
        elif isinstance(error, asyncio.TimeoutError):
            return "timeout", True
        else:
            return error.__class__.__name__, False

    @staticmethod
    def classify_anthropic_error(error: Exception) -> tuple[str, bool]:
        """Classify an Anthropic error.

        Args:
            error: Exception from Anthropic API

        Returns:
            Tuple of (error_type, is_transient)
        """
        if isinstance(error, AnthropicAPIError):
            error_message = str(error).lower()

            # Check for specific error patterns
            if "timeout" in error_message:
                return "timeout", True
            elif "rate" in error_message and "limit" in error_message:
                return "rate_limit", True
            elif "connection" in error_message:
                return "connection_error", True
            elif "503" in error_message or "unavailable" in error_message:
                return "service_unavailable", True
            elif "500" in error_message:
                return "internal_server_error", True
            elif "401" in error_message or "authentication" in error_message:
                return "authentication_error", False
            elif "400" in error_message or "invalid" in error_message:
                return "invalid_request", False

            return "api_error", False
        elif isinstance(error, asyncio.TimeoutError):
            return "timeout", True
        else:
            return error.__class__.__name__, False


class LLMHandler:
    """Robust LLM handler with error handling and deterministic fallback.

    This class orchestrates LLM calls with:
    - Timeout enforcement
    - Smart retry logic for transient errors
    - Circuit breaker pattern per provider
    - Automatic fallback to deterministic rendering
    - Comprehensive logging
    """

    # LLM call configuration
    DEFAULT_TIMEOUT_SECONDS = 30
    RETRY_DELAY_SECONDS = 2
    MAX_RETRIES = 1  # Retry once for transient errors

    def __init__(
        self,
        openai_client: Optional[AsyncOpenAI],
        anthropic_client: Optional[Anthropic],
        deterministic_fallback: Callable[[WeeklySummary, str], str]
    ):
        """Initialize LLM handler.

        Args:
            openai_client: Configured OpenAI client
            anthropic_client: Configured Anthropic client
            deterministic_fallback: Function to generate deterministic recap
        """
        self.openai_client = openai_client
        self.anthropic_client = anthropic_client
        self.deterministic_fallback = deterministic_fallback

        # Circuit breakers per provider
        self.circuit_breakers = {
            "openai": CircuitBreaker("openai"),
            "anthropic": CircuitBreaker("anthropic"),
        }

        logger.info("LLM handler initialized")

    async def generate_recap(
        self,
        summary: WeeklySummary,
        style: str,
        persona: Optional[str] = None,
        provider: str = "openai"
    ) -> RecapResult:
        """Generate a recap with robust error handling.

        This method attempts to generate an LLM recap with full error handling,
        including circuit breaker checks, timeouts, retries, and fallback.

        Args:
            summary: Weekly summary data
            style: Base style for deterministic rendering
            persona: AI persona for LLM rendering
            provider: LLM provider to use ("openai" or "anthropic")

        Returns:
            RecapResult with generated text and metadata
        """
        start_time = time.time()
        warnings = []

        # Validate provider
        if provider not in ["openai", "anthropic"]:
            warnings.append(f"Invalid provider '{provider}', defaulting to deterministic")
            return self._fallback_to_deterministic(summary, style, warnings, start_time)

        # Check if client is configured
        client = self.openai_client if provider == "openai" else self.anthropic_client
        if not client:
            warnings.append(f"{provider} client not configured, using deterministic rendering")
            return self._fallback_to_deterministic(summary, style, warnings, start_time)

        # Check circuit breaker
        circuit = self.circuit_breakers[provider]
        can_attempt, reason = circuit.can_attempt()

        if not can_attempt:
            logger.warning(
                "LLM call blocked by circuit breaker",
                extra={
                    "provider": provider,
                    "reason": reason,
                    "circuit_status": circuit.get_status(),
                }
            )
            warnings.append(reason)

            # Return deterministic fallback with circuit_open mode
            text = self.deterministic_fallback(summary, style)
            latency_ms = int((time.time() - start_time) * 1000)

            return RecapResult(
                text=text,
                mode=RecapMode.CIRCUIT_OPEN,
                warnings=warnings,
                provider=None,
                latency_ms=latency_ms
            )

        # Attempt LLM call with retry logic
        logger.info(
            "Attempting LLM recap generation",
            extra={
                "provider": provider,
                "persona": persona,
                "style": style,
                "league": summary.league_name,
                "week": summary.week,
            }
        )

        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                # Generate prompt
                base_text = self.deterministic_fallback(summary, style)
                system_prompt = build_system_prompt(persona or style) if persona else None
                prompt = base_text  # The deterministic text IS the prompt content

                # Call LLM with timeout
                if provider == "openai":
                    text = await self._call_openai_with_timeout(prompt, system_prompt)
                else:
                    text = await self._call_anthropic_with_timeout(prompt, system_prompt)

                # Success - record and return
                circuit.record_success()
                latency_ms = int((time.time() - start_time) * 1000)

                logger.info(
                    "LLM recap generated successfully",
                    extra={
                        "provider": provider,
                        "latency_ms": latency_ms,
                        "attempt": attempt + 1,
                        "llm_mode": "success",
                    }
                )

                return RecapResult(
                    text=text,
                    mode=RecapMode.LLM,
                    warnings=warnings,
                    provider=provider,
                    latency_ms=latency_ms
                )

            except Exception as e:
                last_error = e

                # Classify error
                if provider == "openai":
                    error_type, is_transient = ErrorClassifier.classify_openai_error(e)
                else:
                    error_type, is_transient = ErrorClassifier.classify_anthropic_error(e)

                logger.warning(
                    "LLM call failed",
                    extra={
                        "provider": provider,
                        "error_type": error_type,
                        "is_transient": is_transient,
                        "attempt": attempt + 1,
                        "max_attempts": self.MAX_RETRIES + 1,
                        "error_message": str(e),
                        "llm_mode": "failed",
                    }
                )

                # Record failure in circuit breaker
                circuit.record_failure(error_type)

                # Only retry for transient errors
                if is_transient and attempt < self.MAX_RETRIES:
                    warnings.append(f"Retrying after {error_type} (attempt {attempt + 1})")
                    await asyncio.sleep(self.RETRY_DELAY_SECONDS)
                    continue
                else:
                    # Don't retry permanent errors or exhausted retries
                    warnings.append(f"LLM failed with {error_type}, using deterministic fallback")
                    break

        # All attempts failed - fallback to deterministic
        logger.error(
            "All LLM attempts exhausted, falling back to deterministic",
            extra={
                "provider": provider,
                "final_error_type": error_type if last_error else "unknown",
                "total_attempts": self.MAX_RETRIES + 1,
                "llm_mode": "failed",
            }
        )

        return self._fallback_to_deterministic(summary, style, warnings, start_time)

    @backoff.on_exception(
        backoff.expo,
        RateLimitError,
        max_tries=5,
        max_time=60,
        on_backoff=lambda details: logger.info(
            f"OpenAI rate limited, backing off {details['wait']:.1f}s (attempt {details['tries']})"
        ),
    )
    async def _call_openai_with_timeout(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call OpenAI API with timeout and exponential backoff for rate limits.

        Uses exponential backoff (via backoff library) for rate limit errors.
        Max 5 retries or 60 seconds total backoff time.

        Args:
            prompt: Prompt to send

        Returns:
            Generated text

        Raises:
            Various OpenAI exceptions or asyncio.TimeoutError
        """
        try:
            response = await asyncio.wait_for(
                self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt or "You are a fantasy sports expert who writes engaging recaps for league group chats."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1500,
                    temperature=0.7
                ),
                timeout=self.DEFAULT_TIMEOUT_SECONDS
            )
            return response.choices[0].message.content.strip()
        except asyncio.TimeoutError:
            logger.warning("OpenAI API call timed out", extra={"timeout_seconds": self.DEFAULT_TIMEOUT_SECONDS})
            raise

    @backoff.on_exception(
        backoff.expo,
        AnthropicRateLimitError,
        max_tries=5,
        max_time=60,
        on_backoff=lambda details: logger.info(
            f"Anthropic rate limited, backing off {details['wait']:.1f}s (attempt {details['tries']})"
        ),
    )
    async def _call_anthropic_with_timeout(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call Anthropic API with timeout and exponential backoff for rate limits.

        Uses exponential backoff (via backoff library) for rate limit errors.
        Max 5 retries or 60 seconds total backoff time.

        Args:
            prompt: Prompt to send

        Returns:
            Generated text

        Raises:
            Various Anthropic exceptions or asyncio.TimeoutError
        """
        try:
            # Anthropic client is sync, use asyncio.to_thread with timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.anthropic_client.messages.create,
                    model="claude-3-5-haiku-20241022",
                    max_tokens=1500,
                    temperature=0.7,
                    system=system_prompt or "You are a fantasy sports expert who writes engaging recaps for league group chats.",
                    messages=[{"role": "user", "content": prompt}]
                ),
                timeout=self.DEFAULT_TIMEOUT_SECONDS
            )
            return response.content[0].text.strip()
        except asyncio.TimeoutError:
            logger.warning("Anthropic API call timed out", extra={"timeout_seconds": self.DEFAULT_TIMEOUT_SECONDS})
            raise

    def _fallback_to_deterministic(
        self,
        summary: WeeklySummary,
        style: str,
        warnings: List[str],
        start_time: float
    ) -> RecapResult:
        """Generate deterministic fallback recap.

        Args:
            summary: Weekly summary data
            style: Style to use
            warnings: Accumulated warnings
            start_time: Start time for latency calculation

        Returns:
            RecapResult with deterministic text
        """
        text = self.deterministic_fallback(summary, style)
        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Generated deterministic fallback",
            extra={
                "style": style,
                "latency_ms": latency_ms,
                "llm_mode": "skipped",
            }
        )

        return RecapResult(
            text=text,
            mode=RecapMode.DETERMINISTIC,
            warnings=warnings,
            provider=None,
            latency_ms=latency_ms
        )

    async def call_prompt(self, prompt: str, provider: str = "openai", system_prompt: Optional[str] = None) -> Optional[str]:
        """Call LLM with a pre-built prompt.

        This is a simplified interface for generators to send prompts directly.
        Rate limits are handled via exponential backoff (decorator on _call_*_with_timeout).
        Circuit breaker tracks failures and prevents cascading issues.

        Args:
            prompt: The complete prompt to send to the LLM
            provider: LLM provider to use ("openai" or "anthropic")

        Returns:
            Generated text from the LLM, or None on failure
        """
        if provider not in ["openai", "anthropic"]:
            logger.warning(f"Invalid provider '{provider}', returning None")
            return None

        client = self.openai_client if provider == "openai" else self.anthropic_client
        if not client:
            logger.warning(f"{provider} client not configured, returning None")
            return None

        circuit = self.circuit_breakers[provider]
        can_attempt, reason = circuit.can_attempt()

        if not can_attempt:
            logger.warning(
                "LLM call blocked by circuit breaker",
                extra={
                    "provider": provider,
                    "reason": reason,
                    "circuit_status": circuit.get_status(),
                }
            )
            return None

        try:
            if provider == "openai":
                text = await self._call_openai_with_timeout(prompt, system_prompt)
            else:
                text = await self._call_anthropic_with_timeout(prompt, system_prompt)

            circuit.record_success()
            logger.info("LLM call_prompt succeeded", extra={"provider": provider})
            return text

        except Exception as e:
            if provider == "openai":
                error_type, _ = ErrorClassifier.classify_openai_error(e)
            else:
                error_type, _ = ErrorClassifier.classify_anthropic_error(e)

            logger.warning(
                "LLM call_prompt failed",
                extra={
                    "provider": provider,
                    "error_type": error_type,
                    "error_message": str(e),
                }
            )
            circuit.record_failure(error_type)
            return None

    def get_circuit_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all circuit breakers for monitoring.

        Returns:
            Dictionary mapping provider to circuit breaker status
        """
        return {
            provider: circuit.get_status()
            for provider, circuit in self.circuit_breakers.items()
        }


def build_system_prompt(
    persona_name: str,
    league_context: Optional[dict] = None,
    sports_news: Optional[list[str]] = None,
) -> str:
    from recaps.prompts.personas import get_persona
    persona = get_persona(persona_name)

    parts = [
        f"You are the AI Commissioner — a fantasy sports expert writing in the '{persona.name}' style.",
        "",
        "PERSONA IDENTITY:",
        persona.instructions,
        "",
        "TONE EXAMPLES (match this voice):",
    ]
    parts.extend(f'- "{ex}"' for ex in persona.tone_examples)

    if league_context:
        parts.append("")
        parts.append("LEAGUE CONTEXT:")
        if league_context.get("name"):
            parts.append(f"- League: {league_context['name']}")
        if league_context.get("sport"):
            parts.append(f"- Sport: {league_context['sport']}")
        if league_context.get("scoring_type"):
            parts.append(f"- Scoring: {league_context['scoring_type']}")
        if league_context.get("num_teams"):
            parts.append(f"- Teams: {league_context['num_teams']}")
        if league_context.get("week"):
            parts.append(f"- Week: {league_context['week']}")
        if league_context.get("season"):
            parts.append(f"- Season: {league_context['season']}")

    if league_context and league_context.get("commissioner_notes"):
        parts.append("")
        parts.append("COMMISSIONER NOTES (weave these naturally into your writing):")
        parts.append(league_context["commissioner_notes"])

    if sports_news:
        parts.append("")
        parts.append("CURRENT SPORTS NEWS (reference naturally when relevant):")
        parts.extend(f"- {headline}" for headline in sports_news)

    parts.append("")
    parts.append("STAT CITATION RULES:")
    parts.append("- Every time you mention a player, include their points in parentheses")
    parts.append("- Include projected points when available: 'Player Name (32.1 pts, proj 24.5)'")
    parts.append("- Never mention a player without their numbers")

    return "\n".join(parts)
