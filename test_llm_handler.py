"""Test script for LLM error handling system.

This script tests the robust LLM error handling implementation including:
- Circuit breaker functionality
- Error classification
- Deterministic fallback
- Logging output
"""
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass

from ai_text.llm_handler import (
    LLMHandler,
    CircuitBreaker,
    ErrorClassifier,
    RecapMode,
)
from ai_text.summary_generator import (
    WeeklySummary,
    WeeklyPerformance,
    PowerRankingEntry,
    TransactionSummary,
)

# Configure logging to see structured output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_mock_summary() -> WeeklySummary:
    """Create a mock weekly summary for testing."""
    # Create mock performances
    performance1 = WeeklyPerformance(
        roster_id="1",
        team_name="Test Team 1",
        owner_name="Owner 1",
        points_scored=120.5,
        points_projected=110.0,
        win=True,
        opponent_name="Test Team 2",
        opponent_points=95.0,
        margin=25.5
    )

    performance2 = WeeklyPerformance(
        roster_id="2",
        team_name="Test Team 2",
        owner_name="Owner 2",
        points_scored=95.0,
        points_projected=100.0,
        win=False,
        opponent_name="Test Team 1",
        opponent_points=120.5,
        margin=25.5
    )

    # Create mock power ranking
    power_ranking = PowerRankingEntry(
        rank=1,
        previous_rank=2,
        roster_id="1",
        team_name="Test Team 1",
        owner_name="Owner 1",
        record="8-2",
        points_for=1200.0,
        points_against=1000.0,
        power_score=1280.0,
        trend="up",
        movement=1
    )

    # Create mock transaction
    transaction = TransactionSummary(
        transaction_type="waiver",
        team_name="Test Team 1",
        owner_name="Owner 1",
        players_added=["Player A"],
        players_dropped=["Player B"],
        faab_spent=25,
        notes="Added Player A for $25"
    )

    return WeeklySummary(
        league_name="Test League",
        week=10,
        season=2024,
        performances=[performance1, performance2],
        highest_scorer=performance1,
        lowest_scorer=performance2,
        biggest_blowout=(performance1, performance2),
        closest_matchup=(performance1, performance2),
        power_rankings=[power_ranking],
        biggest_climber=power_ranking,
        biggest_fall=None,
        transactions=[transaction],
        total_faab_spent=25,
        most_active_trader="Owner 1",
        average_score=107.75,
        total_points=215.5,
        playoff_picture=["Test Team 1", "Test Team 2"]
    )


def mock_deterministic_fallback(summary: WeeklySummary, style: str) -> str:
    """Mock deterministic fallback for testing."""
    return f"Mock recap for {summary.league_name} Week {summary.week} ({style} style)"


async def test_circuit_breaker():
    """Test circuit breaker functionality."""
    logger.info("=" * 60)
    logger.info("TEST: Circuit Breaker Functionality")
    logger.info("=" * 60)

    circuit = CircuitBreaker("test_provider")

    # Initially should be closed
    can_attempt, reason = circuit.can_attempt()
    assert can_attempt is True, "Circuit should be closed initially"
    logger.info("✓ Circuit starts in CLOSED state")

    # Record failures up to threshold
    for i in range(CircuitBreaker.FAILURE_THRESHOLD):
        circuit.record_failure("test_error")
        logger.info(f"  Recorded failure {i + 1}/{CircuitBreaker.FAILURE_THRESHOLD}")

    # Circuit should now be open
    can_attempt, reason = circuit.can_attempt()
    assert can_attempt is False, "Circuit should be open after threshold failures"
    logger.info(f"✓ Circuit OPENED after {CircuitBreaker.FAILURE_THRESHOLD} failures")
    logger.info(f"  Reason: {reason}")

    # Record success to test recovery
    circuit.state = "half_open"  # Simulate cooldown elapsed
    circuit.record_success()

    can_attempt, reason = circuit.can_attempt()
    assert can_attempt is True, "Circuit should close after successful recovery"
    logger.info("✓ Circuit CLOSED after successful recovery")

    status = circuit.get_status()
    logger.info(f"✓ Circuit status: {status}")

    logger.info("")


def test_error_classification():
    """Test error classification."""
    logger.info("=" * 60)
    logger.info("TEST: Error Classification")
    logger.info("=" * 60)

    # Test timeout error
    timeout_error = asyncio.TimeoutError()
    error_type, is_transient = ErrorClassifier.classify_openai_error(timeout_error)
    assert error_type == "timeout", "Should classify timeout correctly"
    assert is_transient is True, "Timeout should be transient"
    logger.info(f"✓ Timeout error classified as: {error_type} (transient={is_transient})")

    # Test generic error
    generic_error = ValueError("Something went wrong")
    error_type, is_transient = ErrorClassifier.classify_openai_error(generic_error)
    assert is_transient is False, "Generic errors should not be transient"
    logger.info(f"✓ Generic error classified as: {error_type} (transient={is_transient})")

    logger.info("")


async def test_deterministic_fallback():
    """Test deterministic fallback when LLM is unavailable."""
    logger.info("=" * 60)
    logger.info("TEST: Deterministic Fallback")
    logger.info("=" * 60)

    # Create handler with no clients (simulates unconfigured API keys)
    handler = LLMHandler(
        openai_client=None,
        anthropic_client=None,
        deterministic_fallback=mock_deterministic_fallback
    )

    summary = create_mock_summary()

    # Attempt to generate recap (should fallback immediately)
    result = await handler.generate_recap(
        summary=summary,
        style="standard",
        persona="witty",
        provider="openai"
    )

    assert result.mode == RecapMode.DETERMINISTIC, "Should use deterministic mode"
    assert result.provider is None, "Provider should be None for deterministic"
    assert len(result.warnings) > 0, "Should have warning about missing client"
    assert "Mock recap" in result.text, "Should contain deterministic text"

    logger.info(f"✓ Mode: {result.mode.value}")
    logger.info(f"✓ Warnings: {result.warnings}")
    logger.info(f"✓ Latency: {result.latency_ms}ms")
    logger.info(f"✓ Text preview: {result.text[:100]}...")

    logger.info("")


async def test_circuit_breaker_integration():
    """Test circuit breaker integration with LLM handler."""
    logger.info("=" * 60)
    logger.info("TEST: Circuit Breaker Integration")
    logger.info("=" * 60)

    # Create handler with no clients (will fail immediately)
    handler = LLMHandler(
        openai_client=None,
        anthropic_client=None,
        deterministic_fallback=mock_deterministic_fallback
    )

    summary = create_mock_summary()

    # First attempt - should fail and use deterministic
    result1 = await handler.generate_recap(
        summary=summary,
        style="standard",
        persona="witty",
        provider="openai"
    )

    logger.info(f"✓ First attempt: mode={result1.mode.value}")

    # Check circuit status
    status = handler.get_circuit_status()
    logger.info(f"✓ Circuit status after attempt: {status}")

    logger.info("")


async def main():
    """Run all tests."""
    logger.info("\n" + "=" * 60)
    logger.info("LLM ERROR HANDLING SYSTEM - TEST SUITE")
    logger.info("=" * 60 + "\n")

    try:
        # Run synchronous tests
        test_error_classification()

        # Run async tests
        await test_circuit_breaker()
        await test_deterministic_fallback()
        await test_circuit_breaker_integration()

        logger.info("=" * 60)
        logger.info("ALL TESTS PASSED ✓")
        logger.info("=" * 60)

    except AssertionError as e:
        logger.error(f"TEST FAILED: {e}")
        raise
    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
